#!/usr/bin/env python3
"""Build _data/publications.json from DBLP (primary) and ORCID (supplement).

Pipeline:
  1. Fetch the DBLP person record (XML) and the ORCID works list (JSON).
  2. Merge DBLP preprints (CoRR) into their published versions.
  3. Add ORCID works that DBLP lacks; complete their metadata via the DOI.
  4. Append _data/manual.yml, apply _data/overrides.yml, sort, write.

Never writes a partial result: if a source fails, or the publication count
drops by more than MAX_DROP, the script exits non-zero and leaves the
existing file untouched. Use --force to override the drop check.
"""

import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_data" / "publications.json"
MAX_DROP = 0.2
USER_AGENT = "academic-site-publication-sync/1.0 (+https://orcid.org)"

# DBLP gives abbreviations only; unknown venues are shown as DBLP writes them.
# Add or correct names under `venues:` in _data/overrides.yml.
VENUE_NAMES = {
    "AAAI": "AAAI Conference on Artificial Intelligence",
    "AISTATS": "International Conference on Artificial Intelligence and Statistics",
    "CHIL": "Conference on Health, Inference, and Learning",
    "CLeaR": "Conference on Causal Learning and Reasoning",
    "ICLR": "International Conference on Learning Representations",
    "ICML": "International Conference on Machine Learning",
    "IJCAI": "International Joint Conference on Artificial Intelligence",
    "ML4H@NeurIPS": "Machine Learning for Health Symposium",
    "NeurIPS": "Advances in Neural Information Processing Systems",
    "Trans. Mach. Learn. Res.": "Transactions on Machine Learning Research",
    "UAI": "Conference on Uncertainty in Artificial Intelligence",
}
# Journals get a short label only when the community uses one.
JOURNAL_SHORT = {"Trans. Mach. Learn. Res.": "TMLR", "J. Mach. Learn. Res.": "JMLR"}


# --------------------------------------------------------------------------
# Helpers

def http_get(url, accept, retries=3):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            if attempt == retries - 1:
                raise
        except urllib.error.URLError:
            if attempt == retries - 1:
                raise
        time.sleep(2 ** attempt * 2)


def fold(s):
    """Accent- and case-insensitive form, for name matching."""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).casefold().strip()


def norm_title(t):
    return re.sub(r"[^a-z0-9]", "", fold(t))


def clean_title(t):
    t = re.sub(r"\s+", " ", t).strip()
    return t[:-1] if t.endswith(".") else t


def arxiv_from(text):
    m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", text or "")
    return m.group(1) if m else None


def doi_from(url):
    m = re.search(r"doi\.org/(10\.\S+)", url or "")
    if not m:
        return None
    doi = m.group(1).lower()
    return None if doi.startswith("10.48550/arxiv") else doi


# --------------------------------------------------------------------------
# DBLP

def fetch_dblp(pid):
    return http_get(f"https://dblp.org/pid/{pid}.xml", "application/xml")


def parse_dblp(xml_bytes, pid, self_name):
    root = ET.fromstring(xml_bytes)
    pubs = []
    for r in root.findall("r"):
        e = r[0]
        authors = []
        for a in e.findall("author") + e.findall("editor"):
            name = re.sub(r"\s\d{4}$", "", a.text or "")  # strip DBLP homonym suffix
            is_self = a.get("pid") == pid
            authors.append({"name": self_name if is_self else name, "self": is_self})
        raw_venue = (e.findtext("booktitle") or e.findtext("journal") or "").strip()
        informal = raw_venue == "CoRR" or e.get("publtype") == "informal"
        if informal:
            venue_short = "arXiv"
        elif e.tag == "article":
            venue_short = JOURNAL_SHORT.get(raw_venue, "")
        else:
            venue_short = raw_venue
        ees = [x.text or "" for x in e.findall("ee")]
        arxiv = arxiv_from(e.findtext("volume")) if raw_venue == "CoRR" else None
        arxiv = arxiv or next((arxiv_from(u) for u in ees if "arxiv" in u.lower()), None)
        doi = next((d for d in map(doi_from, ees) if d), None)
        url = next((u for u in ees if "arxiv" not in u.lower()), None) or (ees[0] if ees else None)
        pubs.append({
            "title": clean_title("".join(e.find("title").itertext())),
            "authors": authors,
            "year": int(e.findtext("year") or 0),
            "venue_short": venue_short,
            "venue": "" if informal else VENUE_NAMES.get(raw_venue, raw_venue),
            "venue_key": raw_venue,
            "status": "preprint" if informal else "published",
            "doi": doi,
            "arxiv": arxiv,
            "url": url,
            "dblp": e.get("key"),
        })
    return pubs


def merge_preprints(pubs):
    """Fold each CoRR entry into the published entry with the same title."""
    groups = {}
    for p in pubs:
        groups.setdefault(norm_title(p["title"]), []).append(p)
    merged = []
    for group in groups.values():
        formal = [p for p in group if p["status"] == "published"]
        if not formal:
            merged.append(max(group, key=lambda p: p["year"]))
            continue
        main = max(formal, key=lambda p: p["year"])
        for p in group:
            main["arxiv"] = main["arxiv"] or p["arxiv"]
            main["doi"] = main["doi"] or p["doi"]
        merged.append(main)
    return merged


# --------------------------------------------------------------------------
# ORCID

def fetch_orcid(orcid):
    return json.loads(http_get(f"https://pub.orcid.org/v3.0/{orcid}/works", "application/json"))


def fetch_csl(doi):
    """Full metadata for a DOI from Crossref or DataCite via content negotiation."""
    try:
        return json.loads(http_get(f"https://doi.org/{doi}", "application/vnd.citationstyles.csl+json"))
    except Exception as e:  # a single unresolvable DOI should not abort the run
        print(f"  warning: could not resolve DOI {doi}: {e}", file=sys.stderr)
        return None


def parse_orcid(data):
    works = []
    for g in data.get("group", []):
        s = g["work-summary"][0]  # ORCID's preferred version of this work
        ids = {}
        for x in (g.get("external-ids") or {}).get("external-id", []):
            ids.setdefault(x["external-id-type"], x["external-id-value"])
        title = (((s.get("title") or {}).get("title")) or {}).get("value", "")
        year = ((s.get("publication-date") or {}).get("year") or {}).get("value")
        works.append({
            "title": clean_title(title),
            "year": int(year) if year else 0,
            "venue": ((s.get("journal-title") or {}).get("value")) or "",
            "type": s.get("type"),
            "doi": ids.get("doi", "").lower() or None,
            "arxiv": arxiv_from(ids.get("arxiv", "")),
        })
    return works


def authors_from_csl(csl, self_variants, self_name):
    """Mark the site owner by full name, or by family name plus first initial."""
    families = {v.split()[-1] for v in self_variants}
    initial = fold(self_name)[:1]
    out = []
    for a in csl.get("author", []):
        name = " ".join(x for x in (a.get("given"), a.get("family")) if x) or a.get("literal", "")
        is_self = fold(name) in self_variants or (
            fold(a.get("family", "")) in families and fold(a.get("given", ""))[:1] == initial)
        out.append({"name": self_name if is_self else name, "self": is_self})
    return out


# --------------------------------------------------------------------------
# Merge, overrides, output

def identifiers(p):
    return {x for x in (p.get("doi"), p.get("arxiv"), p.get("dblp")) if x}


def find_match(pubs, w):
    t = norm_title(w["title"])
    for p in pubs:
        if (w["doi"] and w["doi"] == p.get("doi")) or (w["arxiv"] and w["arxiv"] == p.get("arxiv")):
            return p
        if t and t == norm_title(p["title"]):
            return p
    return None


def add_orcid_works(pubs, works, self_variants, self_name, resolve=fetch_csl):
    added = 0
    for w in works:
        match = find_match(pubs, w)
        if match:
            match["doi"] = match.get("doi") or w["doi"]
            match["arxiv"] = match.get("arxiv") or w["arxiv"]
            continue
        # arXiv papers have DataCite DOIs, which also resolve to full metadata.
        doi = w["doi"] or (f"10.48550/arxiv.{w['arxiv']}" if w["arxiv"] else None)
        csl = resolve(doi) if doi else None
        preprint = w["type"] == "preprint" or (w["arxiv"] and not w["doi"])
        venue = (csl or {}).get("container-title") or w["venue"]
        if isinstance(venue, list):
            venue = venue[0] if venue else ""
        pubs.append({
            "title": clean_title((csl or {}).get("title") or w["title"]),
            "authors": authors_from_csl(csl, self_variants, self_name) if csl else [],
            "year": w["year"] or ((csl or {}).get("issued", {}).get("date-parts") or [[0]])[0][0],
            "venue_short": "arXiv" if preprint else "",
            "venue": "" if preprint else venue,
            "status": "preprint" if preprint else "published",
            "doi": w["doi"],
            "arxiv": w["arxiv"],
            "url": f"https://doi.org/{w['doi']}" if w["doi"]
                   else f"https://arxiv.org/abs/{w['arxiv']}" if w["arxiv"] else None,
            "dblp": None,
            "venue_key": "",
        })
        added += 1
    return added


def apply_overrides(pubs, overrides, self_name):
    venues = overrides.get("venues") or {}
    by_key = overrides.get("papers") or {}
    result = []
    for p in pubs:
        for key in (p.get("venue_key"), p.get("venue_short")):
            if key and key in venues:
                p["venue"] = venues[key]
        o = {}
        for key in identifiers(p):
            o.update(by_key.get(key) or {})
        if o.get("hide"):
            continue
        for field in ("title", "venue", "venue_short", "status", "code", "slides", "project", "note", "url"):
            if field in o:
                p[field] = o[field]
        p["selected"] = bool(o.get("selected"))
        equal = {fold(n) for n in o.get("equal_contribution", [])}
        for a in p["authors"]:
            a["equal"] = fold(a["name"]) in equal or (a["self"] and fold(self_name) in equal)
        result.append(p)
    return result


def load_yaml(name):
    path = ROOT / "_data" / name
    return (yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None) or {}


def main():
    force = "--force" in sys.argv
    cfg = yaml.safe_load((ROOT / "_config.yml").read_text(encoding="utf-8"))["publications"]
    self_name = cfg["name"]
    self_variants = {fold(n) for n in [self_name, *cfg.get("name_variants", [])]}

    try:
        print(f"Fetching DBLP {cfg['dblp']}")
        pubs = merge_preprints(parse_dblp(fetch_dblp(cfg["dblp"]), cfg["dblp"], self_name))
        print(f"  {len(pubs)} entries after merging preprints")
        print(f"Fetching ORCID {cfg['orcid']}")
        works = parse_orcid(fetch_orcid(cfg["orcid"]))
        added = add_orcid_works(pubs, works, self_variants, self_name)
        print(f"  {len(works)} works, {added} not in DBLP")
    except Exception as e:
        print(f"error: source unavailable ({e}); keeping existing publication list", file=sys.stderr)
        return 1

    manual = load_yaml("manual.yml")
    for m in manual if isinstance(manual, list) else []:
        m.setdefault("status", "preprint")
        m["authors"] = [{"name": self_name if fold(n) in self_variants else n,
                         "self": fold(n) in self_variants} for n in m.get("authors", [])]
        pubs.append(m)

    pubs = apply_overrides(pubs, load_yaml("overrides.yml"), self_name)
    pubs.sort(key=lambda p: (-int(p.get("year") or 0), p["title"].casefold()))
    for p in pubs:
        p["id"] = p.get("doi") or p.get("arxiv") or p.get("dblp") or norm_title(p["title"])[:40]

    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    if old and len(pubs) < (1 - MAX_DROP) * len(old) and not force:
        print(f"error: count fell from {len(old)} to {len(pubs)}; refusing to write (use --force)",
              file=sys.stderr)
        return 1

    OUT.write_text(json.dumps(pubs, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {len(pubs)} publications to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
