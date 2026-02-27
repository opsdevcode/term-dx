"""
Diagnosis logic: list terminating resources and run full diagnostics.

Provides list_terminating() for a short listing and run_diagnosis() which
prints detailed sections per resource (finalizers, dependents, events,
remediation command).
"""

from __future__ import annotations

from typing import Optional

from .config import BOLD, CLUSTER_SCOPED_KINDS, SGR0
from .kubectl import (
    items_with_deletion,
    kubectl_get_json,
    kubectl_get_resource_json,
    run_kubectl,
)


def list_terminating(
    types_to_scan: list[str],
    namespace: Optional[str],
    name: Optional[str],
) -> None:
    """
    Print a simple list of resources stuck in Terminating.

    Args:
        types_to_scan: Kubectl plural kinds to scan (e.g. ["pods", "namespaces"]).
        namespace: If set, limit namespaced resources to this namespace.
        name: If set, only consider the resource with this name.
    """
    print()
    print(f"{BOLD}Resources stuck in Terminating{SGR0}")
    print("----------------------------------------")
    count = 0
    for kind in types_to_scan:
        obj = kubectl_get_json(
            kind,
            name=name,
            namespace=namespace,
            all_ns=(not namespace and kind not in CLUSTER_SCOPED_KINDS),
        )
        if not obj:
            continue
        for item in items_with_deletion(obj):
            rname = item.get("metadata", {}).get("name", "?")
            rns = item.get("metadata", {}).get("namespace", "") or ""
            ns_suffix = f" (ns: {rns})" if rns else ""
            print(f"  {kind}/{rname}{ns_suffix}")
            count += 1
    if count == 0:
        print("  (none found)")
    print()


def _diagnose_finalizers(finalizers: list[str]) -> None:
    """Print finalizers only when present (actual reason deletion is blocked)."""
    if not finalizers:
        print("  Finalizers: none")
    else:
        print(f"  Finalizers: {', '.join(finalizers)}")
        print("    -> A controller must complete and remove these before the resource can be removed.")
        print("    -> Investigate which controller owns each finalizer before removing manually.")


def diagnose_namespace(rname: str, verbose: bool, long_output: bool = False) -> None:
    """
    Full diagnosis for a namespace stuck terminating.

    Prints: deletion timestamp, finalizers, remaining resources in the namespace,
    optional unavailable API services (only when long_output is True), optional
    events (when verbose), and remediation command.
    """
    print()
    print(f"{BOLD}Namespace: {rname}{SGR0}")
    print("----------------------------------------")
    obj = kubectl_get_json("namespace", name=rname)
    if not obj:
        print("  (could not get namespace)")
        return
    meta = obj.get("metadata", {})
    finalizers = meta.get("finalizers") or []
    del_ts = meta.get("deletionTimestamp", "?")
    print(f"  Deletion requested: {del_ts}")
    _diagnose_finalizers(finalizers)

    # Only show remaining resources when present (actual reason namespace is stuck).
    # Group by resource type and use -o name so we get kind/name for remediation commands.
    api_res_result = run_kubectl(["api-resources", "--verbs=list", "--namespaced", "-o", "name"])
    if api_res_result.returncode == 0 and api_res_result.stdout:
        resource_types = [r.strip() for r in api_res_result.stdout.strip().splitlines()]
        remaining_by_kind: list[tuple[str, list[str]]] = []
        for res in resource_types:
            get_result = run_kubectl(
                ["get", res, "-n", rname, "--ignore-not-found", "-o", "name", "--no-headers"]
            )
            if get_result.returncode == 0 and get_result.stdout:
                items = [line.strip() for line in get_result.stdout.strip().splitlines() if line.strip()]
                if items:
                    remaining_by_kind.append((res, items))
        if remaining_by_kind:
            print("  Remaining resources in namespace:")
            max_resources = 50
            all_qualified: list[str] = []
            rows: list[tuple[str, str]] = []  # (resource_type, resource kind/name)
            for kind, items in remaining_by_kind:
                for item in items:
                    if len(rows) >= max_resources:
                        break
                    rows.append((kind, item))
                    all_qualified.append(item)
                if len(rows) >= max_resources:
                    break
            total_remaining = sum(len(items) for _, items in remaining_by_kind)
            # Table: RESOURCE TYPE | RESOURCE
            col1_header = "RESOURCE TYPE"
            col2_header = "RESOURCE"
            w1 = max(len(col1_header), max(len(r[0]) for r in rows))
            w2 = max(len(col2_header), max(len(r[1]) for r in rows))
            fmt = f"    {{0:<{w1}}}  {{1:<{w2}}}"
            print(fmt.format(col1_header, col2_header))
            print(f"    {'-' * w1}  {'-' * w2}")
            for kind, item in rows:
                print(fmt.format(kind, item))
            if total_remaining > max_resources:
                print(f"    ... ({total_remaining - max_resources} more; run delete commands below then re-run term-dx)")

            # Detect remaining resources that have finalizers (stuck terminating or will block delete,
            # e.g. Ingress with group.ingress.k8s.aws/alb-controller-ingress-group)
            stuck_remaining: list[tuple[str, list[str]]] = []
            for q in all_qualified:
                obj = kubectl_get_resource_json(q, rname)
                if not obj:
                    continue
                meta = obj.get("metadata", {})
                finalizers = meta.get("finalizers") or []
                if finalizers:
                    stuck_remaining.append((q, finalizers))
            if stuck_remaining:
                print("  Remaining resources that are stuck or have finalizers (blocking deletion):")
                rcol = "RESOURCE"
                fcol = "FINALIZERS"
                ccol = "COMMAND"
                rw = max(len(rcol), max(len(q) for q, _ in stuck_remaining))
                fw = max(len(fcol), max(len(", ".join(f)) for _, f in stuck_remaining))
                patch_cmds = [f"kubectl patch {q} -n {rname} -p '{{\"metadata\":{{\"finalizers\":null}}}}' --type=merge" for q, _ in stuck_remaining]
                cw = max(len(ccol), max(len(c) for c in patch_cmds))
                rfmt = f"    {{0:<{rw}}}  {{1:<{fw}}}  {{2:<{cw}}}"
                print(rfmt.format(rcol, fcol, ccol))
                print(f"    {'-' * rw}  {'-' * fw}  {'-' * cw}")
                for (q, fin), cmd in zip(stuck_remaining, patch_cmds):
                    print(rfmt.format(q, ", ".join(fin), cmd))

            print("  Remediation (delete remaining resources):")
            # Table: RESOURCE | COMMAND
            del_commands = [f"kubectl delete {q} -n {rname}" for q in all_qualified]
            rcol = "RESOURCE"
            ccol = "COMMAND"
            rw = max(len(rcol), max(len(q) for q in all_qualified))
            cw = max(len(ccol), max(len(c) for c in del_commands))
            rfmt = f"    {{0:<{rw}}}  {{1:<{cw}}}"
            print(rfmt.format(rcol, ccol))
            print(f"    {'-' * rw}  {'-' * cw}")
            for q, cmd in zip(all_qualified, del_commands):
                print(rfmt.format(q, cmd))
            if total_remaining > max_resources:
                print("    ... (more resources may remain; re-run term-dx after deleting above)")

    # Unavailable API services only with --long (can be noisy; real blocker is rare)
    if long_output:
        api_result = run_kubectl(["get", "apiservices", "--no-headers"])
        if api_result.returncode == 0 and api_result.stdout:
            bad = [
                line.split()[0]
                for line in api_result.stdout.strip().splitlines()
                if len(line.split()) >= 2 and line.split()[1] != "True"
            ]
            if bad:
                print("  Unavailable API services:")
                for b in bad:
                    print(f"    {b}")

    if verbose:
        print("  Recent namespace events:")
        ev_result = run_kubectl(
            ["get", "events", "-n", rname, "--sort-by=.lastTimestamp", "--no-headers"]
        )
        if ev_result.returncode == 0 and ev_result.stdout:
            for line in ev_result.stdout.strip().splitlines()[-10:]:
                print(f"    {line}")
        else:
            print("    (none)")

    patch_cmd_ns = f"kubectl patch namespace {rname} -p '{{\"metadata\":{{\"finalizers\":null}}}}' --type=merge"
    action_ns = "Remove finalizers (last resort)"
    print("  Remediation (namespace finalizers):")
    aw = max(len("ACTION"), len(action_ns))
    cw = max(len("COMMAND"), len(patch_cmd_ns))
    print(f"    {'ACTION':<{aw}}  {'COMMAND':<{cw}}")
    print(f"    {'-' * aw}  {'-' * cw}")
    print(f"    {action_ns:<{aw}}  {patch_cmd_ns:<{cw}}")
    print()


def diagnose_namespaced_resource(kind: str, rname: str, rns: str, verbose: bool) -> None:
    """
    Full diagnosis for a namespaced resource (pod, service, pvc, etc.) stuck terminating.

    Prints: deletion timestamp, finalizers, owner references, optional events,
    and the kubectl patch command to remove finalizers as last resort.
    """
    print()
    ns_label = f" (namespace: {rns})" if rns else ""
    print(f"{BOLD}{kind}/{rname}{ns_label}{SGR0}")
    print("----------------------------------------")
    obj = kubectl_get_json(kind, name=rname, namespace=rns or None)
    if not obj:
        print("  (could not get resource)")
        return
    meta = obj.get("metadata", {})
    finalizers = meta.get("finalizers") or []
    del_ts = meta.get("deletionTimestamp", "?")
    print(f"  Deletion requested: {del_ts}")
    _diagnose_finalizers(finalizers)

    # Owner refs (e.g. Deployment) may explain why the resource exists or is stuck
    owners = meta.get("ownerReferences") or []
    if owners:
        owner_str = ", ".join(f"{o.get('kind', '')}/{o.get('name', '')}" for o in owners)
        print(f"  Owner(s): {owner_str}")

    if verbose:
        print("  Recent events:")
        args = [
            "get",
            "events",
            "--field-selector",
            f"involvedObject.name={rname}",
            "--sort-by=.lastTimestamp",
            "--no-headers",
        ]
        if rns:
            args = [
                "get",
                "events",
                "-n",
                rns,
                "--field-selector",
                f"involvedObject.name={rname}",
                "--sort-by=.lastTimestamp",
                "--no-headers",
            ]
        ev_result = run_kubectl(args)
        if ev_result.returncode == 0 and ev_result.stdout:
            for line in ev_result.stdout.strip().splitlines()[-10:]:
                print(f"    {line}")
        else:
            print("    (none)")

    patch_cmd = f"kubectl patch {kind} {rname}"
    if rns:
        patch_cmd += f" -n {rns}"
    patch_cmd += " -p '{\"metadata\":{\"finalizers\":null}}' --type=merge"
    action = "Remove finalizers (last resort)"
    print("  Remediation (finalizers):")
    aw = max(len("ACTION"), len(action))
    cw = max(len("COMMAND"), len(patch_cmd))
    print(f"    {'ACTION':<{aw}}  {'COMMAND':<{cw}}")
    print(f"    {'-' * aw}  {'-' * cw}")
    print(f"    {action:<{aw}}  {patch_cmd:<{cw}}")
    print()


def run_diagnosis(
    types_to_scan: list[str],
    namespace: Optional[str],
    name: Optional[str],
    verbose: bool,
    long_output: bool = False,
) -> None:
    """
    Find all terminating resources of the given kinds and run full diagnosis for each.

    Args:
        types_to_scan: Kubectl plural kinds to scan.
        namespace: Optional namespace filter for namespaced kinds.
        name: Optional resource name to restrict to a single resource.
        verbose: If True, include recent events in each diagnosis.
        long_output: If True, include all info (e.g. unavailable API services for namespaces).
    """
    found = 0
    for kind in types_to_scan:
        # Cluster-scoped kinds (namespaces, CRDs) use neither -n nor -A
        use_ns = namespace if kind not in CLUSTER_SCOPED_KINDS else None
        all_ns = not use_ns and kind not in CLUSTER_SCOPED_KINDS
        obj = kubectl_get_json(kind, name=name, namespace=use_ns, all_ns=all_ns)
        if not obj:
            continue
        for item in items_with_deletion(obj):
            meta = item.get("metadata", {})
            rname = meta.get("name", "")
            rns = meta.get("namespace") or ""
            if not rname:
                continue
            found += 1
            if kind == "namespaces":
                diagnose_namespace(rname, verbose, long_output)
            else:
                diagnose_namespaced_resource(kind, rname, rns, verbose)
    if found == 0:
        print("No resources in Terminating state found for the given type/namespace/name.")
