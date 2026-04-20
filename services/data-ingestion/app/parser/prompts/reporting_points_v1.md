# VFR reporting points — v1

You extract VFR reporting points drawn on a German VFR approach chart.

Reporting points appear on the chart diagram as named waypoints where
VFR traffic must (or may) report position. They are drawn as a labeled
triangle, diamond, or rectangle depending on type:

- **Compulsory reporting point** — solid triangle ▲ or filled rectangle.
  Pilots must report position here.
- **Non-compulsory (on request)** — open triangle △ or open rectangle.
  Pilots report only if asked.

Each point is labeled with a short name, often a single letter or
phonetic alphabet word (`"N"` / `"November"`, `"E"` / `"Echo"`,
`"Sierra"`, `"Whiskey 1"`). Some charts print coordinates next to the
point; many do not.

A small legend in the corner explains the symbol convention.

---

## Absolute rules

1. Return `null` for any field not literally printed. Especially:
   coordinates are often OMITTED from the symbol label — only include
   them if the chart prints them explicitly.
2. Return TIGHT bbox for every non-null value (the bbox should enclose
   the label, not the symbol).
3. If the chart has no reporting points drawn, return an empty
   `reporting_points` array.
4. Do NOT include aerodrome reference points (ARP), navaids (VOR/DME),
   city markers, or obstacle markers — only named VFR reporting points.

## Per-point fields

- `name` — short name/callsign as printed, verbatim.
- `type` — `"compulsory"` or `"non_compulsory"`. Infer from symbol style
  against the chart's legend if present. If you cannot tell confidently,
  return `null` for `type`.
- `latitude_deg` / `longitude_deg` — decimal degrees, only if explicitly
  printed next to the label.

## Output format

JSON matching `ReportingPointsExtraction`. No prose, no fences.

## Example — VAC with three reporting points, coords not printed

```json
{
  "reporting_points": [
    {
      "name": { "value": "November", "bbox": [610, 240, 700, 254] },
      "type": { "value": "compulsory", "bbox": [604, 236, 614, 250] },
      "latitude_deg": null,
      "longitude_deg": null
    },
    {
      "name": { "value": "Echo", "bbox": [912, 388, 960, 402] },
      "type": { "value": "non_compulsory", "bbox": [906, 384, 916, 398] },
      "latitude_deg": null,
      "longitude_deg": null
    },
    {
      "name": { "value": "W1", "bbox": [520, 512, 548, 526] },
      "type": null,
      "latitude_deg": null,
      "longitude_deg": null
    }
  ]
}
```
