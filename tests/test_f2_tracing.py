"""
Tests for _call_claude's LangSmith trace_id capture (Day 37, KM #241
LangSmith). _call_claude now returns (text, trace_id) -- trace_id comes
from get_current_run_tree() and must gracefully be None if no run tree is
available (LangSmith not configured), without affecting the returned text.
"""

from types import SimpleNamespace

from src.f2_summarise import summariser


class FakeMessages:
    def __init__(self, text: str):
        self._text = text

    def create(self, **kwargs):
        return SimpleNamespace(content=[SimpleNamespace(text=self._text)])


class FakeClient:
    def __init__(self, text: str):
        self.messages = FakeMessages(text)


def test_call_claude_returns_trace_id_when_run_tree_present(monkeypatch):
    fake_run_tree = SimpleNamespace(id="abc-123")
    monkeypatch.setattr(summariser, "get_current_run_tree", lambda: fake_run_tree)

    text, trace_id, usage = summariser._call_claude(FakeClient("hello"), "prompt")

    assert text == "hello"
    assert trace_id == "abc-123"


def test_call_claude_returns_none_trace_id_when_run_tree_missing(monkeypatch):
    monkeypatch.setattr(summariser, "get_current_run_tree", lambda: None)

    text, trace_id, usage = summariser._call_claude(FakeClient("hello"), "prompt")

    assert text == "hello"
    assert trace_id is None


def test_call_claude_returns_none_trace_id_when_get_current_run_tree_raises(monkeypatch):
    def boom():
        raise RuntimeError("no tracing context")

    monkeypatch.setattr(summariser, "get_current_run_tree", boom)

    text, trace_id, usage = summariser._call_claude(FakeClient("hello"), "prompt")

    assert text == "hello"
    assert trace_id is None
