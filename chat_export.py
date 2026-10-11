#!/usr/bin/env python3
import argparse
import html
import json
import os
import re
import sys
from datetime import datetime


def parse_chatgpt(data):
    if isinstance(data, dict):
        data = data.get("conversations", [data])
    chats = []
    for conv in data:
        turns = []
        for node_id in conv.get("mapping", {}):
            node = conv["mapping"][node_id] or {}
            msg = node.get("message")
            if not msg:
                continue
            role = msg.get("author", {}).get("role")
            if role not in ("user", "assistant"):
                continue
            content = msg.get("content", {})
            parts = content.get("parts")
            if parts is None and isinstance(content.get("text"), str):
                parts = [content["text"]]
            if not parts:
                continue
            text = "\n".join(p if isinstance(p, str) else json.dumps(p)
                             for p in parts if p is not None).strip()
            if text:
                turns.append({"role": role, "text": text})
        if turns:
            chats.append({
                "title": conv.get("title") or "Untitled chat",
                "id": str(conv.get("id") or conv.get("conversation_id") or ""),
                "created_at": conv.get("create_time") or conv.get("created_at") or "",
                "turns": turns,
            })
    return chats


def parse_claude(data):
    if isinstance(data, dict):
        data = data.get("conversations", [data])
    chats = []
    for conv in data:
        turns = []
        for msg in conv.get("chat_messages", conv.get("messages", [])):
            sender = msg.get("sender") or msg.get("role") or "user"
            sender = "user" if sender == "human" else sender
            text = msg.get("text")
            if text is None:
                content = msg.get("content")
                if isinstance(content, list):
                    text = "\n".join(c.get("text", "") if isinstance(c, dict) else str(c)
                                     for c in content)
                else:
                    text = str(content or "")
            text = (text or "").strip()
            if text:
                turns.append({"role": sender, "text": text})
        if turns:
            chats.append({
                "title": conv.get("name") or conv.get("title") or "Untitled chat",
                "id": str(conv.get("uuid") or conv.get("id") or ""),
                "created_at": conv.get("created_at") or conv.get("created") or "",
                "turns": turns,
            })
    return chats


def detect_format(data):
    if isinstance(data, dict):
        data = data.get("conversations", [data])
    if not isinstance(data, list) or not data:
        return "chatgpt"
    first = data[0]
    if isinstance(first, dict):
        if "mapping" in first or "current_node" in first:
            return "chatgpt"
        if "chat_messages" in first or "name" in first or "uuid" in first:
            return "claude"
    return "chatgpt"


def load_chats(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if detect_format(data) == "claude":
        return parse_claude(data), "claude"
    return parse_chatgpt(data), "chatgpt"


def _slug(title, used):
    base = re.sub(r"[^A-Za-z0-9_-]+", "-", title.strip().lower()).strip("-") or "chat"
    name, n = base, 2
    while name in used:
        name = "%s-%d" % (base, n)
        n += 1
    used.add(name)
    return name


def _ts(value):
    if isinstance(value, (int, float)) and value:
        try:
            return datetime.fromtimestamp(
                value, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            return str(value)
    return str(value or "")


def chat_to_markdown(chat):
    lines = ["# %s" % chat["title"], ""]
    ts = _ts(chat.get("created_at"))
    if ts:
        lines += ["*Exported: %s*" % ts, ""]
    for turn in chat["turns"]:
        lines += ["## %s" % turn["role"].capitalize(), "", turn["text"], ""]
    return "\n".join(lines).rstrip() + "\n"


_ROLE_COLORS = {"user": "#2b6cb0", "assistant": "#276749"}


def chat_to_html(chat):
    title = html.escape(chat["title"])
    css = ("body{font-family:Georgia,serif;max-width:760px;margin:2rem auto;"
           "padding:0 1rem;color:#222}"
           ".turn{border-left:3px solid #ccc;margin:1rem 0;padding:.25rem 1rem}"
           ".role{font-weight:bold}"
           "pre{background:#f4f4f4;padding:.5rem;overflow-x:auto}")
    out = ["<!DOCTYPE html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
           "<title>%s</title>" % title, "<style>", css, "</style>", "</head>",
           "<body>", "<h1>%s</h1>" % title]
    ts = _ts(chat.get("created_at"))
    if ts:
        out.append("<p><em>Exported: %s</em></p>" % html.escape(ts))
    for turn in chat["turns"]:
        role = turn["role"]
        color = _ROLE_COLORS.get(role, "#555")
        out.append('<div class="turn" style="border-color:%s">' % color)
        out.append('<span class="role" style="color:%s">%s</span>'
                   % (color, html.escape(role.capitalize())))
        out.append(_text_to_html(turn["text"]))
        out.append("</div>")
    out += ["</body>", "</html>"]
    return "\n".join(out) + "\n"


def _inline(text):
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def _text_to_html(text):
    """Render markdown-ish text to HTML: fenced code, lists, paragraphs."""
    parts = []
    tokens = re.split(r"```", text)  # even tokens: prose; odd: code blocks
    for i, token in enumerate(tokens):
        if i % 2 == 1:
            parts.append("<pre><code>%s</code></pre>" % html.escape(token.strip("\n")))
            continue
        for block in re.split(r"\n\s*\n", token):
            lines = [l for l in block.split("\n") if l.strip()]
            if not lines:
                continue
            if all(re.match(r"^\s*[-*] ", l) for l in lines):
                items = "".join("<li>%s</li>" % _inline(l.strip()[2:]) for l in lines)
                parts.append("<ul>%s</ul>" % items)
            else:
                parts.append("<p>%s</p>" % "<br>".join(_inline(l) for l in lines))
    return "\n".join(parts)


def cmd_convert(args):
    chats, fmt = load_chats(args.input)
    if not chats:
        print("No chats found in %s (format: %s)" % (args.input, fmt), file=sys.stderr)
        return 1
    os.makedirs(args.outdir, exist_ok=True)
    used = set()
    for chat in chats:
        slug = _slug(chat["title"], used)
        with open(os.path.join(args.outdir, slug + ".md"), "w", encoding="utf-8") as f:
            f.write(chat_to_markdown(chat))
        with open(os.path.join(args.outdir, slug + ".html"), "w", encoding="utf-8") as f:
            f.write(chat_to_html(chat))
        print("Wrote %s.md and %s.html in %s" % (slug, slug, args.outdir))
    print("Converted %d chat(s) from %s format into %s" % (len(chats), fmt, args.outdir))
    return 0


def cmd_search(args):
    if not os.path.isdir(args.directory):
        print("Not a directory: %s" % args.directory, file=sys.stderr)
        return 1
    flags = re.IGNORECASE if args.ignore_case else 0
    pattern = re.compile(re.escape(args.query), flags)
    matches = 0
    for name in sorted(os.listdir(args.directory)):
        if not name.lower().endswith(".md"):
            continue
        with open(os.path.join(args.directory, name), "r", encoding="utf-8") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if pattern.search(line):
                matches += 1
                print("%s:%d: %s" % (name, i + 1, line.rstrip()))
                for j in range(1, args.context + 1):
                    if i + j < len(lines):
                        print("  %d: %s" % (i + j + 1, lines[i + j].rstrip()))
                if matches >= args.max:
                    print("... (stopped after %d matches)" % args.max)
                    return 0
    if matches == 0:
        print("No matches for %r in %s" % (args.query, args.directory))
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="chat_export.py",
        description="Convert ChatGPT/Claude chat export JSON to Markdown and "
                    "HTML archives, with search.")
    sub = p.add_subparsers(dest="command")

    pc = sub.add_parser("convert", help="Convert a chat export JSON file to Markdown + HTML")
    pc.add_argument("input", help="Path to the chat export JSON file")
    pc.add_argument("--outdir", default="output", help="Output directory (default: output)")
    pc.set_defaults(func=cmd_convert)

    ps = sub.add_parser("search", help="Search converted Markdown files for a query")
    ps.add_argument("directory", help="Directory of converted Markdown files")
    ps.add_argument("query", help="Query string to search for")
    ps.add_argument("-n", "--max", type=int, default=50, help="Max matches to print")
    ps.add_argument("-C", "--context", type=int, default=0,
                    help="Lines of context after each match")
    ps.add_argument("-i", "--ignore-case", action="store_true",
                    help="Case-insensitive search")
    ps.set_defaults(func=cmd_search)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
