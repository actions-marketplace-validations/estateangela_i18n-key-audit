"""Command line interface.

    i18n-key-audit --app ./my-app
    i18n-key-audit --app ./my-app --fail-on missing
    i18n-key-audit --app ./my-app --json report.json --comment comment.md

Standard library only, so it runs on a bare CI runner with no install step.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .locales import compare, discover, pick_base
from .report import build, dump_json, to_csv, to_markdown, to_text
from .usage import scan

FAIL_CHOICES = ("none", "missing", "gaps", "any")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="i18n-key-audit", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--app", default=".", help="project root (default: .)")
    ap.add_argument("--locales", action="append", metavar="GLOB",
                    help="where the translation files are, relative to --app "
                         "(repeatable). Auto-detected when omitted.")
    ap.add_argument("--base", metavar="NAME",
                    help="reference locale; English or the largest file when omitted")
    ap.add_argument("--source", action="append", metavar="GLOB",
                    help="which sources to scan (repeatable). All of them when omitted.")
    ap.add_argument("--json", metavar="FILE", help="write the full report as JSON")
    ap.add_argument("--csv", metavar="FILE", help="write a per-locale summary as CSV")
    ap.add_argument("--comment", metavar="FILE",
                    help="write a pull request comment as markdown")
    ap.add_argument("--fail-on", choices=FAIL_CHOICES, default="none",
                    help="exit non-zero on: missing keys, locale gaps, or any finding")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.app).expanduser().resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2

    locales = discover(root, args.locales)
    if not locales:
        print("error: no translation files found. Point --locales at them, "
              "e.g. --locales 'src/i18n/*.json'", file=sys.stderr)
        return 2

    base = pick_base(locales, args.base)
    usage = scan(root, base.keys, args.source)
    gaps = compare(base, [l for l in locales if l.path != base.path])
    report = build(base, usage, gaps)

    if not args.quiet:
        print(to_text(report))

    if args.json:
        p = Path(args.json).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(dump_json(report.as_dict()) + "\n", encoding="utf-8")
        print(f"json:    {p}")
    if args.csv:
        print(f"csv:     {to_csv(report, Path(args.csv).expanduser())}")
    if args.comment:
        p = Path(args.comment).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(to_markdown(report), encoding="utf-8")
        print(f"comment: {p}")

    # Only `missing` is certain enough to fail a build on by default; gaps are
    # opt-in because a team mid-translation would never get a green run.
    if args.fail_on in ("missing", "any") and report.missing:
        print(f"error: {len(report.missing)} key(s) used in code are not in "
              f"{report.base}", file=sys.stderr)
        return 1
    if args.fail_on in ("gaps", "any") and report.locales_with_gaps:
        print(f"error: {report.locales_with_gaps} locale(s) are missing keys",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
