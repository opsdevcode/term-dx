"""
Constants and resource type definitions for term-dx.

Defines ANSI codes for output formatting and the set of Kubernetes
resource kinds (and CLI aliases) that term-dx can scan for terminating state.
"""

# ANSI escape sequences for terminal output
BOLD = "\033[1m"   # Start bold
SGR0 = "\033[0m"   # Reset (end bold)

# Kubectl plural resource types we scan for terminating state (must match `kubectl get <kind>`).
ALL_TYPES = [
    "namespaces",
    "customresourcedefinitions",
    "pods",
    "services",
    "persistentvolumeclaims",
    "configmaps",
    "secrets",
]

# Cluster-scoped kinds (no -n or -A when fetching).
CLUSTER_SCOPED_KINDS = frozenset({"namespaces", "customresourcedefinitions"})

# CLI accepts singular or plural; map to the kubectl plural kind name.
RESOURCE_ALIASES = {
    "namespace": "namespaces",
    "namespaces": "namespaces",
    "crd": "customresourcedefinitions",
    "crds": "customresourcedefinitions",
    "customresourcedefinition": "customresourcedefinitions",
    "customresourcedefinitions": "customresourcedefinitions",
    "pod": "pods",
    "pods": "pods",
    "service": "services",
    "services": "services",
    "pvc": "persistentvolumeclaims",
    "persistentvolumeclaims": "persistentvolumeclaims",
    "configmap": "configmaps",
    "configmaps": "configmaps",
    "secret": "secrets",
    "secrets": "secrets",
}
