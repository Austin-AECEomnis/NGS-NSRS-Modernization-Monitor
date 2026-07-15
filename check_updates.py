#!/usr/bin/env python3
"""
check_updates.py

Weekly courtesy check for NGS/NOAA National Spatial Reference System (NSRS)
modernization pages. Deterministic, no LLM/agent invocation, no credentials
beyond what GitHub Actions provides automatically for this one repo.

For each URL in sources.json: fetch it, normalize the text (strip HTML tags
and collapse whitespace, to avoid false positives from navigation/markup-only
changes), and hash it. Compare against state/last-check.json from the prior
run. Write an updated state file and, if anything changed or a fetch failed,
a dated report under reports/.

Exit codes (all nonzero exits are intentional -- see README "How Notification
Works"): 0 = no changes, all sources reachable. 1 = at least one source's
content changed since the last check. 2 = at least one source could not be
fetched (this is always reported as an error, never silently treated as "no
change").
"""

import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
SOURCES_PATH = ROOT / "sources.json"
STATE_PATH = ROOT / "state" / "last-check.json"
REPORTS_DIR = ROOT / "reports"

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
USER_AGENT = "NGS-NSRS-Modernization-Monitor (https://github.com/Austin-AECEomnis/NGS-NSRS-Modernization-Monitor)"


def normalize(html_text):
    """Strip tags and collapse whitespace so markup-only or navigation-only
    changes don't produce a false-positive diff. A heuristic, not a full
    HTML parse -- documented as such, not claimed to be precise."""
    text = TAG_RE.sub(" ", html_text)
    return WHITESPACE_RE.sub(" ", text).strip()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    sources = load_json(SOURCES_PATH, {"sources": []})["sources"]
    prior_state = load_json(STATE_PATH, {})

    new_state = {}
    changed = []
    errored = []

    for src in sources:
        sid, url = src["id"], src["url"]
        try:
            content = fetch(url)
            content_hash = hashlib.sha256(normalize(content).encode("utf-8")).hexdigest()
            new_state[sid] = {
                "url": url,
                "label": src.get("label", sid),
                "hash": content_hash,
                "last_checked": now,
            }
            prior_hash = prior_state.get(sid, {}).get("hash")
            if prior_hash is not None and prior_hash != content_hash:
                new_state[sid]["last_changed"] = now
                changed.append(src)
            elif prior_hash is None:
                # First time seeing this source -- baseline, not a "change".
                new_state[sid]["last_changed"] = None
            else:
                new_state[sid]["last_changed"] = prior_state[sid].get("last_changed")
        except (urllib.error.URLError, TimeoutError) as e:
            # Preserve prior state so an error never overwrites a good hash
            # with nothing, and never reads as "no change".
            new_state[sid] = prior_state.get(sid, {"url": url, "label": src.get("label", sid)})
            new_state[sid]["last_error"] = f"{now}: {e}"
            errored.append((src, str(e)))

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(new_state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if changed or errored:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORTS_DIR / f"{now}.md"
        lines = [f"# NSRS Monitor Report -- {now}", ""]
        if changed:
            lines.append("## Content changed since last check")
            for src in changed:
                lines.append(f"- **{src.get('label', src['id'])}** -- {src['url']}")
            lines.append("")
            lines.append("This means the page's text differs from the last recorded check. "
                          "It does not by itself mean any specific fact changed -- see this "
                          "repo's README, \"What To Do When This Fires\", before touching ATHANOR.")
            lines.append("")
        if errored:
            lines.append("## Could not be checked (reported as an error, not \"no change\")")
            for src, err in errored:
                lines.append(f"- **{src.get('label', src['id'])}** -- {src['url']} -- {err}")
            lines.append("")
        report_path.write_text("\n".join(lines), encoding="utf-8")
        print(report_path.read_text(encoding="utf-8"))

    if errored:
        print(f"RESULT: {len(errored)} source(s) could not be checked.", file=sys.stderr)
        sys.exit(2)
    if changed:
        print(f"RESULT: {len(changed)} source(s) changed since last check.", file=sys.stderr)
        sys.exit(1)
    print("RESULT: no changes, all sources reachable.")
    sys.exit(0)


if __name__ == "__main__":
    main()
