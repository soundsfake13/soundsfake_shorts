# Daily pipeline — "Sounds Fake" YouTube Shorts

This is the procedure the daily scheduled task follows. One run = one video,
scheduled for **tomorrow at 19:00 Asia/Yerevan** (one day of buffer).

## 0. Setup
```bash
bash scripts/setup.sh            # deps, voice model, fonts (prints FONT_DIR export if needed)
```
If it prints an `export FONT_DIR=...` line, export it before rendering.

## 1. Pick the topic
Open `plan.json`. Take the entry whose `date` is **tomorrow** (Yerevan time) and `status` is `planned`.
If none, take the earliest `planned` entry whose date is today or later and whose 19:00 is still in the future.
If nothing is left, report "plan finished" and stop.

Before doing anything else, call Metricool `getScheduledPosts` (brand `7729832`, timezone `Asia/Yerevan`)
for that date. If a YouTube post is already scheduled that day, mark the entry `scheduled` and stop — never double-post.

## 2. Verify the facts (mandatory)
Use web search to confirm every claim in the entry's `facts` field with **at least two reliable sources**
(encyclopedias, universities, museums, science outlets, peer-reviewed papers). If a number or claim can't be
confirmed, soften it ("about", "up to") or drop it. Never add unverified extras.
Write the sources to `specs/dayNN_<slug>.sources.md`.

## 3. Write the script → `specs/dayNN_<slug>.json`
Same format as `specs/day01_venus.json` and `specs/day02_wombat.json` (study both first).
- 25–35 seconds, 7–10 lines. Line 1 = the hook (≤ 9 words), opening scene `slam`.
- Line 2 is usually "Sounds fake? It's true." with a `flash` scene.
- Spell numbers out in `text` (for the voice) and put digits in `caption`.
- Simple, friendly, family-safe English. No gore, no real-person likenesses, no brand logos or characters.
- Last line always: "Sounds fake? It's true. Follow for more." with a `toggle` scene (FAKE → TRUE).
- voice `am_michael`, speed `1.12`, bpm `118`.

### Scene types in `engine/kinetic_short.py`
| type | use | params |
|---|---|---|
| `slam` | words slam in (hook) | `lines`, `colors`, `size`, `y`, `bg`, `stagger`, `cube` |
| `flash` | each spoken word full-screen | `palette`, `cube` |
| `big` | one giant word/number + subline | `text`, `size`, `bg`, `color`, `sub` |
| `cube` | spinning cube + label | `bg`, `label`, `cube_color` |
| `grid` | counter with items popping in | `count`, `label`, `bg` |
| `planet` | flat spinning planet, arrow, counter | `label`, `count`, `count_label`, `arrow`, `dir`, `r`, `y`, `spin_secs`, `bg` |
| `orbit` | orbit around a sun with counter | `days`, `label`, `count_label` |
| `bars` | two-bar comparison + stamp | `rows` [[label, value, color]], `stamp` |
| `thermo` | thermometer with marks | `value`, `max`, `marks` [[label, value, color]] |
| `sunrise`, `squeeze`, `rock` | specific to the first two videos | — |
| `toggle` | cursor flips FAKE → TRUE (ending) | `left`, `right`, `click_at` |

Colors: `red`, `blue`, `cream`, `ink`, `yellow`. Alternate backgrounds between scenes.

**New visuals:** if the topic needs a picture none of these give (an animal, a building, a timeline…),
add a new scene function in the same flat style (palette colours, `INK` outlines, `kin_text`, `back`/`eout`
easing), make it reusable with parameters, register it in `SCENES`, and add it to the table above.

## 4. Render and check
```bash
python3 engine/kinetic_short.py specs/dayNN_<slug>.json out/dayNN.mp4
```
Check: duration 20–45 s; size < 100 MB. Extract ~8 frames into one contact sheet and **look at it**:
no text cut off at the edges, labels not colliding with the caption bar (y ≈ 1540–1660), every scene readable.
Fix and re-render until clean.

## 5. Host the video
```bash
bash scripts/publish_video.sh NN out/dayNN.mp4 "<short title>"   # prints the public URL
```
The repo must be public; the script warns if the URL isn't downloadable.

## 6. Schedule on YouTube via Metricool
`createScheduledPost` with `blogId` `7729832`, `date` `YYYY-MM-DDT19:00:00+04:00` and `info`:
```json
{
  "autoPublish": true, "draft": false, "descendants": [], "firstCommentText": "",
  "hasNotReadNotes": false, "shortener": false, "smartLinkData": {"ids": []},
  "media": ["<release URL>"], "mediaAltText": [],
  "providers": [{"network": "youtube"}],
  "publicationDate": {"dateTime": "YYYY-MM-DDT19:00:00", "timezone": "Asia/Yerevan"},
  "text": "<description>",
  "youtubeData": {"title": "<title>", "type": "short", "privacy": "public",
                  "tags": ["facts", "science", "did you know", "sounds fake", "<topic tags>"],
                  "category": "EDUCATION", "madeForKids": false, "isAiGeneratedContent": false}
}
```
- **Title:** ≤ 70 characters, curiosity-driven, ends with `#shorts`. e.g. `A Day on Venus Is Longer Than Its Year 🤯 #shorts`
- **Description:** 2–3 short lines: the fact in one sentence, one extra detail, then
  `Follow @SoundsFake for a new fact every day.` and hashtags `#shorts #facts #didyouknow` + 2 topic tags.
  Add a line `Sources: <1–2 source names>`.

## 7. Record and report
Set the plan entry's `status` to `scheduled`, add `video_url`, `title`, `metricool_url` (the `plannerUrl`), commit
`Day NN: <topic>` and push. Then message the user: title, publish time, Metricool link.

**If any step fails:** do not schedule a half-finished video. Set `status` to `failed` with a `note` saying why,
commit and push, and message the user what went wrong.
