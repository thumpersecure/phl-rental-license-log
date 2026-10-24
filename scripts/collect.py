#!/usr/bin/env python3
"""
phl-rental-license-log collector.

Pulls every Active/Expired RENTAL license from the City of Philadelphia's
public Carto SQL API, diffs each license against the last known state stored
in state.json, and appends a row for every license whose tracked fields changed
since the previous run.

CHANGE LOG LAYOUT (partitioned):
  changes/YYYY-MM.ndjson   -- append-only, one file per calendar month (UTC).
  changes.ndjson           -- FROZEN historical archive of everything logged
                              before partitioning began; never appended to again.
Partitioning keeps every file small: a single month -- even the February renewal
spike (~most of ~97k licenses expiring at once) -- stays well under GitHub's 50MB
warning / 100MB hard-push-block, which one ever-growing file would eventually hit.

REVERSAL FLAGGING:
  A status flip that reverts within REVERSAL_WINDOW_DAYS (e.g. Expired->Active->
  Expired) is often a City data-entry correction, not a real lapse -- the analyst
  at L&I confirmed live eCLIPSE sync errors during this investigation. We do NOT
  drop these (append-only integrity is the whole point); instead the second flip
  is annotated `"reversal_suspected": true` with the prior change's timestamp, so
  this remains the only public surface that can show a reversion happened at all.

Public open data only. No auth, no page scraping -- a handful of paginated
API calls to phl.carto.com per day.
"""
import json, os, sys, time, glob, urllib.parse, urllib.request, datetime

CARTO = "https://phl.carto.com/api/v2/sql"
REPO = os.environ.get("REPO_DIR", ".")
STATE_FILE = os.path.join(REPO, "state.json")            # last-known state per license
CHANGES_DIR = os.path.join(REPO, "changes")              # monthly partitions live here
LEGACY_CHANGES = os.path.join(REPO, "changes.ndjson")    # frozen pre-partition archive
LATEST_FILE = os.path.join(REPO, "latest.json")          # current snapshot summary
PAGE = 10000
REVERSAL_WINDOW_DAYS = 4   # a flip that reverts within this many days is flagged

# --- Feed-outage guard (2026-10-21 incident: City feed returned NULL address/zip/
# parcel/opa for ~99k licenses for a day). If, for a guarded field, more than
# ANOMALY_FRACTION of tracked licenses (or more than ANOMALY_MIN_COUNT licenses)
# would go from non-null to null/empty in one run, the feed is treated as bad:
# the prior values are carried forward (no null-ing updates logged, state not
# overwritten with nulls) and one `feed_anomaly` record is logged instead.
GUARDED_FIELDS = ["address", "zip", "parcel_id_num", "opa_account_num", "opa_owner"]
ANOMALY_FRACTION = 0.05
ANOMALY_MIN_COUNT = 1000

# --- Size-aware partitions. A month file is never grown past MAX_PARTITION_BYTES;
# further records roll to YYYY-MM-b.ndjson, -c, ... (GitHub hard limit is 100MB).
MAX_PARTITION_BYTES = 60 * 1000 * 1000
# A single run appending more than this many records (non-baseline) gets one
# `large_run` summary annotation first; records are still all written, chunked.
MAX_RUN_RECORDS = 20000

# Fields we track. A change in any of these emits a change record.
FIELDS = ["opa_account_num", "address", "zip", "licensestatus",
          "initialissuedate", "mostrecentissuedate", "expirationdate", "inactivedate",
          "numberofunits", "parcel_id_num", "rentalcategory", "opa_owner"]

# Fields added after the initial baseline. Old state.json records won't have
# these keys, so treat "key absent in old state" as "not a change" for them --
# otherwise the first run after adding them would emit a spurious "updated" for
# every existing license. Once written to state, they diff normally thereafter.
ADDITIVE_FIELDS = {"numberofunits", "parcel_id_num", "rentalcategory", "opa_owner"}

BASE_Q = ("SELECT licensenum,opa_account_num,address,zip,licensestatus,"
          "initialissuedate,mostrecentissuedate,expirationdate,inactivedate,"
          "numberofunits,parcel_id_num,rentalcategory,opa_owner "
          "FROM business_licenses "
          "WHERE licensetype='Rental' AND licensestatus IN ('Active','Expired') "
          "ORDER BY licensenum")

def q(sql):
    url = CARTO + "?" + urllib.parse.urlencode({"q": sql})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.load(r)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))

def fetch_all():
    rows, off = {}, 0
    while True:
        d = q(f"{BASE_Q} LIMIT {PAGE} OFFSET {off}")
        batch = d.get("rows", [])
        if not batch:
            break
        for r in batch:
            ln = r.get("licensenum")
            if ln:
                rows[ln] = {k: r.get(k) for k in FIELDS}
        off += PAGE
        if len(batch) < PAGE:
            break
    return rows

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def _suffix(i):
    """0 -> '', 1 -> '-b', 2 -> '-c' ... 25 -> '-z', 26 -> '-27', ..."""
    if i == 0:
        return ""
    return "-" + (chr(ord("a") + i) if i < 26 else str(i + 1))

def _partition_path(now_dt, i):
    return os.path.join(CHANGES_DIR, now_dt.strftime("%Y-%m") + _suffix(i) + ".ndjson")

def month_partitions(year, month):
    """All existing partition paths for a month, oldest first
    (YYYY-MM.ndjson, YYYY-MM-b.ndjson, ...). Backward compatible: a lone
    YYYY-MM.ndjson is returned exactly as before."""
    out = []
    for i in range(200):
        p = os.path.join(CHANGES_DIR, f"{year:04d}-{month:02d}{_suffix(i)}.ndjson")
        if os.path.exists(p):
            out.append(p)
    return out

def month_partition(now_dt):
    """Path of the partition currently being appended to for this month: the
    last existing one, or the next suffix if that one is at/over
    MAX_PARTITION_BYTES. e.g. changes/2026-08.ndjson (or 2026-08-b.ndjson)."""
    os.makedirs(CHANGES_DIR, exist_ok=True)
    existing = month_partitions(now_dt.year, now_dt.month)
    if not existing:
        return _partition_path(now_dt, 0)
    last = existing[-1]
    if os.path.getsize(last) >= MAX_PARTITION_BYTES:
        return _partition_path(now_dt, len(existing))
    return last

def append_records(now_dt, records):
    """Append records (dicts) as ndjson, never growing any partition past
    MAX_PARTITION_BYTES: rolls to -b, -c, ... as needed. Returns paths written."""
    os.makedirs(CHANGES_DIR, exist_ok=True)
    written, f, size = [], None, 0
    try:
        for rec in records:
            line = json.dumps(rec, separators=(",", ":")) + "\n"
            n = len(line.encode("utf-8"))
            if f is None or size + n > MAX_PARTITION_BYTES:
                if f:
                    f.close()
                i = 0
                while True:
                    path = _partition_path(now_dt, i)
                    sz = os.path.getsize(path) if os.path.exists(path) else 0
                    if sz + n <= MAX_PARTITION_BYTES or sz == 0:
                        break
                    i += 1
                f, size = open(path, "a"), sz
                if path not in written:
                    written.append(path)
            f.write(line)
            size += n
    finally:
        if f:
            f.close()
    return written

def recent_status_changes(now_dt):
    """Map licensenum -> (ts, from_status, to_status) for licensestatus changes
    seen within REVERSAL_WINDOW_DAYS, scanned from the current + previous month
    partitions only (cheap; a reversal by definition happened very recently).
    Used to flag quick flip-backs as suspected data reversions."""
    cutoff = now_dt - datetime.timedelta(days=REVERSAL_WINDOW_DAYS)
    files = []
    for delta_month in (0, 1):
        y, m = now_dt.year, now_dt.month - delta_month
        while m < 1:
            m += 12; y -= 1
        files.extend(month_partitions(y, m))
    recent = {}
    for p in files:
        with open(p) as f:
            for line in f:
                try:
                    ch = json.loads(line)
                except ValueError:
                    continue
                d = ch.get("diff", {})
                if "licensestatus" not in d:
                    continue
                try:
                    t = datetime.datetime.fromisoformat(ch["ts"])
                except (ValueError, KeyError):
                    continue
                if t >= cutoff:
                    # keep the most recent status change per license
                    prior = recent.get(ch["licensenum"])
                    if not prior or t >= prior[0]:
                        recent[ch["licensenum"]] = (t, d["licensestatus"]["from"], d["licensestatus"]["to"])
    return recent

def guard_feed(prev, cur):
    """Detect a bad feed (mass non-null -> null on GUARDED_FIELDS). Mutates `cur`
    in place, carrying prior values forward for the affected licenses/fields.
    Returns an annotation dict (fields, affected, note) or None if feed is sane."""
    tracked = max(len(prev), 1)
    nulled = {k: [] for k in GUARDED_FIELDS}
    for ln, c in cur.items():
        p = prev.get(ln)
        if p is None:
            continue
        for k in GUARDED_FIELDS:
            if p.get(k) not in (None, "") and c.get(k) in (None, ""):
                nulled[k].append(ln)
    bad = [k for k, v in nulled.items()
           if len(v) > ANOMALY_MIN_COUNT or len(v) > ANOMALY_FRACTION * tracked]
    if not bad:
        return None
    affected = set()
    for k in bad:
        for ln in nulled[k]:
            cur[ln][k] = prev[ln][k]
            affected.add(ln)
    return {"fields": bad, "affected": len(affected),
            "per_field": {k: len(nulled[k]) for k in bad},
            "note": "City feed returned null/empty for previously populated fields "
                    "on a mass scale; treated as a bad feed. Prior values carried "
                    "forward, null updates NOT logged."}

def main():
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    now = now_dt.isoformat()
    prev = load_json(STATE_FILE, {})
    cur = fetch_all()
    if not cur:
        print("ERROR: fetched 0 rows; aborting so we don't corrupt state", file=sys.stderr)
        sys.exit(1)

    baseline = not prev
    anomaly = None if baseline else guard_feed(prev, cur)
    recent_flips = recent_status_changes(now_dt) if not baseline else {}
    changes = []
    reversals = 0
    for ln, c in cur.items():
        p = prev.get(ln)
        if p is None:
            changes.append({"ts": now, "licensenum": ln,
                            "change": "initial" if baseline else "appeared",
                            "new": c})
        else:
            # For additive fields, if the key was never in old state, that's a
            # schema addition, not a real change -- skip it (see ADDITIVE_FIELDS).
            diff = {k: {"from": p.get(k), "to": c.get(k)}
                    for k in FIELDS
                    if p.get(k) != c.get(k)
                    and not (k in ADDITIVE_FIELDS and k not in p)}
            if diff:
                rec = {"ts": now, "licensenum": ln, "change": "updated",
                       "diff": diff, "new": c}
                # Reversal flag: this run flips licensestatus BACK to what a very
                # recent change had moved it away from -> likely a data correction,
                # not a genuine lapse. Annotate, don't drop.
                if "licensestatus" in diff:
                    flip = recent_flips.get(ln)
                    if flip and diff["licensestatus"]["to"] == flip[1] \
                            and diff["licensestatus"]["from"] == flip[2]:
                        rec["reversal_suspected"] = True
                        rec["reversal_of_ts"] = flip[0].isoformat()
                        reversals += 1
                changes.append(rec)
    # licenses that dropped out of the Active/Expired set (renewed away, closed, etc.)
    for ln, p in prev.items():
        if ln not in cur:
            changes.append({"ts": now, "licensenum": ln,
                            "change": "left_set", "last": p})

    notes = []
    if anomaly:
        notes.append({"ts": now, "change": "feed_anomaly", **anomaly})
    if not baseline and len(changes) > MAX_RUN_RECORDS:
        notes.append({"ts": now, "change": "large_run", "records": len(changes),
                      "note": f"run produced more than {MAX_RUN_RECORDS} records; "
                              "written in full, chunked across partition files"})
    written = append_records(now_dt, notes + changes) if (changes or notes) else []
    existing = month_partitions(now_dt.year, now_dt.month)
    current_part = written[-1] if written else (existing[-1] if existing else month_partition(now_dt))

    with open(STATE_FILE, "w") as f:
        json.dump(cur, f, separators=(",", ":"), sort_keys=True)

    summary = {"last_run": now, "tracked_licenses": len(cur),
               "changes_this_run": len(changes), "reversals_flagged": reversals,
               "baseline_run": baseline,
               **({"feed_anomaly": anomaly} if anomaly else {}),
               "current_partition": os.path.relpath(current_part, REPO)}
    with open(LATEST_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary))

if __name__ == "__main__":
    main()
