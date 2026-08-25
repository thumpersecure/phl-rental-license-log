# Adds a second collector: rental-license violations (9-3902), full history.
# Unlike licenses, violations persist -- so this is a real historical archive,
# not just a forward-capture. We snapshot the whole set and diff.
import json, os, sys, time, urllib.parse, urllib.request, datetime
CARTO="https://phl.carto.com/api/v2/sql"
REPO=os.environ.get("REPO_DIR",".")
VSTATE=os.path.join(REPO,"violations_state.json")
VCHANGES=os.path.join(REPO,"violations_changes.ndjson")
VLATEST=os.path.join(REPO,"violations_latest.json")
PAGE=10000
F=["casenumber","opa_account_num","address","zip","violationdate","violationcode",
   "violationcodetitle","violationstatus","violationresolutiondate","casestatus",
   "casecreateddate","casecompleteddate","underappeal","publicnov"]
BASE=("SELECT violationnumber,"+",".join(F)+" FROM violations "
      "WHERE violationcode LIKE '9-3902%' ORDER BY violationnumber")
def q(sql):
    u=CARTO+"?"+urllib.parse.urlencode({"q":sql})
    for a in range(4):
        try:
            with urllib.request.urlopen(u,timeout=120) as r: return json.load(r)
        except Exception:
            if a==3: raise
            time.sleep(5*(a+1))
def fetch():
    rows,off={},0
    while True:
        d=q(f"{BASE} LIMIT {PAGE} OFFSET {off}")
        b=d.get("rows",[])
        if not b: break
        for r in b:
            k=r.get("violationnumber")
            if k: rows[k]={x:r.get(x) for x in F}
        off+=PAGE
        if len(b)<PAGE: break
    return rows
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
prev=json.load(open(VSTATE)) if os.path.exists(VSTATE) else {}
cur=fetch()
if not cur: print("ERROR: 0 rows",file=sys.stderr); sys.exit(1)
base=not prev; ch=[]
for k,c in cur.items():
    p=prev.get(k)
    if p is None: ch.append({"ts":now,"violationnumber":k,"change":"initial" if base else "new_violation","new":c})
    else:
        d={x:{"from":p.get(x),"to":c.get(x)} for x in F if p.get(x)!=c.get(x)}
        if d: ch.append({"ts":now,"violationnumber":k,"change":"updated","diff":d,"new":c})
if ch:
    with open(VCHANGES,"a") as f:
        for c in ch: f.write(json.dumps(c,separators=(",",":"))+"\n")
json.dump(cur,open(VSTATE,"w"),separators=(",",":"),sort_keys=True)
s={"last_run":now,"tracked_violations":len(cur),"changes_this_run":len(ch),"baseline_run":base}
json.dump(s,open(VLATEST,"w"),indent=2); print(json.dumps(s))
