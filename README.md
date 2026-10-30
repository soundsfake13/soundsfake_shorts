# Sounds Fake — daily YouTube Shorts

Real facts that sound made up. One short every day at 19:00 (Yerevan).

- `plan.json` — the 30-day topic plan and each day's status. Edit topics here any time.
- `PIPELINE.md` — the daily procedure the automation follows.
- `engine/` — five visual styles, each renders a vertical 1080×1920 short from a spec (voice, captions, motion graphics, music):
  `kinetic` (numbers & physics), `paper` (animals & nature), `space` (space), `clock` (time gaps), `ink` (strange history).
  Each day in `plan.json` has a `style`; the daily run uses the matching engine.
- `specs/` — one script per video (plus fact sources).
- `scripts/` — setup and video hosting helpers.

Videos are stored in `videos/` and served from raw.githubusercontent.com so Metricool can fetch them and publish to YouTube.
