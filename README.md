# Blueberry Planner 2026

A single-page personal planner in a soft, landscape layout.

- **Month view (default):** full month grid, click any day to add or remove plans, today highlighted, weather icons on forecast days.
- **Year view:** January–December 2026 as mini calendars, plus a "Coming up" list.
- **Weather:** Seoul forecast snapshot (°C). It is embedded in the page, not live; update the `WEATHER` object in `index.html` to refresh it.
- **Berry, the AI assistant:** type things like "I have a meet up with my friend on 11/20" and it adds the plan to your calendar. When the page runs as a Claude artifact it uses Claude; anywhere else it falls back to a built-in date parser that handles "11/20", "Nov 20", "tomorrow", "next Friday" and times like "3pm".

## Run it

Open `index.html` in a browser. No build step, no dependencies (fonts load from Google Fonts).

## Where plans are saved

- As a Claude artifact: saved privately to your account.
- Opened as a plain file or on GitHub Pages: saved in the browser's `localStorage`, so they stay on that browser only.

## Navigation

Use the **Year / Month** buttons, the arrows next to the month name (or ← / → keys), or link straight to a view with `#year` or `#month-11`.
