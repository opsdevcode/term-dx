"""
Kubectl invocation and Kubernetes resource JSON helpers.

All cluster access goes through subprocess kubectl calls. This module
provides a small wrapper and helpers to fetch resources as JSON and
filter for those with a deletion timestamp (stuck terminating).
"""

from __future__ import annotations

import json
import subprocess
from typing import Optional

from .config import CLUSTER_SCOPED_KINDS


def run_kubectl(args: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    """
    Run kubectl with the given args.

    Args:
        args: List of arguments (e.g. ["get", "pods", "-A", "-o", "json"]).
        capture: If True, capture stdout/stderr; otherwise inherit from process.

    Returns:
        CompletedProcess with returncode, stdout, stderr. Times out after 60s.
    """
    cmd = ["kubectl"] + args
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        timeout=60,
    )


def kubectl_get_json(
    kind: str,
    name: Optional[str] = None,
    namespace: Optional[str] = None,
    all_ns: bool = False,
) -> Optional[dict]:
    """
    Get one or more resources as JSON.

    Args:
        kind: Resource kind (plural), e.g. "pods", "namespaces".
        name: Optional specific resource name.
        namespace: Optional namespace; used only for namespaced kinds.
        all_ns: Unused; namespace vs all-namespaces is inferred from kind and namespace.

    Returns:
        Parsed JSON dict (List-style with "items" or single object), or None on
        failure / missing resource / invalid JSON.
    """
    args = ["get", kind, "-o", "json"]
    # Cluster-scoped kinds (namespaces, CRDs) use neither -n nor -A
    if kind in CLUSTER_SCOPED_KINDS:
        pass
    elif namespace:
        args.extend(["-n", namespace])
    else:
        args.append("-A")
    if name:
        args.append(name)
    result = run_kubectl(args)
    if result.returncode != 0 or not result.stdout:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def kubectl_get_resource_json(qualified_name: str, namespace: str) -> Optional[dict]:
    """
    Get a single namespaced resource by qualified name (kind/name) as JSON.

    Tries "kubectl get <qualified_name> -n <ns>" first; if that fails (e.g. some
    resources like Ingress expect type and name as separate args), falls back to
    "kubectl get <resource_type> <name> -n <ns>".

    Args:
        qualified_name: Resource in "kind/name" or "kind.api/name" form (e.g.
            "innodbcluster.mysql.oracle.com/mysql", "ingress.networking.k8s.io/app").
        namespace: Namespace the resource lives in.

    Returns:
        Parsed JSON dict for the resource, or None on failure / missing / invalid JSON.
    """
    result = run_kubectl(
        ["get", qualified_name, "-n", namespace, "-o", "json"]
    )
    if result.returncode == 0 and result.stdout:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            pass
    # Fallback: some resources (e.g. Ingress) need type and name as separate args
    if "/" in qualified_name:
        resource_type, name = qualified_name.split("/", 1)
        result = run_kubectl(
            ["get", resource_type, name, "-n", namespace, "-o", "json"]
        )
        if result.returncode == 0 and result.stdout:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                pass
    return None


def items_with_deletion(obj: dict) -> list[dict]:
    """
    Return only items that have a deletion timestamp (stuck terminating).

    Handles both a list response (obj["items"]) and a single-item response
    (the object itself). Only includes items where metadata.deletionTimestamp is set.

    Args:
        obj: JSON from kubectl get -o json (either {"items": [...]} or a single resource).

    Returns:
        List of resource dicts that are in Terminating state.
    """
    if "items" in obj:
        return [i for i in obj["items"] if i.get("metadata", {}).get("deletionTimestamp")]
    meta = obj.get("metadata", {})
    if meta.get("deletionTimestamp"):
        return [obj]
    return []
