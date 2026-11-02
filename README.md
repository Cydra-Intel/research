# Cydra — Threat Research

Static site (GitHub Pages). Plain HTML/CSS/SVG, no build step.

- `index.html` — front page / article index
- `articles/adversary-in-the-middle.html` — first article
- `og-cover.png` — LinkedIn/social preview image (1200×675)
- `.nojekyll` — serve files as-is (no Jekyll)

## Before publishing
Set the social-preview URLs: replace `__BASE__` with your live base URL
(e.g. `https://cydra.io` or `https://<org>.github.io/<repo>`):

    LANG=C find . -name '*.html' -exec sed -i '' 's#__BASE__#https://YOUR-URL#g' {} +

## Deploy
Push to a GitHub repo, then enable Pages (Settings → Pages → Branch: main / root).
