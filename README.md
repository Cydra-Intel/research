# Cydra Intel — Threat Research

research.cydraintel.ai, deployed by GitHub Actions (`.github/workflows/publish.yml`).

## Publishing an article

1. Make a folder named for the day it goes live: `articles/YYYY-MM-DD-short-slug/`
   (lowercase letters, digits and dashes after the date).
2. Put the article's **PDF** in it, and its **hero image** as `hero.png` (or `.jpg` / `.webp`),
   1200×675. The hero is the article's banner and its social preview.
3. Commit and push to `main`.

On the push, the PDF is turned into `article.md` (its text and headings) and `images/` (its
charts and figures), which are committed back to the folder. The article goes live at
**10:00 New York time** on the folder's date; until then it isn't on the site at all.

> The repository is public: a folder pushed ahead of its date can be seen on GitHub before it
> goes live on the site.

### After the conversion

`article.md` is yours to edit; it's never regenerated once it exists (delete it to convert the
PDF again). The lines between the `---` at its top:

| Line | What it does |
| --- | --- |
| `title:` | the headline (from the PDF) |
| `summary:` | the line under the title on the front page |
| `publish:` | when it goes live, `YYYY-MM-DD HH:MM` New York time (default: the folder's date, 10:00) |
| `kicker:` / `tag:` | the small label over the title / the article's tag |
| `dek:` | optional: an italic line under the title on the article page |
| `pdf:` | the PDF offered as "Download the PDF" |

## Building locally

    pip install -r tools/requirements.txt
    python tools/build.py convert               # new PDFs -> article.md + images/
    python tools/build.py build                 # _site/ as of now
    python tools/build.py build --preview       # including articles not live yet
    python tools/build.py build --now "2026-11-10 10:00"   # as of a given time

## Files

- `index.html` — the front page; published articles are added between `<!-- articles:start -->` and `<!-- articles:end -->`
- `articles/adversary-in-the-middle.html` — the first article (hand-written)
- `assets/article.css` — the article pages' style
- `og-cover.png` — the front page's social preview (1200×675)
- `tools/build.py` — the converter and site builder
