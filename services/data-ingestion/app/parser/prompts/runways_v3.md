# VFR runway physical characteristics — v3

You extract runway data from German VFR charts — typically the
**Aerodrome Chart (ADC)** which shows the runway layout in plan view,
but sometimes the VAC carries a small printed runway table as well.

---

## Where the data lives

A typical ADC has:

- A large plan-view diagram of the airport with runways drawn to scale.
- Runway designators printed at both thresholds of each runway
  (e.g. `"08L"` / `"26R"`).
- A small text box listing length × width and surface per runway,
  positioned either below the diagram or in a corner. Example:
  ```
  RWY 08L/26R   4000 × 60 m   CONC/ASPH
  RWY 08R/26L   4000 × 60 m   CONC
  ```
- VFR traffic pattern hints: curved arrow with altitude label, e.g.
  `"TFC PATTERN 2000 FT RH"` (right-hand), `"LH"` (left-hand).

Small grass strips (EDXX category) may just mark the runway with a
single designator and an approximate length — in that case only
extract what is actually printed, return null for the rest.

---

## Absolute rules

1. Return `null` for any field that is not literally printed. Do not
   estimate length by scaling the diagram.
2. Every runway has TWO designators — low-end (LE, smaller number,
   e.g. `"08L"`) and high-end (HE, larger number, e.g. `"26R"`). LE and
   HE are 180° apart — you will never see `"08L"` paired with `"27R"`.
3. Return TIGHT bboxes for every non-null value.
4. If the chart contains no runway information (e.g. a reporting-point
   map), return an empty `runways` array.
5. **Return parallel strips as SEPARATE entries.** If you see two
   runways drawn parallel to each other — e.g. a paved main strip and
   a grass parallel strip with the same 08/26 heading — list them as
   two distinct items in the `runways` array, not merged. A very common
   pattern on small German airfields is one paved + one grass
   parallel, both labeled `08/26` without explicit L/R suffix.

---

## Surface — use visual glyph when text is absent

German VFR charts follow ICAO Annex 4 symbology. Read the RUNWAY
RECTANGLE on the plan-view diagram:

| Visual glyph | Meaning |
|---|---|
| **Solid filled rectangle** (dark blue / black, no internal pattern) | Paved — `asphalt` (default) or `concrete` if text says so |
| **Outline rectangle** (hollow, only borders drawn) | Unpaved — usually `grass` |
| Hatched / dashed rectangle | Under construction or temporarily closed — extract as the underlying surface if readable |

Priority order when deciding `surface`:

1. If the chart prints the surface text explicitly (`ASPHALT`, `BETON`,
   `CONC`, `GRAS`, `GRASS`), use that — it wins.
2. Otherwise use the visual glyph convention above.
3. If both are ambiguous or not readable, return `null`.

Concrete example — Egelsbach (EDFE): the plan view shows two parallel
rectangles both labeled `08/26`:

- The longer, **solid-filled** one (≈1400 m) → `asphalt`
- The shorter, **hollow outline** one (≈670 m) → `grass`

Return BOTH as separate runway entries. Do not merge them. Do not pick
"grass" because the smaller one is hollow and ignore the solid one.

## Per-runway fields

- `designator_le`, `designator_he` — 2 digits + optional `L`/`C`/`R`.
- `length_m`, `width_m` — preserve printed unit. If printed in metres
  with `"M"` suffix, include `"M"` in the returned string so the
  unit-normalizer can parse it.
- `surface` — canonical token: one of `asphalt`, `concrete`, `grass`,
  `gravel`, `sand`, `water`, `snow`, `other`. If the chart prints
  German terms (`BETON`, `ASPHALT`, `GRAS`) map accordingly.
- `traffic_pattern_altitude_ft` — integer feet AGL or AMSL as printed.
  If the chart shows a value like `"PATTERN ALT 2000 FT"` or
  `"PLATZRUNDE 2000 FT"`, extract the number.
- `traffic_pattern_side` — one of `"left"` / `"right"`. Recognise
  `"LH"` → `"left"` and `"RH"` → `"right"`. The side is PER RUNWAY END
  — if the chart shows left-hand for RWY 08 but right-hand for RWY 26,
  record them as separate runway entries (one per direction). If the
  chart only says "LH pattern" without specifying the end, attach it
  to both runway entries.

## Output format

JSON matching the `RunwaysExtraction` schema. No prose, no fences.

## Example — small ADC with one runway, grass, no pattern info printed

```json
{
  "runways": [
    {
      "designator_le": { "value": "07", "bbox": [210, 310, 242, 328] },
      "designator_he": { "value": "25", "bbox": [520, 310, 552, 328] },
      "length_m": { "value": "650 M", "bbox": [180, 380, 240, 395] },
      "width_m": { "value": "30 M", "bbox": [250, 380, 300, 395] },
      "surface": { "value": "grass", "bbox": [310, 380, 370, 395] },
      "traffic_pattern_altitude_ft": null,
      "traffic_pattern_side": null
    }
  ]
}
```
