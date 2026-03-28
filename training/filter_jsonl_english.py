#!/usr/bin/env python3
"""Keep only JSONL rows whose `text` field is detected as English (langdetect)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from langdetect import DetectorFactory, LangDetectException, detect

# Reproducible detection order
DetectorFactory.seed = 42


def is_english(text: str) -> bool:
    text = (text or "").strip()
    if not text:
        return False
    try:
        return detect(text) == "en"
    except LangDetectException:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        type=Path,
        help="Input .jsonl path",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (default: same as input, with backup)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="When writing in-place, do not create a .bak copy",
    )
    args = parser.parse_args()
    inp: Path = args.input
    out: Path = args.output or inp

    if not inp.is_file():
        print(f"error: input not found: {inp}", file=sys.stderr)
        return 1

    tmp = out.with_suffix(out.suffix + ".tmp")
    kept = 0
    dropped = 0
    bad_lines = 0

    with inp.open(encoding="utf-8") as fin, tmp.open("w", encoding="utf-8") as fout:
        for line_no, line in enumerate(fin, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                bad_lines += 1
                print(f"warning: line {line_no}: JSON decode error: {e}", file=sys.stderr)
                continue
            text = obj.get("text", "")
            if is_english(text):
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                kept += 1
            else:
                dropped += 1

    if out == inp and not args.no_backup:
        bak = inp.with_suffix(inp.suffix + ".bak")
        shutil.copy2(inp, bak)
        print(f"backup: {bak}")

    tmp.replace(out)
    print(f"kept={kept} dropped={dropped} bad_lines={bad_lines} -> {out}")
    return 1 if bad_lines else 0


if __name__ == "__main__":
    raise SystemExit(main())
