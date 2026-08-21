<div align="center">

# 🏛️ PHL RENTAL LICENSE — CHANGE LOG

### *The history Philadelphia's public systems throw away.*

[![Live](https://img.shields.io/badge/STATUS-LIVE-00d26a?style=for-the-badge&logo=githubpages&logoColor=white)](https://thumpersecure.github.io/phl-rental-license-log/)
[![Licenses](https://img.shields.io/badge/TRACKED-96%2C879_LICENSES-1a5fb4?style=for-the-badge)](https://thumpersecure.github.io/phl-rental-license-log/latest.json)
[![Data](https://img.shields.io/badge/SOURCE-CITY_OPEN_DATA-a51d2d?style=for-the-badge)](https://phl.carto.com/api/v2/sql)
[![Updated](https://img.shields.io/badge/UPDATES-DAILY_04%3A15_ET-f5a97f?style=for-the-badge&logo=clockify&logoColor=white)](#-how-it-works)

**`Every Active + Expired rental license in Philadelphia. Diffed daily. Never overwritten.`**

</div>

---

## 🎬 The Problem

> **A rental license expires. Months pass. The landlord renews.**
> **And every trace that it ever lapsed — silently disappears.**

Philadelphia publishes rental license data across **four public surfaces**. Every one of them shows only the license's **current** state:

| Surface | Shows expiration? | Shows renewal date? | Shows history? |
|:--|:--:|:--:|:--:|
| 🗺️ **Atlas** `atlas.phila.gov` | ❌ no column | ❌ | ❌ |
| 📋 **Property History** `li.phila.gov` | ❌ no row | ❌ | ❌ |
| 🏢 **eCLIPSE** `eclipse.phila.gov` | ✅ | ⚠️ partial | ❌ |
| 🔌 **Carto API** `phl.carto.com` | ✅ | ✅ *(hidden field)* | ❌ |

**None of them retain history.** When the record updates, the old values are gone — permanently, from every public system.

### 💥 A real case

<table>
<tr><td>

**License `602204`** — 315-23 N 12th St · 163 units

```diff
- Feb 28, 2026 ...... EXPIRED
!  ~155 days unlicensed
+ Aug  2, 2026 ...... RENEWED
```

Today every public system reads **`Active`**, expiration **`Feb 28, 2027`**, inactive date **`—`**.
Property History literally displays *"Date issued: Aug 12, 2013"* beside *"Active"* — as if the license had been valid, without interruption, for thirteen years.

**The 155-day gap is invisible. Everywhere.**

</td></tr>
</table>

---

## ⚡ The Fix

```
   phl.carto.com  ──▶  daily pull  ──▶  diff vs yesterday  ──▶  append-only log  ──▶  git commit
      (public)                          (only changes)          changes.ndjson      (timestamped)
```

This repo runs that loop **once every day** and writes down what changed. Git makes each day's snapshot **timestamped and tamper-evident**.

> 🔭 **What it captures going forward:** every expiration, every renewal, every status flip — with the date it happened.

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

### 5️⃣ Check the latest run

```bash
curl -s https://thumpersecure.github.io/phl-rental-license-log/latest.json | jq .
```

---

## 📦 What's In Here

| File | What it is |
|:--|:--|
| **`changes.ndjson`** | 🔒 **Append-only.** One line per detected change. The whole point. |
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

`licensestatus` · `expirationdate` · `mostrecentissuedate` *(renewal)* · `inactivedate` · `address` · `opa_account_num` · `zip`

---

## 🔧 How It Works

| | |
|:--|:--|
| **Source** | `https://phl.carto.com/api/v2/sql` — public, no auth |
| **Scope** | Rental licenses, status `Active` or `Expired`, **citywide** |
| **Volume** | 96,879 licenses tracked · baseline `2026-08-21` |
| **Schedule** | Daily, 08:15 UTC (**~4:15 AM ET**) |
| **Storage** | Changelog-style — only deltas are written |
| **Load** | A handful of paginated API calls per day |

---

## ⚠️ Honest Limits

> [!IMPORTANT]
> **This captures history only going FORWARD from `2026-08-21`.**
> It cannot recover license 602204's Feb–Aug 2026 lapse — that is already gone from every public system. The next cycle (**602204 expires again Feb 28, 2027**) is the first this log will document with hard evidence.

> [!NOTE]
> Proof-of-concept. Independent project. **Not affiliated with, endorsed by, or operated by the City of Philadelphia.** All data is the City's own public open data.

---

<div align="center">

### 💬 Questions or feedback?

**[onlinemartialartist@pm.me](mailto:onlinemartialartist@pm.me)**

<sub>Built with public data · Because the record should outlive the refresh.</sub>

</div>
