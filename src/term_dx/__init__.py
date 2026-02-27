"""
term_dx: Diagnose Kubernetes resources stuck in Terminating state.

Scans namespaces, pods, services, PVCs, configmaps, and secrets for
metadata.deletionTimestamp (resources that are stuck terminating), then
reports finalizers, dependents, and remediation commands.
"""

__version__ = "0.1.0"
