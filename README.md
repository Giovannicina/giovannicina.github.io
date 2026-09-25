# Personal academic website

Plain Jekyll, no theme, no JavaScript. Hosted on GitHub Pages.

## Setup (once)

1. Create a repository named `<username>.github.io` and push these files to `main`.
2. In the repository: Settings > Pages > Build and deployment > Source: **GitHub Actions**.
3. Actions tab > "Build site" > Run workflow. The first run fills the publication list.

## Everyday edits

| To change                          | Edit                                   |
|-----------------------------------|----------------------------------------|
| Name, position, links, email       | `_config.yml`                          |
| Bio and research summary           | `index.md`                             |
| News                               | `_data/news.yml`                       |
| Featured papers, code links, fixes | `_data/overrides.yml`                  |
| Papers not yet in DBLP or ORCID    | `_data/manual.yml`                     |
| CV                                 | `cv.md`; upload `assets/cv.pdf`        |
| Homepage photo                     | upload to `assets/`, set `photo` in `_config.yml` |
| Appearance                         | `assets/style.css`                     |

Never edit `_data/publications.json`; it is regenerated weekly.

## Adding a page

Create e.g. `teaching.md`:

```
---
layout: default
title: Teaching
permalink: /teaching/
---
# Teaching
...
```

and add it to `_data/navigation.yml`. Set `math: true` in the front matter
to enable KaTeX (`\( ... \)` inline, `$$ ... $$` display) on that page.

## How publications are generated

`scripts/fetch_publications.py` runs in the weekly workflow:

1. Reads your DBLP record; merges each arXiv (CoRR) entry into its published version.
2. Reads your ORCID works; adds those DBLP lacks, with metadata resolved via their DOI.
3. Appends `manual.yml`, applies `overrides.yml`, sorts by year.

If DBLP or ORCID is unreachable, or the count drops by more than 20%, nothing
is written and the site keeps the previous list. Run locally with
`pip install pyyaml && python scripts/fetch_publications.py`.

## Local preview (optional)

`gem install bundler jekyll github-pages && jekyll serve`, or with Docker:
`docker run --rm -p 4000:4000 -v "$PWD":/srv/jekyll jekyll/jekyll jekyll serve`.
