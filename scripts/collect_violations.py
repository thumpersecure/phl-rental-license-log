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

# --- Feed-outage guard (see collect.py): mass non-null -> null on these fields
# is treated as a bad feed; prior values carried forward, one feed_anomaly logged.
GUARDED_FIELDS=["address","zip","opa_account_num","violationcode","violationcodetitle",
                "violationstatus","casestatus","casecreateddate","violationdate"]
ANOMALY_FRACTION=0.05
ANOMALY_MIN_COUNT=1000
# --- Size-aware file rolling: violations_changes.ndjson, then
# violations_changes-b.ndjson, -c ... never past MAX_FILE_BYTES.
MAX_FILE_BYTES=60*1000*1000
MAX_RUN_RECORDS=20000

def _vpath(i):
    if i==0: return VCHANGES
    base=VCHANGES[:-len(".ndjson")]
    return base+"-"+(chr(ord("a")+i) if i<26 else str(i+1))+".ndjson"

def append_records(records):
    written,f,size=[],None,0
    try:
        for rec in records:
            line=json.dumps(rec,separators=(",",":"))+"\n"; n=len(line.encode("utf-8"))
            if f is None or size+n>MAX_FILE_BYTES:
                if f: f.close()
                i=0
                while True:
                    path=_vpath(i); sz=os.path.getsize(path) if os.path.exists(path) else 0
                    if sz+n<=MAX_FILE_BYTES or sz==0: break
                    i+=1
                f,size=open(path,"a"),sz
                if path not in written: written.append(path)
            f.write(line); size+=n
    finally:
        if f: f.close()
    return written

def guard_feed(prev,cur):
    tracked=max(len(prev),1)
    nulled={k:[] for k in GUARDED_FIELDS}
    for key,c in cur.items():
        p=prev.get(key)
        if p is None: continue
        for k in GUARDED_FIELDS:
            if p.get(k) not in (None,"") and c.get(k) in (None,""): nulled[k].append(key)
    bad=[k for k,v in nulled.items() if len(v)>ANOMALY_MIN_COUNT or len(v)>ANOMALY_FRACTION*tracked]
    if not bad: return None
    aff=set()
    for k in bad:
        for key in nulled[k]:
            cur[key][k]=prev[key][k]; aff.add(key)
    return {"fields":bad,"affected":len(aff),"per_field":{k:len(nulled[k]) for k in bad},
            "note":"City feed returned null/empty for previously populated fields on a mass scale; "
                   "treated as a bad feed. Prior values carried forward, null updates NOT logged."}

def main():
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    prev=json.load(open(VSTATE)) if os.path.exists(VSTATE) else {}
    cur=fetch()
    if not cur: print("ERROR: 0 rows",file=sys.stderr); sys.exit(1)
    base=not prev; ch=[]
    anomaly=None if base else guard_feed(prev,cur)
    for k,c in cur.items():
        p=prev.get(k)
        if p is None: ch.append({"ts":now,"violationnumber":k,"change":"initial" if base else "new_violation","new":c})
        else:
            d={x:{"from":p.get(x),"to":c.get(x)} for x in F if p.get(x)!=c.get(x)}
            if d: ch.append({"ts":now,"violationnumber":k,"change":"updated","diff":d,"new":c})
    notes=[]
    if anomaly: notes.append({"ts":now,"change":"feed_anomaly",**anomaly})
    if not base and len(ch)>MAX_RUN_RECORDS:
        notes.append({"ts":now,"change":"large_run","records":len(ch),
                      "note":f"run produced more than {MAX_RUN_RECORDS} records; written in full, chunked across files"})
    if ch or notes: append_records(notes+ch)
    json.dump(cur,open(VSTATE,"w"),separators=(",",":"),sort_keys=True)
    s={"last_run":now,"tracked_violations":len(cur),"changes_this_run":len(ch),"baseline_run":base}
    if anomaly: s["feed_anomaly"]=anomaly
    json.dump(s,open(VLATEST,"w"),indent=2); print(json.dumps(s))

if __name__=="__main__":
    main()
