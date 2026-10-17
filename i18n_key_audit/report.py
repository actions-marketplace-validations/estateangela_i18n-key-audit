"""Turn the analysis into something a person acts on.

Three findings, deliberately ranked by how certain they are rather than by
how many of them there are:

1. **missing** -- referenced in code, absent from the base locale. The user
   sees a raw key. Certain, and always a bug.
2. **gaps** -- present in the base locale, absent from another. Needs no
   source analysis, so it cannot be wrong. Every non-base locale in every
   project measured had some.
3. **unused** -- defined but never referenced. Useful for cleanup, but keys
   can be built at runtime, so this is a suggestion. Reported as *possibly*
   unused, with the number of dynamic call sites alongside it.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from .locales import Gap, Locale
from .usage import Usage

MARKER = "<!-- i18n-key-audit -->"


@dataclass
class Report:
    base: str
    base_keys: int
    style: str
    files_scanned: int
    dynamic_sites: int
    missing: list[str] = field(default_factory=list)
    unused: list[str] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)

    @property
    def locales_with_gaps(self) -> int:
        return sum(1 for g in self.gaps if g.missing)

    def as_dict(self) -> dict:
        return {
            "base": self.base, "base_keys": self.base_keys,
            "reference_style": self.style, "files_scanned": self.files_scanned,
            "dynamic_key_sites": self.dynamic_sites,
            "missing": self.missing, "possibly_unused": self.unused,
            "locales": [{"locale": g.locale, "missing": g.missing,
                         "extra": g.extra, "untranslated": g.untranslated}
                        for g in self.gaps],
        }


def build(base: Locale, usage: Usage, gaps: list[Gap]) -> Report:
    return Report(
        base=base.path, base_keys=len(base.keys), style=usage.style,
        files_scanned=usage.files_scanned, dynamic_sites=usage.dynamic_sites,
        missing=list(usage.unknown_calls),
        unused=sorted(set(base.keys) - usage.used),
        gaps=gaps)


def to_csv(r: Report, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["locale", "missing", "extra", "untranslated", "complete"])
        for g in r.gaps:
            w.writerow([g.locale, len(g.missing), len(g.extra),
                        len(g.untranslated), "yes" if g.complete else "no"])
    return path


def to_markdown(r: Report, limit: int = 10) -> str:
    """A pull request comment. Says nothing when there is nothing to say."""
    lines = [MARKER]
    if not r.missing and not r.locales_with_gaps:
        lines.append(f"**Translations look complete.** {r.base_keys} keys, "
                     f"{len(r.gaps)} locales, none missing anything.")
        return "\n".join(lines) + "\n"

    lines.append("### Translation keys")
    lines.append("")
    if r.missing:
        lines.append(f"**{len(r.missing)} key(s) used in code but not in "
                     f"`{r.base}`** — these render as the raw key:")
        for k in r.missing[:limit]:
            lines.append(f"- `{k}`")
        if len(r.missing) > limit:
            lines.append(f"- _…and {len(r.missing) - limit} more_")
        lines.append("")
    if r.locales_with_gaps:
        worst = sorted((g for g in r.gaps if g.missing),
                       key=lambda g: -len(g.missing))[:limit]
        lines.append(f"**{r.locales_with_gaps} of {len(r.gaps)} locales are "
                     f"missing keys:**")
        for g in worst:
            lines.append(f"- `{g.locale}` — {len(g.missing)} missing")
        if r.locales_with_gaps > limit:
            lines.append(f"- _…and {r.locales_with_gaps - limit} more_")
        lines.append("")
    if r.unused:
        note = (f" (the project builds {r.dynamic_sites} key(s) at runtime, "
                f"so check before deleting)" if r.dynamic_sites else "")
        lines.append(f"<sub>{len(r.unused)} key(s) look unused{note}.</sub>")
    return "\n".join(lines) + "\n"


def to_text(r: Report, limit: int = 8) -> str:
    out = [f"{r.base_keys} keys in {r.base}",
           f"  reference style   {r.style} ({r.files_scanned} source files)"]
    out.append(f"  missing           {len(r.missing)}"
               + ("   <- rendered as a raw key" if r.missing else ""))
    for k in r.missing[:limit]:
        out.append(f"      {k}")
    if len(r.missing) > limit:
        out.append(f"      …and {len(r.missing) - limit} more")
    out.append(f"  locales w/ gaps   {r.locales_with_gaps}/{len(r.gaps)}")
    for g in sorted((g for g in r.gaps if g.missing), key=lambda g: -len(g.missing))[:limit]:
        out.append(f"      {g.locale}  {len(g.missing)} missing")
    tail = f" (watch out: {r.dynamic_sites} runtime-built keys)" if r.dynamic_sites else ""
    out.append(f"  possibly unused   {len(r.unused)}{tail}")
    return "\n".join(out)


def dump_json(data) -> str:
    out = json.dumps(data, ensure_ascii=False, indent=2)
    return out.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
