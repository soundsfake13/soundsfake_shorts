"""Record a scheduled short in plan.json + STYLES.md, commit and push.
Usage: python3 scripts/record_short.py DAY "TITLE" METRICOOL_UUID STYLE ENGINE_PATH "REFERENCE / IDEA" [NOTE]
"""
import json, subprocess, sys
day, title, uuid, style, engine, ref = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
note = sys.argv[7] if len(sys.argv) > 7 else ""
sh = lambda c: subprocess.run(c, shell=True, check=True)
sh("git fetch -q origin main && git rebase -q origin/main")
d = json.load(open("plan.json"))
for e in d["days"]:
    if e["day"] == day:
        e.update(status="scheduled", title=title, style=style,
                 video_url=f"https://raw.githubusercontent.com/soundsfake13/soundsfake_shorts/main/videos/day{day:02d}.mp4",
                 metricool_url=f"https://app.metricool.com/planner/calendar?blogId=7729832&openWithPostUuid={uuid}")
        if note: e["note"] = note
        slot = e.get("time", "19:00")
json.dump(d, open("plan.json", "w"), indent=2, ensure_ascii=False)
s = open("STYLES.md").read()
row = f"| {day} ({slot}) | {style} | `{engine}` | {ref} |\n"
if f"| {day} (" not in s:
    s = s.replace("| — | ink (unused so far)", row + "| — | ink (unused so far)", 1)
open("STYLES.md", "w").write(s)
sh("git add -A && git commit -q -m 'Day %d: %s — scheduled' -m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' && git push -q origin main" % (day, title.replace("'", "")))
print("recorded day", day)
