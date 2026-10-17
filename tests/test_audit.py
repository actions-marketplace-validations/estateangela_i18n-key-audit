"""Tests for the cases that actually went wrong while building this.

Every one of them produced a confident, wrong answer first.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from i18n_key_audit.locales import compare, discover, flatten, pick_base
from i18n_key_audit.report import build, to_markdown
from i18n_key_audit.usage import scan

FIXTURE = Path(__file__).parent / "fixtures" / "sample"


def analyse(**kw):
    locales = discover(FIXTURE, **kw)
    base = pick_base(locales)
    usage = scan(FIXTURE, base.keys)
    gaps = compare(base, [l for l in locales if l.path != base.path])
    return build(base, usage, gaps)


class Discovery(unittest.TestCase):
    def test_nearly_empty_locale_is_kept(self):
        """A locale with four keys is the one most worth reporting. Filtering
        file by file on a minimum key count dropped exactly those -- 42 of
        67 files in one real project."""
        names = {Path(l.path).name for l in discover(FIXTURE)}
        self.assertIn("zh-TW.json", names)

    def test_base_prefers_english(self):
        self.assertEqual(Path(pick_base(discover(FIXTURE)).path).name, "en.json")

    def test_flatten_builds_dotted_keys(self):
        self.assertEqual(flatten({"a": {"b": "c"}}), {"a.b": "c"})

    def test_non_string_leaves_are_ignored(self):
        self.assertEqual(flatten({"a": 1, "b": "x", "c": [1]}), {"b": "x"})


class MissingKeys(unittest.TestCase):
    def test_key_used_in_code_but_undefined(self):
        r = analyse()
        self.assertIn("home.subtitle_that_does_not_exist", r.missing)

    def test_test_files_do_not_contribute(self):
        """Test files invent key-shaped strings. Counting them produces
        confident nonsense -- it reported 144 missing keys in a real project
        where there were 7."""
        r = analyse()
        self.assertNotIn("totally.made.up.in.a.test", r.missing)

    def test_unrelated_namespace_is_not_treated_as_a_key(self):
        from i18n_key_audit.usage import _looks_like_a_key
        known = {"home.title": "Home"}
        self.assertTrue(_looks_like_a_key("home.missing", known))
        self.assertFalse(_looks_like_a_key("router.push", known))


class LocaleGaps(unittest.TestCase):
    def test_missing_keys_per_locale(self):
        r = analyse()
        zh = next(g for g in r.gaps if g.locale.endswith("zh-TW.json"))
        self.assertEqual(len(zh.missing), 2)
        self.assertFalse(zh.complete)

    def test_complete_locale_reports_no_gap(self):
        r = analyse()
        de = next(g for g in r.gaps if g.locale.endswith("de.json"))
        self.assertTrue(de.complete)

    def test_extra_keys_are_reported_separately(self):
        r = analyse()
        de = next(g for g in r.gaps if g.locale.endswith("de.json"))
        self.assertIn("extra.only_here", de.extra)

    def test_copied_but_untranslated_text(self):
        """Same string as the base locale: often fine, often a placeholder
        someone never came back to. Reported, not counted as missing."""
        r = analyse()
        zh = next(g for g in r.gaps if g.locale.endswith("zh-TW.json"))
        self.assertIn("home.greeting", zh.untranslated)
        self.assertNotIn("home.greeting", zh.missing)


class UsageStyles(unittest.TestCase):
    def test_both_reference_styles_are_counted(self):
        """One real project used 521 call-style and 561 property-style
        references in the same codebase."""
        r = analyse()
        self.assertEqual(r.style, "mixed")

    def test_property_access_marks_a_key_as_used(self):
        r = analyse()
        self.assertNotIn("errors.network", r.unused)
        self.assertNotIn("common.cancel", r.unused)

    def test_truly_unused_key_is_reported(self):
        self.assertIn("legacy.removed", analyse().unused)

    def test_runtime_built_keys_are_counted(self):
        """They cannot be resolved, so `unused` is advice, not a fact."""
        self.assertEqual(analyse().dynamic_sites, 1)


class Markdown(unittest.TestCase):
    def test_marker_present_for_updating_a_comment(self):
        self.assertIn("<!-- i18n-key-audit -->", to_markdown(analyse()))

    def test_dynamic_keys_are_disclosed_next_to_the_unused_count(self):
        md = to_markdown(analyse())
        self.assertIn("runtime", md)

    def test_clean_project_says_so(self):
        r = analyse()
        r.missing, r.gaps = [], []
        self.assertIn("look complete", to_markdown(r))


if __name__ == "__main__":
    unittest.main()
