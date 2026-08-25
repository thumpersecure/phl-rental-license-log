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

def month_partition(now_dt):
    """Path of the current month's change partition, e.g. changes/2026-08.ndjson."""
    os.makedirs(CHANGES_DIR, exist_ok=True)
    return os.path.join(CHANGES_DIR, now_dt.strftime("%Y-%m") + ".ndjson")

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
        p = os.path.join(CHANGES_DIR, f"{y:04d}-{m:02d}.ndjson")
        if os.path.exists(p):
            files.append(p)
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

def main():
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    now = now_dt.isoformat()
    prev = load_json(STATE_FILE, {})
    cur = fetch_all()
    if not cur:
        print("ERROR: fetched 0 rows; aborting so we don't corrupt state", file=sys.stderr)
        sys.exit(1)

    baseline = not prev
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

    if changes:
        part = month_partition(now_dt)
        with open(part, "a") as f:
            for ch in changes:
                f.write(json.dumps(ch, separators=(",", ":")) + "\n")

    with open(STATE_FILE, "w") as f:
        json.dump(cur, f, separators=(",", ":"), sort_keys=True)

    summary = {"last_run": now, "tracked_licenses": len(cur),
               "changes_this_run": len(changes), "reversals_flagged": reversals,
               "baseline_run": baseline,
               "current_partition": os.path.relpath(month_partition(now_dt), REPO)}
    with open(LATEST_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary))

if __name__ == "__main__":
    main()
