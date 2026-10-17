"""Find which translation keys the source actually references.

Two things make this harder than it looks, both measured rather than
assumed:

* Projects reference keys in more than one way, and some use several at
  once. One project in the sample had 521 function-call references and 561
  property-access references in the same codebase. Supporting one style
  only reported every key of the other style as unused -- 686 of them, in a
  project where the true figure was 17.
* Keys can be built at runtime (``t(`errors.${code}`)``). Those are
  invisible to any static pass, so "unused" is a suggestion, never a fact.
  The count of dynamic call sites is reported so the caller can say so.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

SOURCE_EXT = (".tsx", ".ts", ".jsx", ".js", ".mjs", ".cjs", ".vue", ".svelte")
SKIP_DIRS = {"node_modules", ".git", "build", "dist", "ios", "android", "vendor",
             "coverage", "__snapshots__", "__tests__", "__mocks__", "e2e",
             "cypress", "storybook-static"}
#: Test files invent strings that look like keys; counting them as missing
#: translations produces confident nonsense.
SKIP_FILE = re.compile(r"\.(test|spec|stories|mock)\.[jt]sx?$|\.d\.ts$")

#: t('key'), i18n.t("key"), $t('key'), __('key')
CALL = re.compile(
    r"""\b(?:t|__|\$t|i18n\.t)\(\s*['"]([A-Za-z0-9_.\-]{2,120})['"]""")
#: intl.formatMessage({ id: 'key' }). Matching a bare `id:` instead pulled in
#: every React prop and test fixture in the project -- it reported 144 missing
#: keys where there were 7, most of them strings like "abc" and "R1".
FORMAT_MESSAGE = re.compile(
    r"""formatMessage\(\s*\{[^}]*?\bid\s*:\s*['"]([A-Za-z0-9_.\-]{2,120})['"]""",
    re.S)
#: t(`key.${x}`) -- a key assembled at runtime
DYNAMIC = re.compile(r"""\b(?:t|__|\$t|i18n\.t)\(\s*[`]""")
#: loc.settings.about / strings.common.ok
PROPERTY = re.compile(r"\b(\w+)((?:\.\w+){1,4})\b")


@dataclass
class Usage:
    by_call: dict[str, int] = field(default_factory=dict)
    by_property: dict[str, int] = field(default_factory=dict)
    dynamic_sites: int = 0
    files_scanned: int = 0
    #: Keys referenced through a call but absent from the base locale.
    #: Only call style can say this: a mistyped property chain is
    #: indistinguishable from any other property chain.
    unknown_calls: list[str] = field(default_factory=list)

    @property
    def used(self) -> set[str]:
        return set(self.by_call) | set(self.by_property)

    @property
    def style(self) -> str:
        if self.by_call and self.by_property:
            return "mixed"
        if self.by_property:
            return "property"
        if self.by_call:
            return "call"
        return "none"


def scan(root: Path, known: dict[str, str], include: list[str] | None = None) -> Usage:
    """Scan sources under ``root`` for references to ``known`` keys."""
    u = Usage()
    paths = []
    if include:
        for pat in include:
            paths += [p for p in root.glob(pat) if p.is_file()]
    else:
        paths = [p for p in root.rglob("*")
                 if p.is_file() and p.suffix in SOURCE_EXT]

    for p in paths:
        if (SKIP_DIRS & set(p.parts)) or SKIP_FILE.search(p.name):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        u.files_scanned += 1
        u.dynamic_sites += len(DYNAMIC.findall(text))

        for key in CALL.findall(text) + FORMAT_MESSAGE.findall(text):
            if key in known:
                u.by_call[key] = u.by_call.get(key, 0) + 1
            elif _looks_like_a_key(key, known):
                u.unknown_calls.append(key)

        # A property chain counts only when it resolves to a real key, which
        # is what keeps `props.navigation.navigate` out of the results.
        for head, rest in PROPERTY.findall(text):
            path = rest.lstrip(".")
            for cand in (path, f"{head}.{path}"):
                if cand in known:
                    u.by_property[cand] = u.by_property.get(cand, 0) + 1
                    break

    u.unknown_calls = sorted(set(u.unknown_calls))
    return u


def _looks_like_a_key(key: str, known: dict[str, str]) -> bool:
    """Is this string plausibly a translation key rather than any old string?

    ``t()`` is a common function name, so without this a project that uses
    some other ``t`` would produce noise. A string counts only if it shares
    a namespace with a key that does exist, or if the locale is flat and the
    string looks like an identifier rather than a sentence.
    """
    if "." in key:
        head = key.split(".")[0]
        return any(k.startswith(head + ".") for k in known)
    flat_locale = not any("." in k for k in known)
    return flat_locale and " " not in key
