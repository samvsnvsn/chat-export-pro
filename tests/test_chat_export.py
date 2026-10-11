import chat_export
"""Tests for chat_export.py (pytest-compatible)."""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import chat_export  # noqa: E402

CHATGPT_FIXTURE = os.path.join(HERE, "fixtures", "chatgpt_sample.json")
CLAUDE_FIXTURE = os.path.join(HERE, "fixtures", "claude_sample.json")


def test_load_chatgpt_fixture():
    chats, fmt = chat_export.load_chats(CHATGPT_FIXTURE)
    assert fmt == "chatgpt"
    assert len(chats) == 1
    chat = chats[0]
    assert chat["title"] == "Python Tips"
    assert chat["id"] == "conv-001"
    assert len(chat["turns"]) == 4  # system node skipped
    assert [t["role"] for t in chat["turns"]] == ["user", "assistant", "user", "assistant"]
    assert "reverse a string" in chat["turns"][0]["text"]
    assert "slicing" in chat["turns"][1]["text"]
    with open(CHATGPT_FIXTURE, encoding="utf-8") as f:
        assert chat_export.detect_format(json.load(f)) == "chatgpt"


def test_load_claude_fixture():
    chats, fmt = chat_export.load_chats(CLAUDE_FIXTURE)
    assert fmt == "claude"
    assert len(chats) == 2
    first = chats[0]
    assert first["title"] == "Recipe Planning"
    assert first["id"] == "claude-uuid-1234"
    assert [t["role"] for t in first["turns"]] == ["user", "assistant", "user"]
    assert first["turns"][2]["text"] == "How long does that take?"  # content-list form
    assert chats[1]["title"] == "Code Review"
    with open(CLAUDE_FIXTURE, encoding="utf-8") as f:
        assert chat_export.detect_format(json.load(f)) == "claude"


def test_parse_chatgpt_skips_empty_and_system():
    data = {"conversations": [{
        "title": "T", "id": "1",
        "mapping": {
            "a": {"message": {"author": {"role": "system"},
                              "content": {"parts": ["sys"]}}},
            "b": {"message": {"author": {"role": "user"}, "content": {"parts": [""]}}},
            "c": {"message": {"author": {"role": "user"}, "content": {"parts": ["hi"]}}},
        }}]}
    chats = chat_export.parse_chatgpt(data)
    assert chats[0]["turns"] == [{"role": "user", "text": "hi"}]


def test_markdown_structure():
    chats, _ = chat_export.load_chats(CHATGPT_FIXTURE)
    md = chat_export.chat_to_markdown(chats[0])
    assert md.startswith("# Python Tips")
    assert "## User" in md and "## Assistant" in md
    assert "text[::-1]" in md
    assert md.index("reverse a string") < md.index("slicing") < md.index("reversing a list")
    assert md.endswith("\n")


def test_html_structure():
    chats, _ = chat_export.load_chats(CHATGPT_FIXTURE)
    out = chat_export.chat_to_html(chats[0])
    assert out.startswith("<!DOCTYPE html>") and "</html>" in out
    assert "<title>Python Tips</title>" in out and "<h1>Python Tips</h1>" in out
    assert out.count('class="turn"') == 4
    assert "<code>text[::-1]</code>" in out
    assert "<li>Simple</li>" in out
    assert "<pre><code>" in out  # fenced code block rendered


def test_html_escapes_user_input():
    chat = {"title": "A <b> & title", "id": "x", "created_at": "",
            "turns": [{"role": "user", "text": "<script>alert(1)</script>"}]}
    out = chat_export.chat_to_html(chat)
    assert "<script>" not in out and "&lt;script&gt;" in out
    assert "A &lt;b&gt; &amp; title" in out


def test_html_bold_italic():
    chats, _ = chat_export.load_chats(CLAUDE_FIXTURE)
    out = chat_export.chat_to_html(chats[0])
    assert "<em>quick</em>" in out
    assert "<strong>aglio e olio</strong>" in out
    assert "<li>Boil spaghetti</li>" in out


def test_slug_unique():
    used = set()
    s1 = chat_export._slug("My Chat!", used)
    s2 = chat_export._slug("My Chat!", used)
    s3 = chat_export._slug("My Chat!", used)
    assert s1 == "my-chat"
    assert {s1, s2, s3} == {"my-chat", "my-chat-2", "my-chat-3"}


def test_convert_cli_produces_files(tmp_path):
    outdir = tmp_path / "out"
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "chat_export.py"),
         "convert", CHATGPT_FIXTURE, "--outdir", str(outdir)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert sorted(os.listdir(outdir)) == ["python-tips.html", "python-tips.md"]
    assert (outdir / "python-tips.md").read_text(encoding="utf-8").startswith("# Python Tips")
    assert "</html>" in (outdir / "python-tips.html").read_text(encoding="utf-8")


def test_convert_claude_cli(tmp_path):
    outdir = tmp_path / "out"
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "chat_export.py"),
         "convert", CLAUDE_FIXTURE, "--outdir", str(outdir)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "recipe-planning.md" in os.listdir(outdir)
    assert "code-review.md" in os.listdir(outdir)


def test_convert_empty_export_returns_error(tmp_path):
    bad = tmp_path / "empty.json"
    bad.write_text(json.dumps({"conversations": []}), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "chat_export.py"),
         "convert", str(bad), "--outdir", str(tmp_path / "o")],
        capture_output=True, text=True)
    assert r.returncode != 0


def test_help_works():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "chat_export.py"), "--help"],
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "convert" in r.stdout and "search" in r.stdout


@pytest.fixture()
def converted_dir(tmp_path):
    """Convert both fixtures into one directory; return its path."""
    outdir = tmp_path / "out"
    for fixture in (CHATGPT_FIXTURE, CLAUDE_FIXTURE):
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "chat_export.py"),
             "convert", fixture, "--outdir", str(outdir)],
            capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    return str(outdir)


def _run_search(directory, *extra):
    return subprocess.run(
        [sys.executable, os.path.join(ROOT, "chat_export.py"), "search", directory, *extra],
        capture_output=True, text=True)


def test_search_finds_match(converted_dir):
    r = _run_search(converted_dir, "reverse")
    assert r.returncode == 0
    assert "python-tips.md" in r.stdout
    assert "reverse a string" in r.stdout


def test_search_case_insensitive(converted_dir):
    assert "reverse a string" in _run_search(converted_dir, "REVERSE", "-i").stdout
    assert "reverse a string" not in _run_search(converted_dir, "REVERSE").stdout


def test_search_no_match(converted_dir):
    r = _run_search(converted_dir, "xyzzy-not-here")
    assert r.returncode == 0 and "No matches" in r.stdout


def test_search_context_lines(converted_dir):
    r = _run_search(converted_dir, "slicing", "-C", "1")
    assert r.returncode == 0
    assert any(line.startswith("  ") for line in r.stdout.splitlines())


def test_search_missing_directory(tmp_path):
    assert _run_search(str(tmp_path / "nope"), "query").returncode != 0


def test_parse_claude_content_blocks_with_null_text_preserve_unicode_text():
    chats = chat_export.parse_claude([{
        "name": "Unicode",
        "chat_messages": [{
            "sender": "human",
            "content": [{"text": None}, {"text": "☃"}],
        }],
    }])

    assert chats[0]["turns"] == [{"role": "user", "text": "☃"}]
