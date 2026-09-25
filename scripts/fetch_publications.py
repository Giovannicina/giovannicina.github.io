#!/usr/bin/env python3
"""Build _data/publications.json from OpenAlex (primary) and ORCID (supplement).

Pipeline:
  1. Fetch your works from OpenAlex (linked to you via your ORCID iD) and
     your works list from ORCID.
  2. Merge each preprint into its published version (same title).
  3. Add ORCID works that OpenAlex lacks; complete their metadata via the DOI.
  4. Append _data/manual.yml, apply _data/overrides.yml, sort, write.

DBLP is not used: its servers block automated requests with a bot check.

Set the environment variable OPENALEX_API_KEY (a free key from
https://openalex.org/settings/api) for reliable access; in GitHub, store it
as a repository secret with that name.

Never writes a partial result: if a source fails, or the publication count
drops by more than MAX_DROP, the script exits non-zero and leaves the
existing file untouched. Use --force to override the drop check.
"""

import gzip
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_data" / "publications.json"
MAX_DROP = 0.2
USER_AGENT = "academic-site-publication-sync/1.1"

# OpenAlex work types that are not publications in their own right.
SKIP_TYPES = {"paratext", "erratum", "peer-review", "retraction", "supplementary-materials", "dataset"}
# Venues that host preprints rather than publish them.
PREPRINT_SERVERS = re.compile(r"arxiv|medrxiv|biorxiv|ssrn|research ?square|preprints\.org|techrxiv|openreview", re.I)


# --------------------------------------------------------------------------
# Helpers

def http_get(url, accept, retries=3):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
                if body[:2] == b"\x1f\x8b":  # gzip-compressed despite not being asked for
                    body = gzip.decompress(body)
                return body
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
    t = t.replace("\\n", " ")  # literal backslash-n left in some arXiv titles
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
# OpenAlex

def fetch_openalex(orcid):
    params = {"filter": f"author.orcid:{orcid}", "per_page": "200", "cursor": "*"}
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if key:
        params["api_key"] = key
    works = []
    while True:
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
        try:
            body = http_get(url, "application/json")
        except urllib.error.HTTPError as e:
            hint = "" if key else " Add a free API key as the OPENALEX_API_KEY secret."
            raise RuntimeError(f"OpenAlex unavailable: HTTP {e.code}.{hint}") from None
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            start = body[:200].decode("utf-8", "replace").replace("\n", " ")
            raise RuntimeError(f"OpenAlex unavailable: not JSON ({e}); response began: {start!r}")
        works += data.get("results", [])
        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor or not data.get("results"):
            return works
        params["cursor"] = cursor


def strip_tags(t):
    return re.sub(r"<[^>]+>", "", t or "")


def parse_openalex(works, orcid, self_name, self_variants):
    pubs = []
    for w in works:
        if w.get("is_paratext") or w.get("type") in SKIP_TYPES:
            continue
        title = clean_title(strip_tags(w.get("display_name") or w.get("title")))
        if not title:
            continue
        authors = []
        for a in w.get("authorships") or []:
            au = a.get("author") or {}
            name = au.get("display_name") or a.get("raw_author_name") or ""
            is_self = (au.get("orcid") or "").endswith(orcid) or fold(name) in self_variants
            authors.append({"name": self_name if is_self else name, "self": is_self})

        doi = (w.get("doi") or "").lower().replace("https://doi.org/", "") or None
        arxiv = None
        for loc in w.get("locations") or []:
            for u in (loc.get("landing_page_url"), loc.get("pdf_url")):
                if u and "arxiv.org" in u:
                    arxiv = arxiv or arxiv_from(u)
        if doi and doi.startswith("10.48550/arxiv."):  # the arXiv DOI itself
            arxiv, doi = arxiv or arxiv_from(doi), None

        loc = w.get("primary_location") or {}
        source = loc.get("source") or {}
        venue = source.get("display_name") or ""
        preprint = w.get("type") == "preprint" or (
            not doi and (source.get("type") == "repository" or bool(PREPRINT_SERVERS.search(venue))))
        url = (f"https://doi.org/{doi}" if doi else None) or loc.get("landing_page_url") \
            or (f"https://arxiv.org/abs/{arxiv}" if arxiv else None)

        pubs.append({
            "title": title,
            "authors": authors,
            "year": int(w.get("publication_year") or 0),
            "venue_short": "",
            "venue": "" if preprint else venue,
            "venue_key": venue,
            "status": "preprint" if preprint else "published",
            "doi": doi,
            "arxiv": arxiv,
            "url": url,
            "openalex": (w.get("id") or "").rsplit("/", 1)[-1] or None,
        })
    return pubs


def merge_preprints(pubs):
    """Merge entries for the same paper: same arXiv ID or same normalized title.
    The published version (latest year) is kept; identifiers are pooled."""
    parent = list(range(len(pubs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    first = {}
    for i, p in enumerate(pubs):
        for key in (p.get("arxiv"), "t:" + norm_title(p["title"])):
            if key and key != "t:":
                if key in first:
                    parent[find(i)] = find(first[key])
                else:
                    first[key] = i
    groups = {}
    for i, p in enumerate(pubs):
        groups.setdefault(find(i), []).append(p)

    merged = []
    for group in groups.values():
        formal = [p for p in group if p["status"] == "published"]
        main = max(formal or group, key=lambda p: (p["year"], len(p["authors"])))
        for p in group:
            for k in ("arxiv", "doi", "openalex"):
                main[k] = main.get(k) or p.get(k)
        merged.append(main)
    return merged


# --------------------------------------------------------------------------
# ORCID

def fetch_orcid(orcid):
    url = f"https://pub.orcid.org/v3.0/{orcid}/works"
    body = http_get(url, "application/json")
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        start = body[:200].decode("utf-8", "replace").replace("\n", " ")
        raise RuntimeError(f"ORCID unavailable:\n  {url}: not JSON ({e}); response began: {start!r}")


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
    return {x for x in (p.get("doi"), p.get("arxiv"), p.get("openalex")) if x}


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
            "venue_key": "",
            "openalex": None,
        })
        added += 1
    return added


def apply_overrides(pubs, overrides, self_name):
    venues = overrides.get("venues") or {}
    by_key = {}
    for k, v in (overrides.get("papers") or {}).items():
        by_key[str(k).lower()] = v
        by_key["t:" + norm_title(str(k))] = v  # papers may also be keyed by title
    result = []
    for p in pubs:
        for key in (p.get("venue_key"), p.get("venue_short")):
            if key and key in venues:
                p["venue"] = venues[key]
        o = {}
        for key in [*identifiers(p), "t:" + norm_title(p["title"])]:
            o.update(by_key.get(key.lower() if not key.startswith("t:") else key) or {})
        if o.get("hide"):
            continue
        for field in ("title", "venue", "venue_short", "status", "code", "slides", "project", "note", "url", "year"):
            if field in o:
                p[field] = o[field]
        if "authors" in o:
            p["authors"] = [{"name": self_name if fold(n) == fold(self_name) else n,
                             "self": fold(n) == fold(self_name)} for n in o["authors"]]
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
    sys.stdout.reconfigure(line_buffering=True)  # keep log lines in order with stderr
    force = "--force" in sys.argv
    cfg = yaml.safe_load((ROOT / "_config.yml").read_text(encoding="utf-8"))["publications"]
    self_name = cfg["name"]
    self_variants = {fold(n) for n in [self_name, *cfg.get("name_variants", [])]}

    try:
        print(f"Fetching OpenAlex works for ORCID {cfg['orcid']}")
        works = fetch_openalex(cfg["orcid"])
        pubs = merge_preprints(parse_openalex(works, cfg["orcid"], self_name, self_variants))
        print(f"  {len(works)} works, {len(pubs)} after merging preprints")
        print(f"Fetching ORCID {cfg['orcid']}")
        works = parse_orcid(fetch_orcid(cfg["orcid"]))
        added = add_orcid_works(pubs, works, self_variants, self_name)
        print(f"  {len(works)} works, {added} not in OpenAlex")
    except Exception as e:
        print(f"error: {e}\nKeeping the existing publication list.", file=sys.stderr)
        return 1

    manual = load_yaml("manual.yml")
    for m in manual if isinstance(manual, list) else []:
        m.setdefault("status", "preprint")
        for k in ("doi", "arxiv", "url", "openalex"):
            m.setdefault(k, None)
        m.setdefault("venue", "")
        m.setdefault("venue_short", "")
        m["authors"] = [{"name": self_name if fold(n) in self_variants else n,
                         "self": fold(n) in self_variants} for n in m.get("authors", [])]
        pubs.append(m)

    pubs = apply_overrides(pubs, load_yaml("overrides.yml"), self_name)
    pubs.sort(key=lambda p: (-int(p.get("year") or 0), p["title"].casefold()))
    for p in pubs:
        p["id"] = p.get("doi") or p.get("arxiv") or p.get("openalex") or norm_title(p["title"])[:40]

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
