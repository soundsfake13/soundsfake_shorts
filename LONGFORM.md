# Long-form pipeline — "Sounds Fake: Deep Dive" (regular YouTube videos, not Shorts)

Twice a week — **Tuesday and Friday at 21:00 Asia/Yerevan** — one **8–10 minute, 16:9 (1920×1080)** video about
**one topic in depth**: 10 genuinely jaw-dropping facts, one per chapter. The plan is `longplan.json`.
A scheduled task runs the day before (Monday / Thursday) and makes the next episode.

## 1. Pick the episode
Take the `longplan.json` episode whose `date` is **tomorrow**. If it is `scheduled`/`published`, stop ("nothing to do").
Check Metricool `getScheduledPosts` for a YouTube post at 21:00 that day — never double-post.

## 2. Choose only REALLY cool facts (the most important step)
The bar is: *would a normal person say "no way, that can't be true" and tell a friend?* `fact_ideas` is only a
starting list — replace weak ones. Prefer facts with a number or image you can SHOW, a surprising comparison, or a
twist. Avoid trivia that's "interesting" but not jaw-dropping, and avoid anything shaky or contested.
Verify **every** fact with **≥ 2 reliable sources** (NASA/ESA, universities, museums, peer-reviewed papers, major
science outlets). If two good sources disagree, soften ("about", "scientists think") or drop it. Popular legends
(e.g. "archaeologists ate tomb honey") must be checked — debunk or drop. Save sources to
`specs/long/epNN_<slug>.sources.md`.

## 3. Script → `specs/long/epNN_<slug>.json` (study `specs/long/ep01_space.json` first)
- **Cold open (first 15 s) decides retention.** Frame 0 = the most jaw-dropping visual + a big claim on screen; the
  voice starts immediately with the best surprising fact; then promise the best one for the end
  ("Before this video ends, you'll know where it rains diamonds"); then "All real, sources in the description."
- 10 chapters, escalating; the **most mind-blowing fact is #10** (the promised payoff). Each chapter: a `chapter` card
  ("Number three."), 3–5 beats, and a vivid comparison or "so what". Something visual changes every 3–6 s.
- A 20-second quick recap before the outro, then the outro: "Which one sounded the most fake? Tell me in the
  comments… new deep dive every Tuesday and Friday" + the FAKE → TRUE switch.
- **1,150–1,350 words**, speed ~0.93 → 8–9 minutes. Numbers spelled out in `text`, digits in `caption`.
  Family-safe, no logos/brand characters/real people's likenesses.

## 4. Engine
Copy `engine/long/space_deep_dive.py` to `engine/long/epNN_<topic>.py` and adapt the visual beats to the topic
(new beat functions in the same polished style: glowing type, chapter cards, counters, comparisons, lower-third
captions, corner chapter tracker). Give each episode a look that fits its topic (e.g. deep sea → dark blue
bioluminescence; history → archival paper and film grain; body → clean medical-illustration style).
The voice cache (`~/.cache/sf_tts`) makes re-renders fast, so preview freely:
```bash
python3 engine/long/epNN_<topic>.py specs/long/epNN_<slug>.json out/epNN.mp4 0.0,3,20,60,120,240,400   # frames only
python3 engine/long/epNN_<topic>.py specs/long/epNN_<slug>.json out/epNN.mp4                          # full (~15 min)
```
**Look at frame 0.0 first** — it must show the hook. Check that the full render is 8–10 min and < 95 MB
(re-encode with a higher `-crf` if needed).

## 5. Thumbnail (1280×720 JPG) → `thumbs/epNN.jpg`
2–4 huge words with a curiosity gap (not the title), one striking visual, high contrast, readable on a phone.
See `engine/long/thumb_ep01.py`. Never put text over the bottom-right corner (YouTube's timestamp sits there).

## 6. Host and schedule
```bash
bash scripts/publish_video.sh epNN out/epNN.mp4 "<title>"     # -> raw URL of videos/epNN.mp4
git add -f thumbs/epNN.jpg && git commit -m "Thumbnail epNN" && git push   # raw URL of the thumbnail
```
Metricool `createScheduledPost`, `blogId` 7729832, date `YYYY-MM-DDT21:00:00+04:00`, info:
`providers` [{"network":"youtube"}], `media` [video URL], `videoThumbnailUrl` = thumbnail URL (if Metricool rejects it
with VIDEO_THUMBNAIL_NOT_APPLICABLE, resend without it and tell the user), `firstCommentText` = a question,
`youtubeData`: {"title": "<≤ 70 chars, curiosity first>", "type": "video", "privacy": "public",
"category": "EDUCATION", "madeForKids": false, "isAiGeneratedContent": false, "tags": [...]}.
**Description**: 2-line hook, then **chapters** with timestamps (`0:00 Intro`, then each chapter card's start time —
the engine writes them to `<out>_chapters.txt`), then "Sources:" (the ones you checked), then
"New deep dive every Tuesday & Friday. Daily Shorts on the channel. #facts #science #didyouknow".

## 7. Record
Update the episode in `longplan.json` (status, title, video_url, thumb_url, metricool_url), commit, push, and message
the user. On failure: status `failed` + note, push, report.
