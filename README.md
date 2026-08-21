# Philadelphia Rental License — Change Log

An append-only daily change log of every **Active** and **Expired** rental
license in Philadelphia, built from the Citys public open data
(`phl.carto.com` Business Licenses dataset).

## Why this exists

The Citys public property systems (Atlas, Property History, eCLIPSE) show
only a licenses **current** state. When a license expires and is later
renewed, the expired period is overwritten and disappears from every public
surface — there is no way, after the fact, to see that a property operated
on a lapsed license. This log preserves that history going forward by
recording each daily change.

## Files

- **`changes.ndjson`** — append-only. One JSON object per line, per detected
  change. Types: `initial` (baseline), `appeared`, `updated` (with a per-field
  `diff`), `left_set` (license left the Active/Expired set).
- **`state.json`** — last-known state of every tracked license (used to diff).
- **`latest.json`** — summary of the most recent run.

## Tracked fields

`licensestatus`, `expirationdate`, `mostrecentissuedate` (renewal date),
`inactivedate`, plus address / OPA account for identification.

## Source & method

Public data from `https://phl.carto.com/api/v2/sql`, rental licenses only,
status Active or Expired. Collected once daily. This is an independent
proof-of-concept; not affiliated with or endorsed by the City of Philadelphia.

Baseline captured 2026-08-21.
