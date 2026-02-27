"""Tests for term-dx config."""

import pytest

from term_dx.config import RESOURCE_ALIASES, ALL_TYPES, CLUSTER_SCOPED_KINDS


def test_resource_aliases_cover_all_types():
    """All ALL_TYPES have at least one alias in RESOURCE_ALIASES."""
    for kind in ALL_TYPES:
        assert kind in RESOURCE_ALIASES.values()


def test_resource_aliases_singular_plural():
    """Common resources have singular and plural aliases."""
    assert RESOURCE_ALIASES["namespace"] == "namespaces"
    assert RESOURCE_ALIASES["namespaces"] == "namespaces"
    assert RESOURCE_ALIASES["pod"] == "pods"
    assert RESOURCE_ALIASES["pods"] == "pods"
    assert RESOURCE_ALIASES["crd"] == "customresourcedefinitions"


def test_cluster_scoped_kinds():
    """Cluster-scoped kinds are correct."""
    assert "namespaces" in CLUSTER_SCOPED_KINDS
    assert "customresourcedefinitions" in CLUSTER_SCOPED_KINDS
    assert "pods" not in CLUSTER_SCOPED_KINDS
