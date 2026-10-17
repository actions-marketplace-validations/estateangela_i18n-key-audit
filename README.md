# i18n-key-audit

**Find the translation problems that never fail a build.**

Three of them, and none shows up as an error:

* a key referenced in code that no locale defines — the user reads
  `home.subtitle` instead of a sentence
* a key in the base locale that another locale never got — that feature
  silently stays English for everyone else
* a key nobody references any more — translated, paid for, never rendered

Standard library Python, no dependencies, works on any project with JSON
translation files.

```
1093 keys in app/i18n/locales/en.json
  reference style   mixed (1344 source files)
  missing           7   <- rendered as a raw key
      Encryption_keys_failed
      Invalid_email
      Push_consumption_alert_title
  locales w/ gaps   66/66
      app/i18n/locales/nn.json  600 missing
      app/i18n/locales/es.json  546 missing
  possibly unused   342 (watch out: 2 runtime-built keys)
```

That is a real run against
[Rocket.Chat.ReactNative](https://github.com/RocketChat/Rocket.Chat.ReactNative).
`I18n.t('Invalid_email')` is shown on the registration screen and the key is
not in `en.json`.

## Use as a GitHub Action

```yaml
- uses: actions/checkout@v4
- uses: estateangela/i18n-key-audit@v1
  id: i18n
  with:
    app: .
    fail-on: missing          # a raw key on screen is always a bug
    comment-file: i18n.md
- run: echo "${{ steps.i18n.outputs.locales-with-gaps }} locales need work"
```

### Inputs

| Input | Default | Description |
|---|---|---|
| `app` | `.` | Project root. |
| `locales` | auto | Globs for the translation files, newline or comma separated. |
| `base` | English, else largest | The reference locale. |
| `source` | all | Globs for the sources to scan. |
| `json-file` | — | Write the full report. |
| `csv-file` | — | Per-locale summary. |
| `comment-file` | — | Markdown for a PR comment. |
| `fail-on` | `none` | `missing`, `gaps`, `any`, or `none`. |

### Outputs

`missing`, `locales-with-gaps`, `locales`, `unused`, `base`, `json`, `comment`.

## Use as a CLI

```bash
git clone https://github.com/estateangela/i18n-key-audit
cd i18n-key-audit
python3 -m i18n_key_audit --app ~/code/my-app
python3 -m i18n_key_audit --app ~/code/my-app --fail-on missing
```

## How certain each finding is

They are ranked by confidence, not by count, because they do not deserve the
same trust.

| Finding | Confidence | Why |
|---|---|---|
| **missing** | certain | A literal key passed to `t()` that no locale defines. Always a bug. |
| **locale gaps** | certain | Pure comparison of two JSON files. No source analysis, so nothing to get wrong. |
| **untranslated** | a hint | Present, but identical to the base text. Often legitimate — `OK` is `OK` in many languages. |
| **possibly unused** | advisory | Keys can be assembled at runtime. The count of such call sites is printed next to it. **Read it before deleting anything.** |

`fail-on: missing` is the setting worth putting in CI. `gaps` only suits a
team that keeps every locale complete; anyone mid-translation would never
get a green run.

## What it understands

```tsx
t('home.title')              i18n.t("home.title")     $t('home.title')
__('home.title')             intl.formatMessage({ id: 'home.title' })
loc.home.title               strings.home.title
```

A property chain counts only when it resolves to a key that exists, so the
i18n object can be called anything and `props.navigation.navigate` is never
mistaken for a translation. Nested and flat JSON both work.

Test files (`*.test.*`, `__tests__/`, `*.stories.*`) are skipped: they invent
key-shaped strings, and counting those reported 144 missing keys in a project
that had 7.

## Measured, not assumed

The design came from cloning three projects and counting, before writing the
analysis:

| Project | Style | Keys | Missing | Locales with gaps |
|---|---|--:|--:|---|
| [BlueWallet](https://github.com/BlueWallet/BlueWallet) | property | 686 | 0 | 67 / 70 |
| [Rocket.Chat.ReactNative](https://github.com/RocketChat/Rocket.Chat.ReactNative) | mixed | 1093 | 7 | 66 / 66 |
| [Excalidraw](https://github.com/excalidraw/excalidraw) | mixed | 639 | 0 | 57 / 57 |

Three things that changed the design:

1. **Locale gaps are universal.** Every non-base locale in every project was
   missing keys. That check needs no source analysis at all, so it leads.
2. **Projects mix reference styles.** One had 521 call-style and 561
   property-style references in the same codebase. Supporting one style
   reported 686 keys as unused in a project where the real figure was 17 —
   and someone acting on that would have deleted live translations.
3. **A barely-started locale must not be filtered out.** Dropping files with
   too few keys to look like translations discarded 42 of 67 locale files in
   one project — precisely the ones a translation manager needs to see.

## Development

```bash
python3 -m unittest discover -s tests -t . -v     # 18 tests, no dependencies
```

Every test case is drawn from an answer this tool got confidently wrong
first.

## License

MIT
