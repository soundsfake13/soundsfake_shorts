# Daily pipeline — "Sounds Fake" YouTube Shorts

This is the procedure the daily scheduled task follows. One run = one video,
scheduled for **tomorrow at 19:00 Asia/Yerevan** (one day of buffer).

## 0. Setup
```bash
bash scripts/setup.sh            # deps, voice model, fonts (prints FONT_DIR export if needed)
```
If it prints an `export FONT_DIR=...` line, export it before rendering.

## 1. Pick the topic
Open `plan.json`. Take the entry whose `date` is **tomorrow** (Yerevan time).
- If its `status` is `scheduled` or `published` (it was made in advance), there is nothing to do: report "tomorrow is
  already scheduled" and stop.
- If it is `planned` (or `failed`), make it.
If no entry has tomorrow's date, report "plan finished" and stop.

Before doing anything else, call Metricool `getScheduledPosts` (brand `7729832`, timezone `Asia/Yerevan`)
for that date. If a YouTube post is already scheduled that day, mark the entry `scheduled` and stop — never double-post.

## 2. Verify the facts (mandatory)
Use web search to confirm every claim in the entry's `facts` field with **at least two reliable sources**
(encyclopedias, universities, museums, science outlets, peer-reviewed papers). If a number or claim can't be
confirmed, soften it ("about", "up to") or drop it. Never add unverified extras.
Write the sources to `specs/dayNN_<slug>.sources.md`.

## 3. Design this video's own style, then write the script → `specs/dayNN_<slug>.json`
**Every short gets a new visual style that fits its topic — never reuse a previous video's look** (check `STYLES.md`).
- If the entry's `style` is one of the existing engines (`kinetic`, `paper`, `space`, `clock`, `ink`) **and it is
  already scheduled**, nothing to do. Otherwise treat `style` + `style_idea` in `plan.json` as the brief.
- Look at https://claudevideo.org (WebFetch the home page or `/videos`, then the 1–2 most relevant video pages) for a
  reference that fits the topic, and decide the look: palette (3–5 colors), textures, typography (1–2 fonts),
  motion language, transitions, and an original music bed that matches the mood.
- Build it as a **new engine** `engine/styles/dayNN_<style>.py` on top of `engine/core.py` (copy techniques from the
  existing engines; see `STYLES.md` → Toolkit). Keep it self-contained so earlier videos still re-render.
- Keep the **channel constants** in every style so the channel stays recognisable:
  same voice (`am_michael`), word-by-word captions in the caption area (y ≈ 1540–1700) styled to fit the look but
  always high-contrast, a thin progress bar at the bottom, and the signature ending — a FAKE → TRUE switch drawn in the
  video's own style, with "Sounds fake? It's true. Follow for more."
- Support the preview mode used by the other engines (`... spec.json out.mp4 2,6,10` writes frames only).
- Add a row to `STYLES.md` (day, style name, engine path, reference) and commit it with the engine.
- Quality bar: it should look intentional and polished, as good as the existing engines. If a style idea proves too
  hard to make look good, simplify it (fewer elements, cleaner shapes) rather than ship something messy; as a last
  resort use the closest existing engine with a clearly different palette and typography, and say so in the report.

Script rules (all styles):
- 25–35 seconds, 7–9 lines. Line 1 = the hook (≤ 10 words), shown big from the very first frame.
- Line 2 is usually "Sounds fake? It's true."
- Spell numbers out in `text` (for the voice) and put digits in `caption`.
- Simple, friendly, family-safe English. No gore, no real-person likenesses, no brand logos or characters.
- Last line always: "Sounds fake? It's true. Follow for more."
- voice `am_michael`; speed 1.0–1.12 to suit the mood.

### Existing engines (toolkit and examples)
**kinetic** (`engine/kinetic_short.py`) — colors `red`, `blue`, `cream`, `ink`, `yellow`; alternate backgrounds.

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
| `jelly` | bobbing flat jellyfish, optional size ruler | `bg`, `color`, `spot`, `r`, `y`, `label`, `label_color`, `ruler`, `sub`, `sub_color`, `sub_y` |
| `cycle` | life-cycle ring with stage nodes; optional shortcut arrow + stamp | `stages`, `icons` (`dot`/`polyp`/`jelly`), `reverse` [from, to], `bg`, `node`, `label`, `label_color`, `stamp`, `stamp_y`, `y`, `R` |
| `sunrise`, `squeeze`, `rock` | specific to days 1–2 | — |
| `toggle` | cursor flips FAKE → TRUE (ending) | `left`, `right`, `click_at` |

**paper** (`engine/paper_short.py`) — colors in `C` (`deep`, `sea`, `light`, `sand`, `cream`, `coral`, `red`, `blue`,
`ink`, `yellow`, `pink`, `green`). Everything is built from `Sheet` layers (rough cut edges + shadow) and `strip()`
paper labels; animate with `paste()`, `boil(t)` (3 drawing variants at 8 fps) and `jit()` (12 fps jitter).

| type | use | params |
|---|---|---|
| `hook` | sea background, hero creature bobbing, paper title strips drop in | `lines`, `hi` {line: word index}, `size` |
| `title` | paper strips on a flat colored sheet | `lines`, `bg`, `colors`, `hi`, `size`, `y` |
| `hearts`, `blood`, `swim`, `crawl` | octopus-specific (day 6) — use as patterns | — |
| `end` | paper FAKE → TRUE switch (ending) | `click_at` |

The only creature sprite so far is `octopus()`. **For a new animal/plant, add a sprite function** in the same way
(layers of simple shapes via `Sheet.add`, 3 variants for boil), and make `hook`/`crawl` take a `creature` param.

**space** (`engine/space_short.py`) — gold/ice glowing type via `gtext()`, planets via `saturn()` / `earth()`,
`comp()` to composite, `bloom()` applied to every frame.

| type | use | params |
|---|---|---|
| `hero` | big planet + title lines | `lines`, `accent` {line: true}, `size`, `y` |
| `words` | glowing title lines over a star zoom | `lines`, `accent`, `size`, `y` |
| `compare` | planet vs tiny Earth + big multipliers | `rows` [[number, label]] |
| `elements` | glowing element tiles (H, He) | `label` |
| `density` | two glowing bars (water vs Saturn) | — |
| `float`, `tub` | Saturn-specific (day 13) — use as patterns | `label` |
| `end` | neon FAKE → TRUE switch (ending) | `click_at` |

For other bodies (neutron star, the Moon, an exoplanet…) add a renderer next to `saturn()` (shaded sphere +
texture + glow) and scenes that use it.

**clock** (`engine/clock_short.py`) — top-level `"span": [start_year, end_year]` (negative = BC; spans ≥ 100,000
years switch labels to "X MILLION YRS AGO" automatically).

| type | use | params |
|---|---|---|
| `headline` | big editorial lines, red accents | `lines`, `accent` {line: 1}, `y`, `size` |
| `clock` | 24-hour dial; hand sweeps from event `from` to `to`, arcs fill, callouts pop, year counter rolls | `events` [[year, label, icon]], `from`, `to`, `title`, `note`, `note_at` |
| `end` | FAKE → TRUE switch (ending) | `click_at` |

Icons: `pyramid`, `crown`, `moon`, `rocket` — add more line icons to `icon()` when needed (keep 6 px line style).
Keep the same `events` list across consecutive clock scenes so the dial feels continuous.

**ink** (`engine/ink_short.py`) — black & white; scenes `title` (silhouette + ink title), `ledger` (ink lines),
`horizon` (figure on a ridge), `heat`, `planet`, `orbit`, `end`. Text forms from ink blots (`Ink` class).
Add history-themed silhouettes (castle, ship, scroll…) as new scenes in the same style.

**New visuals (any style):** if the topic needs a picture the engine lacks, add a reusable scene in **that style's**
look, register it in `SCENES`, and add it to the table above. Never mix styles inside one video.

## 4. Render and check
```bash
python3 engine/styles/dayNN_<style>.py specs/dayNN_<slug>.json out/dayNN.mp4 2,6,10,14   # preview frames only
python3 engine/styles/dayNN_<style>.py specs/dayNN_<slug>.json out/dayNN.mp4              # full render
```
Preview a few frames at full size **before** the full render, at the busiest moments, and look at them. Check: duration 20–45 s; size < 90 MB. Make one contact sheet of
~8 frames and **look at it**: no text cut off at the edges, nothing colliding with the caption area (y ≈ 1540–1700),
every scene readable. Fix and re-render until clean. Grainy/noisy looks compress badly: use `render(..., crf=30)` for those.

## 5. Host the video
```bash
bash scripts/publish_video.sh NN out/dayNN.mp4 "<short title>"   # commits videos/dayNN.mp4, pushes, prints the public raw URL
```
Videos are stored as normal files in `videos/` (GitHub release uploads are blocked in Claude sessions) and served from
`raw.githubusercontent.com`. The repo must be public; the script warns if the URL isn't downloadable. Keep videos small
(most styles are 2–6 MB; ink ~20 MB).

## 6. Schedule on YouTube via Metricool
`createScheduledPost` with `blogId` `7729832`, `date` `YYYY-MM-DDT19:00:00+04:00` and `info`:
```json
{
  "autoPublish": true, "draft": false, "descendants": [], "firstCommentText": "",
  "hasNotReadNotes": false, "shortener": false, "smartLinkData": {"ids": []},
  "media": ["<raw video URL>"], "mediaAltText": [],
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
