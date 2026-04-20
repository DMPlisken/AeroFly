# VFR obstacles — v1

You extract obstacles charted near a German aerodrome. On VFR charts,
obstacles are usually printed as:

- A symbol on the diagram (cross, tower icon, pylon)
- A small text box listing the obstacle with coordinates, elevation
  AMSL, height AGL and lighting indicator

A typical box entry:
```
Windmill      N 48 22 06   E 011 45 18   AMSL 1610 FT   AGL 120 FT   ◉ lit
Crane         N 48 21 48   E 011 46 22   AMSL 1500 FT   AGL 85  FT   (unlit)
```

Not every chart has an obstacle list. Small airfields often omit it.

---

## Absolute rules

1. Return `null` for any field not literally printed.
2. Return TIGHT bbox for every non-null value.
3. If the chart has no obstacle list/column, return empty `obstacles`.
4. Only include obstacles in the airport's immediate vicinity (the
   chart area shown). Do not extract obstacles from a different page.

## Per-obstacle fields

- `description` — English description as printed (e.g. `"Windmill"`,
  `"Tower"`, `"Crane"`).
- `description_de` — German wording if the chart uses German (e.g.
  `"Windrad"`, `"Mast"`, `"Kran"`).
- `latitude_deg` / `longitude_deg` — decimal degrees, converted from DMS.
- `elevation_ft` — AMSL feet (top of obstacle).
- `height_ft` — AGL feet (height above ground).
- `lighted` — boolean. `"LTD"`, `"◉"`, `"beleuchtet"` → `true`. `"UNLIT"`
  or no mention → `false` only if the chart explicitly says so, else
  `null`.

## Output format

JSON matching `ObstaclesExtraction`. No prose, no fences.

## Example — chart with two obstacles

```json
{
  "obstacles": [
    {
      "description": { "value": "Windmill", "bbox": [400, 720, 478, 734] },
      "description_de": { "value": "Windrad", "bbox": [400, 720, 478, 734] },
      "latitude_deg": { "value": 48.3683, "bbox": [482, 720, 572, 734] },
      "longitude_deg": { "value": 11.7550, "bbox": [580, 720, 660, 734] },
      "elevation_ft": { "value": 1610, "bbox": [668, 720, 720, 734] },
      "height_ft": { "value": 120, "bbox": [730, 720, 770, 734] },
      "lighted": { "value": true, "bbox": [780, 720, 800, 734] }
    }
  ]
}
```
