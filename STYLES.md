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
| 7 | codex | `engine/styles/day07_codex.py` | Two books on one screen: illuminated manuscript (vellum, gold-leaf type with moving sheen, drop caps, Fraktur script written by a quill) vs flat-colour screenfold codex panels (amate paper, terracotta/turquoise/ochre, step-fret borders, footprints, hill place-signs); page-turn transitions; lute + hand-drum bed (brief: 'Jade-green Chinese landscape painting comes alive'; claudevideo.org unreachable this run) |
| 8 (19:00) | risograph | `engine/styles/day08_risograph.py` | Risograph print: pink/blue/yellow spot inks multiplied, halftone dots, mis-registration, rubber stamps (ref: halftone portrait overlay) |
| 34 (23:00) | plate-astronomy | `engine/styles/day34_plates.py` | 1930s glass photographic plates: negative star field, blink comparator, grease-pencil circles, handwritten labels, typewriter dates (own idea) |
| 9 (19:00) | pulsar-cinema | `engine/styles/day09_pulsar.py` | Cold monochrome cinema: sweeping pulsar beams, anamorphic flares, letterbox, grain, wide-tracked titles (ref: ray-traced black hole, but cold) |
| 10 (19:00) | voxel-chess | `engine/styles/day10_voxel.py` | Isometric voxel world: cube-built chessboard, glowing move tiles, numbers grow into voxel towers, chiptune (ref: Voxel pelican rides a bike) |
| 35 (23:00) | wallpaper-60s | `engine/styles/day35_wallpaper.py` | 1960s mod wallpaper: bold repeating flowers/circles/waves in mustard-orange-teal-chocolate, glossy popping bubbles, Righteous retro type |
| 36 (23:00) | apothecary | `engine/styles/day36_apothecary.py` | Victorian apothecary label: double-rule borders, black+vermilion letterpress, serif display, bottle, pill box, newspaper feud, QUACKERY stamps |
| 11 (19:00) | hanafuda | `day11_hanafuda.py` | Jade-green Chinese landscape painting comes alive |
| 37 (23:00) | felt-craft | `day37_felt.py` | Cozy handmade felt/wool craft |
| — | ink (unused so far) | `engine/ink_short.py` | Grainy silhouettes and ink-blot type form a title card |
| 32 (23:00) | pointillism | `engine/styles/day32_pointillism.py` | Seurat-like dots morphing galaxy ↔ forest; hook claim on a navy plate at frame 0 (first video to the hook rules) |
| 31 (23:00) | honeycomb | `engine/styles/day31_honeycomb.py` | Golden honeycomb macro: cells filling with amber, drips, serif type on wax labels (own idea) |

## Toolkit for building a new style
- `engine/core.py` — narration + word timings (`narrate`), audio mix with ducking (`write_audio`), `tone`/`place` for
  composing original music, caption grouping, easing, and `render()` (one ffmpeg pass, temp file renamed on success).
- The existing engines are working examples of very different looks — copy techniques freely:
  cut-paper layers with shadows and boil (`paper`), per-pixel shaded spheres, rings and bloom (`space`), editorial
  data-viz dials (`clock`), film grain and ink-forming type (`ink`), motion-blurred kinetic type and 3D cubes (`kinetic`).
- Fonts: Inter Display (system or `FONT_DIR`), `engine/fonts/` (Fredoka, DM Serif Display). More free fonts can be
  downloaded from `https://raw.githubusercontent.com/google/fonts/main/ofl/<family>/…` into `engine/fonts/` (OFL only).
