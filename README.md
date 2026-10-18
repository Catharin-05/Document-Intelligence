# Bid-item judge

Checks the scope items (bid items) in a `results.json` against the drawings PDF. Each item is judged **right** or **wrong**:
does the text the item points at really support the work it names? Wrong items are removed from a corrected copy of
`results.json`, and every item gets a row in a findings spreadsheet with the verdict and the reason.

A Gemini vision model (`gemini-3.8-flash`) does most of the judging. It sees the sheet with the item's regions drawn
in red, the region texts, and the lines of the project legend that match the item's codes.

## Files

| File | What it does |
|---|---|
| `config.yaml` | **The only config**: paths, model, triage switches, filters |
| `judge.py` | Main script: legend, judge, export |
| `triage.py` | Cheap steps before the model: rules, legend lookup, legend trimming |
| `legend.py` | Turns the legend sheets into text (abbreviations and wall types) |
| `prompts/judge.md` | The single prompt (rules + legend + item) |
| `review.py` | Builds a review PDF from the findings sheet and reads your notes back |
| `requirements.txt` | Python packages |
| `annotate_pdf.py`, `visualize_regions.py` | Older helpers that draw items/regions on the sheets (not needed to run) |

## Setup (once)

```
pip install -r requirements.txt
```

Put the inputs in `data/` (or change `paths` in `config.yaml`):

```
data/results.json
data/drawings.pdf
```

Set your API key in the same PowerShell window you run from:

```
$env:GEMINI_API_KEY="your-key"
```

## Run

```
py .\judge.py
```

This does three steps (`run`): extract the legend, judge every item, export. It writes to `output/run1/`:

| Output | Meaning |
|---|---|
| `results.corrected.json` | Same structure as the input, wrong items removed, `scopes` kept in sync |
| `findings.xlsx` | One row per judged item: sheet, package, item, verdict, category, reason, confidence, who decided it, your columns |
| `legend.txt` | The legend text sent to the model (read it once; fix it if it looks wrong) |
| `cache/` | One saved verdict per item (this is what makes re-runs cheap) |
| `evidence/`, `prompts/` | The image and the exact prompt used for each item |

Individual steps:

```
py .\judge.py legend      # only extract the legend -> output\run1\legend.txt
py .\judge.py judge       # only judge
py .\judge.py export      # only rebuild the JSON and the spreadsheet from saved verdicts
py .\judge.py models      # list the Gemini models your key can use
```

Handy options (any config value can be overridden with `--set key=value`):

```
py .\judge.py --set filters.limit=5                      # only the first 5 items (a cheap test)
py .\judge.py --set filters.sheets=[A-421]               # only one sheet
py .\judge.py --set model.name=gemini-3.8-flash
py .\judge.py --force                                    # re-judge everything
py .\judge.py --mock                                     # no API; fake heuristic verdicts to test the plumbing
py .\judge.py --config other.yaml
```

## How an item is judged

1. **Rules (no model call).** Text that is only a URL/e-mail, only bare numbers/dimensions with no letters, or a
   grid-bubble pattern is marked wrong. These rules are strict on purpose, so they decide very few items.
2. **Legend lookup (no model call).** If every text is a single legend code whose defined meaning matches the item,
   it is marked right.
3. **Text-only call** (when `triage.text_first: true`). Items with long text go to the model without the image first.
   A confident answer stands.
4. **Image call.** Short tags (about 20 characters or less, like `P-1`), unsure answers and items flagged for review go
   to the model with the sheet image. Set `text_first: false` to send every item with its image.

Each prompt contains only the legend lines whose code appears in that item (`triage.trim_legend`).
The `decided_by` column in `findings.xlsx` shows which step decided each item (`rule`, `legend`, `text`, `image`).

## Settings you will use (`config.yaml`)

```yaml
model:
  provider: gemini
  name: gemini-3.8-flash          # the model id; `py judge.py models` lists the ones your key can use
  fallback_names: []              # tried in order when the daily quota of `name` runs out
  min_seconds_between_calls: 0    # set e.g. 6-8 on a free tier with per-minute limits
  workers: 4

triage:
  rules: true
  legend_auto: true
  trim_legend: true
  text_first: true                # false = every item judged with its image

filters:
  sheets: []                      # e.g. [A-421]
  limit: null                     # e.g. 5
```

## Free tiers and quotas

A free Gemini key allows about 20 calls per day per model, so a full run will stop part-way. Turning on billing for the key removes that limit. A stop is safe:

- The run stops cleanly and prints `INCOMPLETE: x of y items have a verdict`.
- Verdicts are cached. Run the same command later and it continues where it stopped.
- The corrected JSON and the spreadsheet only reflect the items judged so far. **Items without a verdict are kept
  as they are**, so do not treat a partial run as final.

A cached verdict is reused only if the prompt file, the legend, the model name and the `triage` settings are
unchanged, so do not change them between runs of the same job. `--force` re-judges everything.
Cached verdicts are matched by sheet, scope package and the item's position in its list, so keep the same `results.json`.

## Checking the results by hand

```
py .\review.py build --xlsx .\output\run1\findings.xlsx
```

Writes `review.pdf` next to the spreadsheet: one page per row, with the sheet and the item's regions in red on the
left, and on the right the item, the model's verdict (and whether it is removed), the reason, the region texts, and
two fields for you: **Your verdict** (`right`/`wrong`) and **Your notes**. Options: `--only wrong` (just removed items),
`--only review` (removed or flagged).

Open it in Acrobat Reader or Edge, fill in the fields, **save the PDF**, then:

```
py .\review.py import --xlsx .\output\run1\findings.xlsx    # writes your entries into human_verdict / human_note
py .\judge.py export                                        # applies them: final_verdict + results.corrected.json
```

You can also type straight into the `human_verdict` / `human_note` columns of `findings.xlsx` instead. Your verdict
overrides the model's. Close `findings.xlsx` in Excel before running anything that writes it; otherwise the export saves
a numbered copy (`findings_HHMMSS.xlsx`).

## Running on a new set of sheets

Give it the new files and a fresh output folder, so the old cache is not mixed in:

```
py .\judge.py --set paths.results=data\new_results.json --set paths.pdf=data\new_drawings.pdf --set paths.out_dir=output\new
```

If the new set does not contain the legend sheets (G-002.3, G-501, G-511), reuse the legend from the first run:

```
... --set legend.file=output\run1\legend.txt
```

If the legend sheets have different numbers, change `legend.sheets` in `config.yaml`.

## How the corrected `results.json` is made

- Items judged wrong (or marked wrong by you) are removed from `bid_items`; every other item is copied unchanged.
- In `scopes`, a region is removed only if it belonged to a removed item and no kept item in the same package uses it.
  Scope entries left with no regions, and packages left with no items, are dropped.
- The three legend sheets are never judged and are left untouched.

## Known limits

- The model only decides right or wrong; it does not edit items.
- Whether a bare tag (like `BR1`) counts depends on the prompt's wording; room data tags and floating tags are treated
  as labels, product tags attached to an element and defined in the legend are treated as real.
- The legend text comes from the PDF text layer and is imperfect for wall-type cells; check `legend.txt`.
- Pages stored rotated (`/Rotate 270`) are handled for text lookups; `quad_px` is always in the page as displayed.
- The specification book is not used.
- Verdicts are only as good as the model. Spot-check them with the review PDF.