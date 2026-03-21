# Citatio — download page (Vercel)

Single static page in **English**: platinum grey UI matching the desktop app (`theme.py`), **IBM-style striped** “CITATIO” title, app **logo** in the window (`logo.ico`), **animated rainbow** on the “View downloads on GitHub” link (same six colors as `RainbowHeader` in the app), Win95-style chrome, and a bottom bar: **Made by Teo Simon Untroib** + clock.

**Download for Windows** resolves the latest `Citatio-Setup-*.exe` from [GitHub Releases](https://github.com/SIMI2COOL/Citatio/releases).

## Deploy on Vercel

1. Sign in at [vercel.com](https://vercel.com) with GitHub.
2. **Add New → Project** → import **Citatio**.
3. **Root Directory**: **`website`**.
4. Framework: **Other** (no build command).
5. **Deploy**.

Redeploy after pulling updates. New GitHub releases still work without editing the HTML.

## Tuning the “Citatio” title stripes (in the browser)

The title uses CSS variables on `.citatio-title`:

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
