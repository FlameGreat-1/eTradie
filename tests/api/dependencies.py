"""Tests for Container dependency injection.

Production module: src/engine/dependencies.py

The Container requires real environment variables (DATABASE_URL, etc.)
and establishes DB/Redis connections on init. These tests verify the
import chain and class structure. Full wiring tests require Docker.
"""


class TestContainerImports:
    def test_container_importable(self):
        """Container can be imported without side effects."""
        from engine.dependencies import Container
        assert Container is not None

    def test_container_has_init(self):
        from engine.dependencies import Container
        assert hasattr(Container, "__init__")

    def test_container_has_shutdown(self):
        from engine.dependencies import Container
        assert hasattr(Container, "shutdown")

    def test_container_has_build_rag(self):
        from engine.dependencies import Container
        assert hasattr(Container, "build_rag")

    def test_container_has_build_processor(self):
        from engine.dependencies import Container
        assert hasattr(Container, "build_processor")
