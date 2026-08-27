<div align="center">

# 🏛️ PHL RENTAL LICENSE — CHANGE LOG

### *The history Philadelphia's public systems throw away.*

[![Live](https://img.shields.io/badge/STATUS-LIVE-00d26a?style=for-the-badge&logo=githubpages&logoColor=white)](https://thumpersecure.github.io/phl-rental-license-log/)
[![Licenses](https://img.shields.io/badge/TRACKED-96%2C879_LICENSES-1a5fb4?style=for-the-badge)](https://thumpersecure.github.io/phl-rental-license-log/latest.json)
[![Violations](https://img.shields.io/badge/ARCHIVED-25%2C946_VIOLATIONS-8b5cf6?style=for-the-badge)](https://thumpersecure.github.io/phl-rental-license-log/violations_latest.json)
[![Data](https://img.shields.io/badge/SOURCE-CITY_OPEN_DATA-a51d2d?style=for-the-badge)](https://phl.carto.com/api/v2/sql)
[![Updated](https://img.shields.io/badge/UPDATES-DAILY_04%3A15_ET-f5a97f?style=for-the-badge&logo=clockify&logoColor=white)](#-how-it-works)

**`Every Active + Expired rental license, diffed daily. Every §9-3902 violation since 2010.`**

</div>

---

## 🎬 What The City Keeps &mdash; And What It Discards

> **A rental license expires. Months pass. The landlord renews.**
> **Every trace that it ever lapsed — silently disappears.**

Philadelphia publishes rental license data across **four public surfaces**. Every one shows only the license's **current** state:

| Surface | Expiration? | Renewal date? | Status history? |
|:--|:--:|:--:|:--:|
| 🗺️ **Atlas** `atlas.phila.gov` | ❌ no column | ❌ | ❌ |
| 📋 **Property History** `li.phila.gov` | ❌ no row | ❌ | ❌ |
| 🏢 **eCLIPSE** `eclipse.phila.gov` | ✅ | ⚠️ partial | ❌ |
| 🔌 **Carto API** `phl.carto.com` | ✅ | ✅ *(hidden field)* | ❌ |

### 🛡️ But violations are permanent

When L&I cites a property for operating **without a valid rental license**, that record does **not** get erased by a later renewal. It keeps its case number, its dates, its resolution — and a link to the official Notice of Violation PDF.

**That enforcement history reaches back to `2010`.**

### 🎯 What each source can answer

| Question | Answer |
|:--|:--|
| Was this license expired on a given past date? | ❌ **Not available** — overwritten |
| When was it last renewed? | ✅ **Available** — `mostrecentissuedate` |
| Was the property cited for operating unlicensed, and when? | ✅ **Permanent** — since 2010 |

> [!WARNING]
> **The gap that remains.** Not every lapse produces a violation. A license that expires and is renewed *before an inspector visits* leaves **no enforcement record and no status history**. Those lapses are invisible in every public system — which is exactly what the daily license log exists to catch.

---

## ⚡ Two Logs, One Repo

```
   phl.carto.com ─▶ daily pull ─▶ diff ─▶ append-only log ─▶ OpenTimestamps ─▶ git commit
      (public)                    (deltas)                  (Bitcoin anchor)   (+ .ots proof)
```

| Log | What | Coverage |
|:--|:--|:--|
| 📜 **License log** | 96,879 Active/Expired rental licenses, diffed daily | **Forward** from `2026-08-21` |
| ⚖️ **Violations archive** | 25,946 §9-3902 rental-license citations | **2010 → present** |

Every update is a timestamped Git commit, and **GitHub's Activity log records every push — including any force-push — with compare links, visible to anyone with read access.** That push history is outside the maintainer's control, which is what makes it worth citing. See [`REWRITE_LOG.md`](REWRITE_LOG.md) for a full account of any history changes.

---

## 🔐 Cryptographic Timestamps — proof the data existed, independent of GitHub

A git commit date is only as trustworthy as the person (or platform) who wrote it — it can be back-dated, and GitHub could in principle be compelled to rewrite history. So the daily job does one more thing: it **anchors each change log to the Bitcoin blockchain** using [OpenTimestamps](https://opentimestamps.org/).

Here's what that means in plain terms:

- Every day, the job computes a **SHA-256 hash** of each change log and submits *only that hash* to free public OpenTimestamps calendar servers. **The data itself never leaves the runner** — a hash reveals nothing about the contents, it just uniquely fingerprints them.
- The calendars batch thousands of hashes into a single Bitcoin transaction. Once that transaction is mined, the hash is **permanently embedded in a Bitcoin block**. Because rewriting a Bitcoin block would cost more than the network's entire mining economy, that block's timestamp becomes an independent, tamper-evident witness: *this exact file existed, unaltered, no later than this block.*
- The proof is saved next to the data as a small **`.ots` file** (e.g. `changes.ndjson.ots`) and committed to the repo. **These proofs are self-validating** — once a `.ots` carries its Bitcoin attestation, anyone can verify it with nothing but a Bitcoin node, *even if this repo, GitHub, and every calendar server disappear.*

> [!NOTE]
> **Why this matters here:** the whole point of this project is that Philadelphia's systems overwrite history. A back-datable git log would be a weak answer to that. A Bitcoin anchor is not — it proves the log's contents on a given day to anyone, forever, without asking you to trust GitHub or the maintainer.

### Verify it yourself

```bash
# one-time: install the client (no account, no API key)
pipx install opentimestamps-client        # or: pip install opentimestamps-client

# grab a log and its proof
curl -O https://thumpersecure.github.io/phl-rental-license-log/changes.ndjson
curl -O https://thumpersecure.github.io/phl-rental-license-log/changes.ndjson.ots

ots info   changes.ndjson.ots   # shows the SHA-256 + which Bitcoin block(s) it's anchored in
ots verify changes.ndjson.ots   # confirms the file matches the proof and the block timestamp
```

`ots info` lists the Bitcoin block heights the hash is committed to; `ots verify` recomputes the hash of your copy of `changes.ndjson` and checks it against the block. If someone hands you an altered log, the hash won't match and verification fails.

Proof files carried in the repo: **`changes.ndjson.ots`**, **`violations_changes.ndjson.ots`**, and the current month partition (**`changes/YYYY-MM.ndjson.ots`**). Each is refreshed the moment its data file changes, so the committed proof always anchors the current contents; every past state keeps its own confirmed proof in git history at that day's commit.

> [!NOTE]
> Timestamping is **best-effort and additive** — it never blocks or gates a daily data update. If a calendar server is briefly unreachable, that day's stamp is simply retried on the next run; the data log is unaffected.

---

## ♾️ How Long Can This Run Untouched?

Short answer: **indefinitely, with a light human touch roughly every year or two** — not "5 months," and not honestly "forever with zero hands." Here's the real accounting, because the honest version is more useful than a slogan.

**What costs nothing and never expires (the machinery is durable):**

| Component | Status |
|:--|:--|
| **GitHub Actions minutes** | Free and unmetered for public repos — one run/day is nothing |
| **GitHub Pages hosting** | No inactivity expiry; usage is far under every limit |
| **The Actions token** | Auto-issued fresh each run, self-renewing — nothing to rotate |
| **Existing Bitcoin timestamps** | Self-validating forever, independent of GitHub *and* of OpenTimestamps' own servers |
| **Data source** | `phl.carto.com` — public, no auth, no key to expire |

**The two things that eventually need a human:**

1. **GitHub's 60-day scheduled-workflow rule.** GitHub auto-disables a scheduled (cron) workflow *"when no repository activity has occurred in 60 days"* in a public repo. This job commits every day, so it **should** keep resetting that clock and run unattended — **but GitHub's docs do not explicitly state whether a commit made by the workflow's own bot counts as "activity,"** and their answer to that is undocumented. If bot commits count, this runs untouched for years. If they don't, the workflow would pause at day 60 and need one click ("Enable workflow") or any manual commit to resume. Either way the *data is never lost* — a paused job just stops adding new days until you nudge it. **This is the one thing worth glancing at once every couple of months.**

2. **Pinned action / runtime decay.** The workflow pins versioned actions (`actions/checkout`, `actions/setup-python`, `actions/cache`). GitHub retires the underlying runner Node runtimes on a schedule and eventually *removes* them rather than grandfathering old pins, so about **every 1–2 years** those pins need a version bump. It's a two-line edit when it comes due; ignoring it indefinitely is the thing that would ultimately break an otherwise-immortal job.

**Bottom line:** the infrastructure has no built-in expiry and no recurring cost, so there's no fixed lifespan — but "runs itself forever with nobody ever looking" isn't truthful. The accurate promise is **years of hands-off daily operation, punctuated by a ~1–2-year maintenance touch (an action-version bump) and a possible one-click re-enable if GitHub's 60-day rule turns out not to count bot commits.** Design-wise it's built to survive neglect: a missing state cache just self-re-baselines, a flaky calendar server just retries next day, and every timestamp already earned stays valid no matter what happens to this repo.

---

## 🚀 How To Use It

### 1️⃣ Grab the log

```bash
curl -O https://thumpersecure.github.io/phl-rental-license-log/changes.ndjson
```

One JSON object per line. No parsing ceremony.

### 2️⃣ Look up one license

```bash
grep '"licensenum":"602204"' changes.ndjson | jq .
```

### 3️⃣ Find every license that expired

```bash
jq -c 'select(.diff.licensestatus.to == "Expired")' changes.ndjson
```

### 4️⃣ Find every license renewed *after* it expired — the lapse detector

```bash
jq -c 'select(.diff.licensestatus.from == "Expired" and
              .diff.licensestatus.to   == "Active")' changes.ndjson
```

### 5️⃣ Every property cited for operating unlicensed

```bash
curl -O https://thumpersecure.github.io/phl-rental-license-log/violations_changes.ndjson

jq -c 'select(.new.violationcode | startswith("9-3902"))
       | {case:.new.casenumber, addr:.new.address,
          issued:.new.violationdate, resolved:.new.violationresolutiondate}' \
   violations_changes.ndjson
```

### 6️⃣ Violations for one address — with the official NOV

```bash
grep '"address":"315-23 N 12TH ST"' violations_changes.ndjson | jq '.new.publicnov'
```

Each record carries `publicnov` — a direct link to the City's **official Notice of Violation PDF**.

### 7️⃣ Check the latest run

```bash
curl -s https://thumpersecure.github.io/phl-rental-license-log/latest.json | jq .
```

---

## 📦 What's In Here

| File | What it is |
|:--|:--|
| **`changes.ndjson`** | 🔒 **Append-only.** One line per detected change. The whole point. |
| **`violations_changes.ndjson`** | ⚖️ **Violations archive.** §9-3902 citations, 2010–present. |
| **`violations_latest.json`** | 📊 Summary of the most recent violations run. |
| **`state.json`** | 📸 Last-known state of every tracked license (the diff basis). |
| **`latest.json`** | 📊 Summary of the most recent run. |
| **`index.html`** | 🌐 The public page. |

### Change record shapes

```jsonc
// a license changed
{"ts":"…","licensenum":"602204","change":"updated",
 "diff":{"licensestatus":{"from":"Expired","to":"Active"},
         "expirationdate":{"from":"2026-02-28…","to":"2027-02-28…"}},
 "new":{…}}

// first time we ever saw it
{"ts":"…","licensenum":"000001","change":"initial","new":{…}}

// left the Active/Expired set entirely
{"ts":"…","licensenum":"…","change":"left_set","last":{…}}
```

### Tracked fields

**Licenses** — `licensestatus` · `expirationdate` · `mostrecentissuedate` *(renewal)* · `inactivedate` · `address` · `opa_account_num` · `zip`

**Violations** — `violationcode` · `violationcodetitle` · `violationstatus` · `violationdate` · `violationresolutiondate` · `casestatus` · `underappeal` · `publicnov`

---

## 🔧 How It Works

| | |
|:--|:--|
| **Source** | `https://phl.carto.com/api/v2/sql` — public, no auth |
| **Scope** | Rental licenses (`Active`/`Expired`) + §9-3902 violations, **citywide** |
| **Volume** | 96,879 licenses · 25,946 violations |
| **Schedule** | Daily, 08:15 UTC (**~4:15 AM ET**) |
| **Storage** | Changelog-style — only deltas are written |
| **Load** | A handful of paginated API calls per day |

---

## ⚠️ Scope

> [!IMPORTANT]
> The **violations archive is complete history** — every §9-3902 citation issued since 2010.
> The **license log is forward-capturing**: it records status changes from `2026-08-21` onward and cannot reconstruct a license's status before that date.

> [!NOTE]
> Independent project. **Not affiliated with, endorsed by, or operated by the City of Philadelphia.** All data is the City's own public open data.

---

<div align="center">

### 💬 Questions or feedback?

**[onlinemartialartist@pm.me](mailto:onlinemartialartist@pm.me)**

<sub>Built with public data · Because the record should outlive the refresh.</sub>

</div>
