"""
CLI entry point for term-dx.

Parses options and arguments, then delegates to list_terminating() or
run_diagnosis(). Run after setting cluster context (e.g. set-clus staging).
"""

from __future__ import annotations

import sys
from typing import Optional

import click

from .config import ALL_TYPES, RESOURCE_ALIASES
from .diagnose import list_terminating, run_diagnosis

# Shown at the bottom of term-dx --help / term-dx -h
EPILOG = """
Examples:

  term-dx -h                     # Show help (same as --help)
  term-dx --help                 # Show help
  term-dx                        # Find and diagnose all terminating resources (all types)
  term-dx namespace              # Only namespaces stuck terminating
  term-dx crd                    # Only CRDs stuck terminating
  term-dx pod -n app             # Only pods in namespace app
  term-dx namespace my-stuck-ns  # Diagnose why namespace my-stuck-ns is stuck
  term-dx pod my-pod -n app      # Diagnose why pod my-pod in app is stuck
  term-dx -l                     # List only (no diagnosis)
  term-dx --long                 # Include all info (e.g. unavailable API services)

Run after setting cluster context (e.g. set-clus staging).
"""


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
    epilog=EPILOG,
)
@click.option(
    "-n",
    "--namespace",
    "namespace",
    metavar="NS",
    help="Limit pod/service/pvc/etc. to namespace NS",
)
@click.option(
    "-l",
    "--list",
    "list_only",
    is_flag=True,
    help="Only list terminating resources; do not run full diagnosis",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Include events and extra detail",
)
@click.option(
    "--long",
    "long_output",
    is_flag=True,
    help="Include all diagnostic info (e.g. unavailable API services for namespaces)",
)
@click.argument(
    "resource_type",
    type=click.Choice(list(RESOURCE_ALIASES), case_sensitive=False),
    required=False,
)
@click.argument("name", required=False)
def main(
    namespace: Optional[str],
    list_only: bool,
    verbose: bool,
    long_output: bool,
    resource_type: Optional[str],
    name: Optional[str],
) -> int:
    """
    List and diagnose Kubernetes resources stuck in Terminating state.

    Dispatches to list_terminating() when -l/--list is set, otherwise
    run_diagnosis(). Resource type and name are optional; when omitted,
    all supported kinds are scanned.
    """
    if resource_type:
        types_to_scan = [RESOURCE_ALIASES[resource_type]]
    else:
        types_to_scan = ALL_TYPES

    ns: Optional[str] = namespace or None
    resource_name: Optional[str] = name or None

    if list_only:
        list_terminating(types_to_scan, ns, resource_name)
    else:
        run_diagnosis(types_to_scan, ns, resource_name, verbose, long_output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
