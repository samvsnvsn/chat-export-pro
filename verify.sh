#!/usr/bin/env bash
# verify.sh - run the chat-export-pro test suite (non-zero exit on failure).
set -e
cd "$(dirname "$0")"
python -m pytest tests/ -v
