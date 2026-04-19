# Golden Fixtures for Chart Extraction

These YAML files are the ground truth against which the extraction
pipeline is measured. Every F1 score in CI comes from this directory.

## Status

This directory contains **5 draft labels** for the Phase 0 spike. They
are based on publicly-known data about the listed airports and need
**pilot verification** before the pipeline is gated on them.

For Phase 2 (the real F1-gate), we need 30 fully-labelled fixtures:
10 international, 10 regional, 5 GA, 3 military-mixed, 2 special cases.

## Format

Each `.labels.yaml` corresponds to one AD-2 preview PNG in
`data/aerodromes/<ICAO>/` (chart whose `dfs_name` starts with "AD 2-").

```yaml
icao: EDDM
source_chart: AD_2-<NN>_print.png
source_airac_cycle: 2026-04
geo:
  latitude_deg: 48.3538
  longitude_deg: 11.7861
  elevation_ft: 1487
  ...
runways:
  - designator_le: "08L"
    designator_he: "26R"
    length_m: 4000
    ...
frequencies:
  - type: twr
    callsign_de: "München Turm"
    frequency_mhz: "118.700"
    ...
```

Fields set to `null` mean "the AIP shows no value there"; fields set
to `"unverified"` mean "value not yet checked by a pilot reviewer".

## Process for approval

1. A pilot opens `data/aerodromes/<ICAO>/AD_2-*_print.png`
2. Compares every field in the corresponding `.labels.yaml`
3. Edits any incorrect value, adds missing ones, removes halluczinated ones
4. Replaces `"unverified"` markers with actual values or `null`
5. Adds `approved_by: <initials>` and `approved_at: <date>` at the top
6. Opens a PR for review by a second pilot

No extraction pipeline will be graded against a fixture that lacks an
`approved_by` line.
