# Sounds Fake — daily YouTube Shorts

Real facts that sound made up. One short every day at 19:00 (Yerevan).

- `plan.json` — the 30-day topic plan and each day's status. Edit topics here any time.
- `PIPELINE.md` — the daily procedure the automation follows.
- `engine/kinetic_short.py` — renders a vertical 1080×1920 short from a spec (voice, captions, motion graphics, music).
- `specs/` — one script per video (plus fact sources).
- `scripts/` — setup and video hosting helpers.

Videos are hosted as GitHub release assets (`dayNN` releases) so Metricool can fetch them and publish to YouTube.
