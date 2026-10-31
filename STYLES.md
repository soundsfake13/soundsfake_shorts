# Style catalog — every video has its own look

Rule: **each short gets a visual style designed for its topic, never reused.** Add a row here for every new video.
Inspiration: browse https://claudevideo.org (categories Motion Graphics, Explainers, Stories, 3D Scenes, Art) and pick the
reference that best fits the topic; the plan's `style_idea` is the starting brief.

| day | style | engine | reference / idea |
|---|---|---|---|
| 1 | kinetic | `engine/kinetic_short.py` | Bold type and a spinning cube in a 15-second motion reel |
| 2 | trailcam | `engine/styles/day02_trailcam.py` | Infrared wildlife trail camera (own idea: wombats are nocturnal) |
| 3 | abyss | `engine/styles/day03_abyss.py` | Deep-sea bioluminescence + VHS rewind (glow technique from 'Ray-traced black hole') |
| 4 | strata | `engine/styles/day04_strata.py` | Geology-survey dig through layered rock: depth gauge in millions of years, embossed fossils found with survey rings, slab-serif field labels, pull-back to a core sample (brief: 'Animated timeline of humanity'; claudevideo.org was unreachable this run) |
| 5 | clock | `engine/clock_short.py` | Human inventions unfold on a one-day clock toward midnight |
| 6 | paper | `engine/paper_short.py` | Paper-cutout girl writes a question, not a task |
| 13 | space | `engine/space_short.py` | Ray-traced black hole bends its glowing accretion disk |
| — | ink (unused so far) | `engine/ink_short.py` | Grainy silhouettes and ink-blot type form a title card |

## Toolkit for building a new style
- `engine/core.py` — narration + word timings (`narrate`), audio mix with ducking (`write_audio`), `tone`/`place` for
  composing original music, caption grouping, easing, and `render()` (one ffmpeg pass, temp file renamed on success).
- The existing engines are working examples of very different looks — copy techniques freely:
  cut-paper layers with shadows and boil (`paper`), per-pixel shaded spheres, rings and bloom (`space`), editorial
  data-viz dials (`clock`), film grain and ink-forming type (`ink`), motion-blurred kinetic type and 3D cubes (`kinetic`).
- Fonts: Inter Display (system or `FONT_DIR`), `engine/fonts/` (Fredoka, DM Serif Display). More free fonts can be
  downloaded from `https://raw.githubusercontent.com/google/fonts/main/ofl/<family>/…` into `engine/fonts/` (OFL only).
