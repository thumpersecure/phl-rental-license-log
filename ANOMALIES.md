# Known data anomalies

This log is append-only and each partition is anchored to Bitcoin with OpenTimestamps. Existing lines in `changes/*.ndjson` are **never edited or deleted**; rewriting them would invalidate the `.ots` proofs. Problems are documented here (and, going forward, as `feed_anomaly` annotation records) instead. All figures below were computed directly from `changes/2026-10.ndjson`.

## 1. 2026-10-21: City feed returned NULLs for ~99,000 licenses

On 2026-10-21 (run at 13:44 UTC) the City's Carto feed returned `NULL` for `address`, `zip`, `parcel_id_num`, `opa_account_num` and `opa_owner` on nearly every rental license. The diff logic recorded this as a change.

| Measure | Count |
|:--|--:|
| `updated` records on 2026-10-21 (all of them null-setting) | **99,038** |
| ...that set `address`, `zip` and `parcel_id_num` to null | 99,038 |
| ...that also set `opa_account_num` and `opa_owner` to null | 98,968 |
| Distinct licenses affected | 99,038 |
| ...that also carry a genuine change in another field (status 122; issue/expiration dates 154; units 1; category 1; 230 records in total have at least one) | 230 |

The 70 licenses where only three fields were nulled already had blank OPA account/owner in the City data. Normal days have a few hundred `updated` records. Each bogus record's `diff` holds the real prior value in `from` (for example `address: {"from":"509-19 VINE ST","to":null}`), so nothing is lost.

The 122 genuine status flips that happened to fall on 2026-10-21 are mixed into those records. They are real and the lapse reconstruction still uses them. Only the null-setting fields are artifacts.

The log shows no later restoration for these licenses: only 2 `updated` records afterwards set one of those fields from null back to a value. The City's data came back the next day, but the unpublished 2026-10-22 state absorbed the restoration (see section 2), so the published log never records it. Treat the nulls as artifacts, not as the licenses' real state.

**How `index.html` handles it:** for `updated` records dated 2026-10-21 that null those five fields, the search page hides the "changed to blank" diff and shows a "City feed outage 2026-10-21 (not a real change)" badge. Such records are excluded from change counts and type filters. A license's address/ZIP/OPA/owner is always shown using its last non-null value in the log. Lapse (expired/renewed/days lapsed) logic is unchanged.

## 2. 2026-10-22: no log entries (push failed)

The 2026-10-22 daily run completed locally but its push was rejected: `changes/2026-10.ndjson` had grown to ~139 MB, over GitHub's 100 MB per-file limit (the 99,038 bogus records are most of that growth). Consequently:

- `changes/` has **no records timestamped 2026-10-22** (confirmed: the days present are ...10-20, 10-21, 10-23, 10-24).
- The next published run, 2026-10-23, diffed against the unpublished 2026-10-22 state, not against the published 2026-10-21 state.
- **Genuine license transitions (Active to Expired, Expired to Active, new, left-set) that occurred between the 2026-10-21 and 2026-10-22 runs were not captured with their true date.** Their effects show up on 2026-10-23 where they changed anything the log tracks, but any lapse that opened or closed on 10-22 is dated 10-23, and days-lapsed figures spanning that date can be off by about a day. A transition that began and reversed within that window was never seen.

### Did 2026-10-23 absorb 2026-10-22 changes?

Probably yes, though the data cannot prove it. 2026-10-23 has 519 records (338 updated, 140 appeared, 41 left_set), and it does not look like a doubled day (other recent days: 10-16 405, 10-17 395, 10-18 231, 10-19 322, 10-20 587, 10-24 414). Indicators:

- 165 of the 338 `updated` records moved `mostrecentissuedate` to a date of 2026-10-22, and 62 more to 2026-10-21.
- 122 `appeared` records have `mostrecentissuedate` and 71 have `initialissuedate` dated 2026-10-22, i.e. licenses issued the day the log is missing.
- Status flips on 10-23: 131 (80 Active to Expired, 51 Expired to Active), within the 67-155 range of nearby days.

These are consistent with 2026-10-23 carrying changes made on both 10-22 and 10-23, but a precise split is not possible from the log.

## 3. Why the log was not rewritten

The partitions are anchored to Bitcoin via OpenTimestamps. Deleting or editing the bogus lines would break the proofs and the tamper-evidence that makes the log usable in court. The anomaly is instead documented here and annotated with `feed_anomaly` records (`ts`, `note`, `affected`, `fields`), which the search page shows as a grey "City data outage - not a real change" notice. Because of the file-size problem, new partitions are rolled by size (`changes/YYYY-MM-b.ndjson`, `-c`, ...); the page loads them all.

## 4. Verifying against current City data

To check a license, query the City's Carto API directly (public, no auth). Example for license 0952885:

```
https://phl.carto.com/api/v2/sql?q=SELECT licensenum,address,zip,opa_account_num,opa_owner,licensestatus,mostrecentissuedate,expirationdate FROM business_licenses WHERE licensetype='Rental' AND licensenum='0952885'
```

Count rows the City still reports with a blank address (should be small, normal background):

```
https://phl.carto.com/api/v2/sql?q=SELECT count(*) FROM business_licenses WHERE licensetype='Rental' AND licensestatus IN ('Active','Expired') AND address IS NULL
```

To check the nulling locally:

```
python3 - <<'PY'
import json
n=sum(1 for l in open('changes/2026-10.ndjson')
      if (o:=json.loads(l))['change']=='updated' and o['ts'][:10]=='2026-10-21'
      and o['diff'].get('address',{}).get('to','x') is None)
print(n)   # 99038
PY
```
