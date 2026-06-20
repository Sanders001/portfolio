"""
Tests for the Compiler Framework.

Covers: Tokenizer, Parser, Executor, Pipeline, Cache, Registry, Trace.
"""
import pytest
from compiler import (
    BaseRegistry,
    BinaryOpNode,
    BlockNode,
    CompilerPipeline,
    ExecutionError,
    IdentifierNode,
    InMemoryCompilerCache,
    LexError,
    LiteralNode,
    ParseError,
    TraceStep,
    TracePrinter,
    UnaryOpNode,
)


# ── AST Nodes ─────────────────────────────────────────────────

class TestASTNodes:
    def test_literal_node_is_immutable(self):
        node = LiteralNode(value=42)
        assert node.value == 42
        assert node.node_type == "literal"
        assert node.children() == []
        with pytest.raises(AttributeError):
            node.value = 99  # frozen=True

    def test_identifier_node(self):
        node = IdentifierNode(name="age")
        assert node.name == "age"
        assert node.node_type == "identifier"

    def test_binary_op_node(self):
        left = LiteralNode(value=10)
        right = LiteralNode(value=20)
        node = BinaryOpNode(operator=">", left=left, right=right)
        assert node.operator == ">"
        assert node.children() == [left, right]

    def test_unary_op_node(self):
        operand = LiteralNode(value=True)
        node = UnaryOpNode(operator="not", operand=operand)
        assert node.children() == [operand]

    def test_block_node(self):
        stmts = (LiteralNode(1), LiteralNode(2), LiteralNode(3))
        node = BlockNode(statements=stmts)
        assert len(node.children()) == 3


# ── Cache ─────────────────────────────────────────────────────

class TestInMemoryCache:
    def test_set_and_get(self):
        cache = InMemoryCompilerCache()
        cache.set("key1", b"data1")
        assert cache.get("key1") == b"data1"

    def test_get_missing(self):
        cache = InMemoryCompilerCache()
        assert cache.get("nonexistent") is None

    def test_invalidate(self):
        cache = InMemoryCompilerCache()
        cache.set("key1", b"data1")
        cache.invalidate("key1")
        assert cache.get("key1") is None


# ── Registry ──────────────────────────────────────────────────

class TestRegistry:
    def test_register_and_get(self):
        registry = BaseRegistry()
        registry.register("greet", lambda name: f"Hello, {name}!")
        func = registry.get("greet")
        assert func("World") == "Hello, World!"

    def test_get_missing_raises(self):
        registry = BaseRegistry()
        with pytest.raises(ValueError, match="Handler not found"):
            registry.get("nonexistent")

    def test_exists(self):
        registry = BaseRegistry()
        registry.register("test", lambda: None)
        assert registry.exists("test") is True
        assert registry.exists("nope") is False

    def test_duplicate_raises(self):
        registry = BaseRegistry()
        registry.register("action", lambda: None)
        with pytest.raises(ValueError, match="already registered"):
            registry.register("action", lambda: None)


# ── Trace ─────────────────────────────────────────────────────

class TestTrace:
    def test_trace_step_to_dict(self):
        step = TraceStep(
            node_type="literal",
            value=42,
            result=42,
        )
        d = step.to_dict()
        assert d["type"] == "literal"
        assert d["result"] == 42
        assert d["value"] == 42

    def test_trace_step_with_children(self):
        child = TraceStep(node_type="literal", value=1, result=1)
        parent = TraceStep(node_type="block", result=[1], children=[child])
        d = parent.to_dict()
        assert len(d["children"]) == 1
        assert d["children"][0]["type"] == "literal"

    def test_trace_step_omits_none_fields(self):
        step = TraceStep(node_type="literal", result=True)
        d = step.to_dict()
        assert "value" not in d
        assert "duration_ms" not in d
        assert "metadata" not in d


# ── Pipeline Cache Key ────────────────────────────────────────

class TestPipeline:
    def test_cache_key_is_deterministic(self):
        key1 = CompilerPipeline._build_cache_key("age > 18")
        key2 = CompilerPipeline._build_cache_key("age > 18")
        assert key1 == key2

    def test_cache_key_varies_by_source(self):
        key1 = CompilerPipeline._build_cache_key("age > 18")
        key2 = CompilerPipeline._build_cache_key("age > 21")
        assert key1 != key2

    def test_cache_key_varies_by_version(self):
        key1 = CompilerPipeline._build_cache_key("age > 18", parser_version="1.0")
        key2 = CompilerPipeline._build_cache_key("age > 18", parser_version="2.0")
        assert key1 != key2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
