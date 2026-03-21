# Citatio — download page (Vercel)

Single static page in **English**: platinum grey UI matching the desktop app (`theme.py`), **IBM-style striped** “CITATIO” title (fixed at the top center of the page; **does not** move with the download window), app **logo** in the window (`logo.ico`), **animated rainbow** on the “View downloads on GitHub” link (same six colors as `RainbowHeader` in the app), Win95-style chrome, and a bottom bar: **Made by Teo Simon Untroib** + clock.

The page loads the latest release from GitHub and wires:

- **Windows** → `Citatio-Setup-*.exe`
- **Linux** → `Citatio-Linux-*.tar.gz` (built by `.github/workflows/release-publish.yml` when you publish a release)

Download buttons use **`dl-icon-windows.svg`** (Windows XP–style mark from your Icons8 asset) and **`dl-icon-linux.svg`** (Tux artwork). If Icons8’s license for your account asks for attribution, add it in the page footer or here in the docs.

### Link preview (WhatsApp, etc.)

`index.html` sets **`og:title` / Twitter title** to **Citatio** (not “Citatio — Download”), **`og:description`** to the one-line app pitch (Scholar + CSV/Excel), and **`og-image.png`** as the preview image. After changing the PNG, bump the `?v=` query on the `og:image` / `twitter:image` URLs in `index.html` so caches refresh. WhatsApp can take a while to update; the [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/) can help force a rescrape.

## Deploy on Vercel

1. Sign in at [vercel.com](https://vercel.com) with GitHub.
2. **Add New → Project** → import **Citatio**.
3. **Root Directory**: **`website`**.
4. Framework: **Other** (no build command).
5. **Deploy**.

Redeploy after pulling updates. New GitHub releases still work without editing the HTML.

## Tuning the “Citatio” title stripes (in the browser)

The title uses CSS variables on `.citatio-title` (size is `font-size`, e.g. **150px**):

- `--title-stripe-gap` — height of the **transparent** band (larger = black lines farther apart).
- `--title-stripe-width` — thickness of each **black** line (try **1px–4px**; too large looks like solid black).

**Chrome / Edge**

1. Open your local or deployed page.
2. **Right‑click** the word **Citatio** → **Inspect**.
3. In the **Elements** panel, the `<h1 class="citatio-title">` should be selected.
4. In **Styles** (right), find the `.citatio-title` rule (or click **:hov** / filter for `citatio`).
5. Click the values next to `--title-stripe-gap` and `--title-stripe-width` and change them (e.g. gap `8px`, width `2px`). The page updates **live**.
6. When you like the look, copy the two values and put them in `index.html` on `.citatio-title` (same variable lines), then commit.

**Firefox**

Same idea: right‑click → **Inspect**, select the `h1`, open **Rules**, edit the custom properties on `.citatio-title`.

**Tip:** You can also add a temporary line in the Styles panel, e.g. `element.style { --title-stripe-gap: 10px; }`, to experiment without touching the file first.
