#!/usr/bin/env python3
"""Builds research.cydraintel.ai into _site/.

An article is a folder `articles/YYYY-MM-DD-some-slug/` holding a PDF and a hero image
(`hero.png`, `.jpg` or `.webp`). That's all it needs:

    python tools/build.py convert   # PDF -> article.md + images/ (only for folders without article.md)
    python tools/build.py build     # _site/: the front page and every article that's published

`convert` writes `article.md` once, with the article's details at the top (title, summary,
publish time, …); edit it freely afterwards, it isn't overwritten. An article is published at
10:00 New York time on its folder's date (or at `publish:` in article.md) and is left out of
_site/ entirely until then. `build --preview` includes the unpublished ones, to look at locally.
"""
import argparse
import html
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / '_site'
BASE = 'https://research.cydraintel.ai'
TZ = ZoneInfo('America/New_York')
PUBLISH_AT = '10:00'
DATED = re.compile(r'^(\d{4}-\d{2}-\d{2})-[a-z0-9][a-z0-9-]*$')
HEROES = ('hero.png', 'hero.jpg', 'hero.jpeg', 'hero.webp')
# Kept out of the published site.
PRIVATE = {'_site', 'tools', '.github', '.git', 'README.md', '.gitignore'}


def article_dirs():
    root = ROOT / 'articles'
    return sorted(d for d in root.iterdir() if d.is_dir() and DATED.match(d.name)) if root.exists() else []


def hero_of(d):
    return next((h for h in HEROES if (d / h).exists()), None)


def pdf_of(d):
    return next(iter(sorted(d.glob('*.pdf'))), None)


# ---------- convert: PDF -> article.md + images/ ----------

def clean_markdown(md, title):
    """pymupdf4llm's Markdown, tidied: page footers, the repeated title and the doc byline
    dropped, lines the PDF wrapped joined back into paragraphs and list items."""
    keep = []
    for line in md.splitlines():
        s = line.strip()
        if re.fullmatch(r'Page \d+ of \d+', s):
            continue
        if s == title or s == f'# {title}':
            continue  # the title is the page's own heading
        if re.match(r'^[A-Z][a-z]{2} \d{1,2}, \d{4}\s+-\s+\W*@', s):
            continue  # the doc's byline: "Nov 9, 2026 - @Name"
        keep.append(line.rstrip())
    # Blocks separated by blank lines.
    blocks, cur = [], []
    for line in keep:
        if line.strip():
            cur.append(line.strip())
        elif cur:
            blocks.append(' '.join(cur))
            cur = []
    if cur:
        blocks.append(' '.join(cur))
    # A block the PDF broke mid-sentence continues in the next one.
    structural = re.compile(r'^(#|!\[|```|\||>|`|\d+\.\s|[-*+]\s|\*\*)')
    out = []
    for b in blocks:
        prev = out[-1] if out else ''
        # A short line right under an image is its caption.
        if prev.startswith('![') and len(b) < 90 and not structural.match(b) and not re.search(r'[.!?]$', b):
            out.append(f'<p class="caption">{b}</p>')
            continue
        joins = (prev and not re.match(r'^(#|!\[|```|\||`|<p class="caption">)', prev) and not structural.match(b)
                 and (not re.search(r'[.!?:;)\]”"]$', prev) or b[:1].islower()))
        if joins:
            out[-1] = f'{prev} {b}'
        else:
            out.append(b)
    return '\n\n'.join(out) + '\n'


def first_paragraph(md, sentences=2):
    """The first paragraph's opening sentences: the line under the title on the front page."""
    for b in md.split('\n\n'):
        b = b.strip()
        if b and not re.match(r'^(#|!\[|```|\||>|<|\d+\.\s|[-*+]\s)', b):
            b = re.sub(r'[*_`]', '', b)
            return ' '.join(re.split(r'(?<=[.!?])\s+', b)[:sentences])
    return ''


def convert(d):
    if (d / 'article.md').exists():
        return False
    pdf = pdf_of(d)
    if not pdf:
        return False
    import pymupdf
    import pymupdf4llm
    title = (pymupdf.open(pdf).metadata or {}).get('title') or ''
    images = d / 'images'
    images.mkdir(exist_ok=True)
    md = pymupdf4llm.to_markdown(str(pdf), write_images=True, image_path=str(images), image_format='png', dpi=150)
    md = md.replace(str(images) + '/', 'images/')
    if not title:
        m = re.search(r'^# (.+)$', md, re.M)
        title = m.group(1).strip() if m else d.name[11:].replace('-', ' ').capitalize()
    body = clean_markdown(md, title)
    date = DATED.match(d.name).group(1)
    head = '\n'.join([
        '---',
        f'title: {title}',
        f'summary: {first_paragraph(body)}',
        f'publish: {date} {PUBLISH_AT}',
        'kicker: Threat research',
        'tag: Campaign analysis',
        f'pdf: {pdf.name}',
        '---',
        '',
    ])
    (d / 'article.md').write_text(head + '\n' + body)
    return True


# ---------- build: _site/ ----------

def read_article(d):
    text = (d / 'article.md').read_text()
    meta, body = {}, text
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(':')
            if k.strip():
                meta[k.strip()] = v.strip()
        body = text[m.end():]
    return meta, body


def publish_time(meta, d):
    when = meta.get('publish') or f'{DATED.match(d.name).group(1)} {PUBLISH_AT}'
    return datetime.strptime(when, '%Y-%m-%d %H:%M').replace(tzinfo=TZ)


def esc(s):
    return html.escape(s or '', quote=True)


def read_minutes(body):
    return max(1, round(len(re.findall(r'\w+', body)) / 230))


def page(a):
    import markdown
    body_html = markdown.markdown(a['body'], extensions=['extra', 'sane_lists'], output_format='html5')
    url = f"{BASE}/articles/{a['slug']}/"
    hero = f"{url}{a['hero']}" if a['hero'] else f'{BASE}/og-cover.png'
    pdf = f'<span>·</span><span><a class="pdf-link" href="{esc(a["pdf"])}">Download the PDF</a></span>' if a['pdf'] else ''
    hero_fig = f'<figure class="hero"><img src="{esc(a["hero"])}" alt="{esc(a["title"])}" width="1200" height="675"></figure>' if a['hero'] else ''
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(a["title"])}</title>
<meta name="description" content="{esc(a["summary"])}">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(a["title"])}">
<meta property="og:description" content="{esc(a["summary"])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{esc(hero)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(a["title"])}">
<meta name="twitter:description" content="{esc(a["summary"])}">
<meta name="twitter:image" content="{esc(hero)}">
<meta name="theme-color" content="#f5f6f8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0d0f14" media="(prefers-color-scheme: dark)">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:ital,wght@0,400;0,500;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<link rel="stylesheet" href="../../assets/article.css">
</head>
<body>
<header class="site-head"><a href="../../index.html"><span>◆</span> CYDRA</a><span class="sub">· Research</span></header>
<button class="theme-toggle" id="themeToggle" type="button" aria-label="Toggle light or dark theme" title="Toggle theme">◐</button>
{hero_fig}
<div class="wrap">
  <div class="eyebrow">{esc(a["kicker"])}</div>
  <h1>{esc(a["title"])}</h1>
  {f'<p class="dek">{esc(a["dek"])}</p>' if a["dek"] else ''}
  <div class="meta"><span><b>{esc(a["tag"])}</b></span><span>·</span><span>{a["date_long"]}</span><span>·</span><span>{a["minutes"]} min read</span>{pdf}</div>
{body_html}
</div>
<footer class="site-footer">
  <span><a href="../../index.html" style="color:inherit;text-decoration:none"><b>Cydra</b></a> · Threat Research</span>
  <span>·</span><span>{a["date_long"]}</span>
  <span>·</span><span><a href="mailto:contact@cydraintel.ai" style="color:inherit">Contact</a></span>
  <span>·</span><span>© {a["when"].year} Cydra Intel, LLC</span>
</footer>
<script>
  (function () {{
    var root = document.documentElement, KEY = "cydra-theme";
    try {{ var saved = localStorage.getItem(KEY); if (saved === "dark" || saved === "light") root.setAttribute("data-theme", saved); }} catch (e) {{}}
    var btn = document.getElementById("themeToggle");
    if (btn) btn.addEventListener("click", function () {{
      var cur = root.getAttribute("data-theme");
      var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
      var isDark = cur ? cur === "dark" : prefersDark;
      var next = isDark ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try {{ localStorage.setItem(KEY, next); }} catch (e) {{}}
    }});
  }})();
</script>
</body>
</html>
'''


def card(a):
    thumb = (f'<span class="card-thumb" aria-hidden="true"><img src="articles/{a["slug"]}/{esc(a["hero"])}" alt="" '
             f'style="display:block;width:100%;height:100%;object-fit:cover;object-position:left center"></span>') if a['hero'] else '<span class="card-thumb" aria-hidden="true"></span>'
    return f'''  <a class="card" href="articles/{a["slug"]}/" style="margin-bottom:1.1rem">
    {thumb}
    <span class="card-body">
      <span class="tagrow"><span class="tag">{esc(a["tag"])}</span></span>
      <h2 class="card-title">{esc(a["title"])}</h2>
      <p class="card-dek">{esc(a["summary"])}</p>
      <span class="card-meta"><span>{a["date_short"]}</span><span>·</span><span>{a["minutes"]} min read</span><span>·</span><span class="readmore">Read →</span></span>
    </span>
  </a>
'''


def build(now, preview=False):
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    for p in ROOT.iterdir():
        if p.name in PRIVATE or p.name == 'articles':
            continue
        (shutil.copytree if p.is_dir() else shutil.copy2)(p, SITE / p.name)
    (SITE / 'articles').mkdir()
    for p in (ROOT / 'articles').iterdir():  # hand-written articles (not dated folders)
        if not (p.is_dir() and DATED.match(p.name)):
            (shutil.copytree if p.is_dir() else shutil.copy2)(p, SITE / 'articles' / p.name)
    shown, held = [], []
    for d in article_dirs():
        if not (d / 'article.md').exists():
            print(f'skip {d.name}: no article.md yet (run convert)')
            continue
        meta, body = read_article(d)
        when = publish_time(meta, d)
        if when > now and not preview:
            held.append((d.name, when))
            continue
        pdf = meta.get('pdf') or (pdf_of(d).name if pdf_of(d) else '')
        a = {
            'slug': d.name, 'title': meta.get('title') or d.name, 'summary': meta.get('summary', ''),
            'dek': meta.get('dek', ''), 'kicker': meta.get('kicker') or 'Threat research', 'tag': meta.get('tag') or 'Campaign analysis',
            'hero': meta.get('hero') or hero_of(d), 'pdf': pdf if pdf and (d / pdf).exists() else '',
            'when': when, 'date_long': f'{when.day} {when:%B %Y}', 'date_short': f'{when.day} {when:%b %Y}',
            'minutes': read_minutes(body), 'body': body,
        }
        out = SITE / 'articles' / d.name
        out.mkdir()
        for f in d.iterdir():
            if f.name != 'article.md':
                (shutil.copytree if f.is_dir() else shutil.copy2)(f, out / f.name)
        (out / 'index.html').write_text(page(a))
        shown.append(a)
    shown.sort(key=lambda a: a['when'], reverse=True)
    index = (SITE / 'index.html').read_text()
    feed = ''.join(card(a) for a in shown)
    index, n = re.subn(r'(<!-- articles:start -->\n).*?(\s*<!-- articles:end -->)', lambda m: m.group(1) + feed + m.group(2), index, flags=re.S)
    if not n:
        sys.exit('index.html has no <!-- articles:start --> / <!-- articles:end --> markers')
    (SITE / 'index.html').write_text(index)
    for a in shown:
        print(f"published {a['slug']} ({a['when']:%Y-%m-%d %H:%M %Z})")
    for name, when in held:
        print(f'held     {name} until {when:%Y-%m-%d %H:%M %Z}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('step', choices=['convert', 'build'])
    ap.add_argument('--now', help='build as of this time (YYYY-MM-DD HH:MM, New York), for checking a schedule')
    ap.add_argument('--preview', action='store_true', help='include articles not published yet')
    args = ap.parse_args()
    if args.step == 'convert':
        done = [d.name for d in article_dirs() if convert(d)]
        print('converted: ' + (', '.join(done) if done else 'nothing new'))
    else:
        now = datetime.strptime(args.now, '%Y-%m-%d %H:%M').replace(tzinfo=TZ) if args.now else datetime.now(TZ)
        build(now, args.preview)


if __name__ == '__main__':
    main()
