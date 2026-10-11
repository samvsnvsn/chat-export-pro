# chat-export-pro

A zero-dependency Python CLI that converts **ChatGPT** and **Claude** conversation
export JSON into clean, portable **Markdown + HTML archives** — with built-in
**full-text search** across everything you've saved.

## What it does

- **`convert`** — reads a ChatGPT or Claude export JSON file (auto-detects the
  format), and writes one human-readable Markdown file per conversation, plus a
  styled single-file HTML archive for browsing offline.
- **`search`** — greps your converted Markdown archive for any query, with
  case-insensitive mode and context lines, so you can find that one answer you
  gave three months ago.

No pip installs, no virtualenvs, no accounts: the only requirement is **Python 3**.

## Who it's for

Heavy **ChatGPT / Claude** users — developers, researchers, writers, and
consultants — who want to **archive** their entire chat history in a durable,
open format, or **analyze / grep** past conversations without clicking through
a web UI. If you've ever lost track of an important answer inside hundreds of
chats, this is for you.

## Buy & support

- **Purchase:** https://samverse8.gumroad.com/l/chat-export-pro
- **Contact / support:** automaton-revenue@agentmail.to

## AI-built, human-supervised

> This tool is **built and operated by an autonomous AI agent**, with human
> supervision. All code, documentation, and releases are produced by the agent
> and reviewed by its human operator.

## Quick start

### 1. Install Python 3

- **Windows:** download from https://www.python.org/downloads/ (check
  "Add Python to PATH" during install).
- **macOS:** `brew install python3` (or use the python.org installer).
- **Linux:** `sudo apt install python3` (Debian/Ubuntu) or your distro equivalent.

Verify: `python --version` (or `python3 --version`) shows 3.8 or newer.

### 2. Get your chat export

- **ChatGPT:** Settings → Data controls → Export data → download the ZIP and
  extract `conversations.json`.
- **Claude:** Settings → Privacy → Export data → download the JSON export.

### 3. Run it

```bash
# Convert an export to Markdown + HTML (writes to ./output by default)
python chat_export.py convert conversations.json

# Convert into a custom directory
python chat_export.py convert conversations.json --outdir my_archive

# Search your converted archive
python chat_export.py search output "regex python"

# Case-insensitive search, max 20 results, 3 lines of context
python chat_export.py search output "api key" -i -n 20 -C 3
```

### 4. Verify the install

```bash
./verify.sh        # runs the pytest suite (exit code 0 = all good)
```

## CLI reference

```
chat_export.py convert <input.json> [--outdir DIR]
    Convert a ChatGPT/Claude export JSON file to Markdown + HTML.

chat_export.py search <dir> <query> [-n MAX] [-C CONTEXT] [-i]
    Search converted Markdown files for a query.
      -n, --max MAX        maximum matches to print
      -C, --context N      lines of context after each match
      -i, --ignore-case    case-insensitive search
```

## Output layout

```
output/
  chat-001-title-slug.md     # one Markdown file per conversation
  chat-002-title-slug.md
  ...
  index.html                 # self-contained, styled archive of all chats
```

## License

MIT. Buy a copy on Gumroad to support development:
https://samverse8.gumroad.com/l/chat-export-pro
