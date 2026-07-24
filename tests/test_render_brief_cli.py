from __future__ import annotations

from bungalow import build_report, render_html, render_markdown
from bungalow._sample_data import SAMPLE_RESPONSES, SAMPLE_SITUATION
from bungalow.backend import StaticBackend
from bungalow.brief import deterministic_brief, write_brief
from bungalow.cli import main


def _report():
    return build_report(SAMPLE_SITUATION, StaticBackend(SAMPLE_RESPONSES))


def test_markdown_has_the_key_sections() -> None:
    md = render_markdown(_report())
    assert "# bungalow due-diligence pack" in md
    assert "## Money" in md
    assert "Doubling ground rent" in md
    assert "Next actions" in md
    assert "not legal or financial advice" in md


def test_html_is_self_contained_and_escaped() -> None:
    html = render_html(_report())
    assert html.startswith("<!doctype html>")
    assert "Doubling ground rent" in html
    assert "£475,000" in html


class _Block:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _Resp:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]


class _FakeClient:
    def __init__(self, text: str | Exception) -> None:
        self._text = text

    @property
    def messages(self):  # type: ignore[no-untyped-def]
        return self

    def create(self, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(self._text, Exception):
            raise self._text
        return _Resp(self._text)


def test_brief_uses_client_text() -> None:
    brief = write_brief(_report(), client=_FakeClient("Watch the doubling ground rent."))
    assert brief == "Watch the doubling ground rent."


def test_brief_is_optional_on_failure() -> None:
    assert write_brief(_report(), client=_FakeClient(RuntimeError("no key"))) == ""


def test_deterministic_brief_leads_with_worst() -> None:
    brief = deterministic_brief(_report())
    assert brief
    assert "ground rent" in brief.lower()  # the top HIGH finding
    assert "high" in brief.lower()


def test_next_actions_excludes_routine_low_items() -> None:
    md = render_markdown(_report())
    actions_block = md.split("## Next actions", 1)[1]
    assert "No action needed" not in actions_block


def test_cli_demo_renders(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "due-diligence pack" in out
    assert "Doubling ground rent" in out
