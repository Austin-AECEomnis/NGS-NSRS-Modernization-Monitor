# NGS NSRS Modernization Monitor

A weekly courtesy check for official status updates on NOAA/NGS's modernization of the National Spatial Reference System (NAD83/NAVD88 → NATRF2022/NAPGD2022). It exists so a real milestone doesn't get missed for weeks just because nobody remembered to check — nothing more.

## 🎯 Purpose

The NSRS modernization timeline (new reference frames, a new vertical datum, a new State Plane generation) is still moving: beta phases, an FGCS approval target, and a legacy-system submission deadline are all in flux as of this writing. A geodetic reference library that cites this material needs to know when the underlying status changes — but manually re-checking NGS's pages every week is exactly the kind of chore that quietly stops happening. This repo automates the checking, not the judgment: it flags that something may have changed and leaves the actual fact-checking to a human.

**This monitor is deliberately not load-bearing.** If a check gets missed for a month, nothing downstream breaks — see [What To Do When This Fires](#-what-to-do-when-this-fires) for why.

## 📡 What It Monitors

An explicit allowlist in [`sources.json`](sources.json) — currently NGS's three "New Datums" pages:

- [New Datums landing page](https://geodesy.noaa.gov/datums/newdatums/index.shtml)
- [New Datums FAQ](https://geodesy.noaa.gov/datums/newdatums/FAQNewDatums.shtml)
- [Track Our Progress](https://geodesy.noaa.gov/datums/newdatums/TrackOurProgress.shtml)

It never discovers or follows links on its own — adding a source means editing `sources.json` directly.

## ⚙️ How It Works

[GitHub Actions](.github/workflows/check-nsrs.yml) runs [`check_updates.py`](check_updates.py) every Monday (or on demand via the Actions tab). For each source, it fetches the page, strips HTML tags and collapses whitespace (so navigation or markup-only edits don't produce a false alarm), and hashes the result. That hash is compared against [`state/last-check.json`](state/last-check.json) from the previous run.

No LLM or agent runs inside this workflow. It's a fixed, deterministic script on a timer — the same shape as [USGS-Guadalupe-LiveStage](https://github.com/Austin-AECEomnis/USGS-Guadalupe-LiveStage), applied to a status-check instead of a live reading.

## 🚦 How Notification Works

No email service, webhook, or extra credential — no new infrastructure, just GitHub's own primitives, honestly scoped:

- **The durable record is a same-repository GitHub Issue**, opened whenever a content change or fetch error is detected, containing the report. This is the thing to actually rely on.
- **A failed-run email is a secondary, non-guaranteed signal.** When the script detects a change or error, it exits nonzero, which makes the workflow run show as **failed** — and GitHub *can* email the repo owner on workflow failure, but this depends on Austin's own GitHub notification settings, not a universal default. A failed run here means "go look," not "something is broken."
- **Weekly execution is best-effort, not guaranteed.** GitHub may delay or drop a scheduled run under load, and — the case actually worth knowing about — **GitHub disables scheduled workflows on a public repository after 60 days with no other repository activity.** Since this design only commits when a change is actually detected (see Output below), a long stretch of unchanged NGS pages could eventually cause GitHub to auto-disable the schedule. Given this monitor is deliberately non-load-bearing, that's an accepted risk to notice next time this repo is visited, not something engineered around.

A fetch error (page unreachable, timeout) and a detected content change are two different things and are reported as such — an error is never recorded as "no change."

## 📄 Output

- **`state/last-check.json`** — current hash, label, and last-checked/last-changed timestamp per source. Committed on every run, whether or not anything changed, so the commit history is the audit trail of when this actually ran (as opposed to relying solely on GitHub's own Actions run history, which isn't retained indefinitely).
- **`reports/<timestamp>.md`** — written only when something changed or errored; content of the Issue GitHub opens.

## 📝 What To Do When This Fires

This is the part that matters more than the code. **A detected change is a lead, not a fact.**

1. Open the linked report (or the latest file under `reports/`) and read which source changed.
2. Start a session with Claude or Sol and ask it to directly re-verify the current content of that NGS page — the diff this monitor detected is not itself evidence of what changed, only that something did.
3. If a claim in **ATHANOR-core**'s `PROJECTS/GEODETICS-LIBRARY/` is actually affected:
   - Add or update the source in `PROJECTS/GEODETICS-LIBRARY/SOURCES/REGISTRY.md`, with a real retrieval date and direct-review confirmation.
   - Update the relevant file under `PROJECTS/GEODETICS-LIBRARY/NSRS-MODERNIZATION/` (or the future canonical fact document once one exists), citing the new registry entry and refreshing its `as_of` / `reviewed_at` fields.
   - Follow the mutable-canon policy in `PROJECTS/GEODETICS-LIBRARY/SCHEMA.md` (Section 9) — edit in place with a `revision_note`, don't create a superseding file for a routine update.
4. If nothing in the library actually changed (the diff was a false positive — reworded paragraph, layout change), no action needed beyond closing the Issue.

This monitor has no access to ATHANOR-core and cannot make this update itself, on purpose — see below.

## 🔒 Design Principles

- **No credentials.** Every source here is public. GitHub Actions' own short-lived, repo-scoped token is the only credential this workflow ever uses — nothing is stored in secrets.
- **No cross-repo writes.** This repo cannot and does not write to ATHANOR-core or anywhere else. Incorporating a finding is always a separate, manual, human-triggered step.
- **Detection only, never a conclusion.** A hash mismatch means the page's text differs from last time — it does not mean a specific geodetic fact changed. That judgment stays with a human (and whichever agent they bring in to verify).
- **Errors are never silence.** A page that can't be fetched is reported as an error, distinctly from "no change."

## 🛠️ Tech Stack

Python 3.11 (standard library only — no dependencies to install), GitHub Actions, GitHub Issues.

## 🔗 Related

Part of the geodetics reference work in `ATHANOR-core` (private repo) — see `CATALOG/decisions/ADR-0003-nsrs-monitor-exception.md` for the decision record authorizing this monitor as a bounded exception to that vault's normal "nothing runs unattended" rule.
