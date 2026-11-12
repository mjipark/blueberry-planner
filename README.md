# Blueberry Planner 2026–27

A soft-focus personal planner: month and year views for 2026 and 2027, Seoul weather, and Berry, a helper that adds plans when you type things like "I have a meet up with my friend on 12/5 at 3pm".

- **Month view** (opens by default): click or tap a day to add or remove plans. Arrows (or ← / →) move across both years.
- **Year view**: switch between 2026 and 2027, plus a "Coming up" list.
- **Weather**: live Seoul forecast from Open-Meteo when the app runs on its own site; a saved snapshot on claude.ai.
- **Berry**: understands "12/5", "Dec 5", "tomorrow", "next Friday" and times like "3pm". A date with no year means the next time it comes around, so "1/8" is January 8, 2027. On claude.ai, Berry uses Claude.

## Install it as an app

Put it on GitHub Pages first (below), then open `https://mjipark.github.io/blueberry-planner/`:

- **Mac, Chrome/Edge:** the **Install** button in the app, or ⋮ → Cast, save, and share → Install page as app.
- **Mac, Safari:** File → Add to Dock.
- **iPhone (Safari):** Share → Add to Home Screen.
- **Android (Chrome):** ⋮ → Add to Home screen.

It works offline once installed; plans you add offline sync the next time you're online.

## Sync across devices

Same method as myPlanner: plans are saved to a private GitHub Gist (`blueberry-planner-sync.json`) in your own account.

- On a device where **myPlanner sync is already on**, Blueberry Planner reuses that token automatically (same site, same browser), so there's nothing to set up.
- Otherwise tap **Sync** → create a classic GitHub token with only the `gist` scope → paste → Connect.
- To add your phone, tap **Copy setup link** and open it on the phone. The link contains your token, so only open it on your own devices.

Each plan carries the time it was last changed. The newest change wins, and a deletion wins over any edit made before it, so removing a plan on your phone removes it on your Mac too.

## Publish on GitHub Pages

1. Push this folder to `github.com/mjipark/blueberry-planner`.
2. On GitHub: repo → **Settings → Pages** → Source: *Deploy from a branch* → Branch: `main`, folder `/ (root)` → Save.
3. After a minute it's live at `https://mjipark.github.io/blueberry-planner/`.

## Files

`index.html` (the whole app) · `manifest.webmanifest` + `icons/` (app install) · `sw.js` (offline) · `logo/` (logo sources and the renderer that made them).
