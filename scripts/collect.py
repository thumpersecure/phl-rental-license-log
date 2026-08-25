#!/usr/bin/env python3
"""
phl-rental-license-log collector.

Pulls every Active/Expired RENTAL license from the City of Philadelphia's
public Carto SQL API, diffs each license against the last known state stored
in state.json, and appends a row to changes.ndjson for every license whose
tracked fields changed since the previous run. First run writes a baseline
(every license recorded as an "initial" observation).

Public open data only. No auth, no scraping of pages — a handful of paginated
API calls to phl.carto.com per day.
"""
import json, os, sys, time, urllib.parse, urllib.request, datetime

CARTO = "https://phl.carto.com/api/v2/sql"
REPO = os.environ.get("REPO_DIR", ".")
STATE_FILE = os.path.join(REPO, "state.json")          # last-known state per license
CHANGES_FILE = os.path.join(REPO, "changes.ndjson")    # append-only change log
LATEST_FILE = os.path.join(REPO, "latest.json")        # current snapshot summary
PAGE = 10000

# Fields we track. A change in any of these emits a change record.
FIELDS = ["opa_account_num", "address", "zip", "licensestatus",
          "initialissuedate", "mostrecentissuedate", "expirationdate", "inactivedate"]

BASE_Q = ("SELECT licensenum,opa_account_num,address,zip,licensestatus,"
          "initialissuedate,mostrecentissuedate,expirationdate,inactivedate "
          "FROM business_licenses "
          "WHERE licensetype='Rental' AND licensestatus IN ('Active','Expired') "
          "ORDER BY licensenum")

def q(sql):
    url = CARTO + "?" + urllib.parse.urlencode({"q": sql})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.load(r)
        except Exception as e:
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

def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    prev = load_json(STATE_FILE, {})
    cur = fetch_all()
    if not cur:
        print("ERROR: fetched 0 rows; aborting so we don't corrupt state", file=sys.stderr)
        sys.exit(1)

    baseline = not prev
    changes = []
    for ln, c in cur.items():
        p = prev.get(ln)
        if p is None:
            changes.append({"ts": now, "licensenum": ln,
                            "change": "initial" if baseline else "appeared",
                            "new": c})
        else:
            diff = {k: {"from": p.get(k), "to": c.get(k)}
                    for k in FIELDS if p.get(k) != c.get(k)}
            if diff:
                changes.append({"ts": now, "licensenum": ln,
                                "change": "updated", "diff": diff, "new": c})
    # licenses that dropped out of the Active/Expired set (renewed away, closed, etc.)
    for ln, p in prev.items():
        if ln not in cur:
            changes.append({"ts": now, "licensenum": ln,
                            "change": "left_set", "last": p})

    if changes:
        with open(CHANGES_FILE, "a") as f:
            for ch in changes:
                f.write(json.dumps(ch, separators=(",", ":")) + "\n")

    with open(STATE_FILE, "w") as f:
        json.dump(cur, f, separators=(",", ":"), sort_keys=True)

    summary = {"last_run": now, "tracked_licenses": len(cur),
               "changes_this_run": len(changes), "baseline_run": baseline}
    with open(LATEST_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary))

if __name__ == "__main__":
    main()
