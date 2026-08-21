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
   phl.carto.com  ──▶  daily pull  ──▶  diff  ──▶  append-only log  ──▶  git commit
      (public)                          (deltas)                        (timestamped)
```

| Log | What | Coverage |
|:--|:--|:--|
| 📜 **License log** | 96,879 Active/Expired rental licenses, diffed daily | **Forward** from `2026-08-21` |
| ⚖️ **Violations archive** | 25,946 §9-3902 rental-license citations | **2010 → present** |

Git makes every day's snapshot **timestamped and tamper-evident**.

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
