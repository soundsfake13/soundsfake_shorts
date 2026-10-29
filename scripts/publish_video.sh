#!/usr/bin/env bash
# Host a rendered video in the repo (videos/dayNN.mp4), push it, and print its public raw URL.
# (Release uploads are not permitted from Claude sessions, so videos live as normal files.)
# Usage: scripts/publish_video.sh <day-number> <path/to/video.mp4> "<title>"
set -euo pipefail
DAY=$(printf "%02d" "$1"); FILE="$2"; TITLE="${3:-Day $DAY}"
cd "$(git rev-parse --show-toplevel)"
REPO=$(git config --get remote.origin.url | sed -E 's#(https://github.com/|git@github.com:)##; s#\.git$##')
BRANCH=$(git rev-parse --abbrev-ref HEAD)
SIZE=$(stat -c %s "$FILE")
[ "$SIZE" -lt 95000000 ] || { echo "video is over 95 MB; re-encode smaller" >&2; exit 1; }
mkdir -p videos
cp "$FILE" "videos/day${DAY}.mp4"
git add -f "videos/day${DAY}.mp4"
git commit -q -m "Video: day $DAY · $TITLE" || true
git push -q origin "$BRANCH"
URL="https://raw.githubusercontent.com/$REPO/$BRANCH/videos/day${DAY}.mp4"
for i in 1 2 3 4 5 6; do
  CODE=$(curl -sSL -o /dev/null -w "%{http_code}" -r 0-1023 "$URL" || true)
  { [ "$CODE" = "200" ] || [ "$CODE" = "206" ]; } && break
  sleep 5
done
echo "$URL"
[ "$CODE" = "200" ] || [ "$CODE" = "206" ] || echo "WARNING: public URL returned HTTP $CODE (is the repo public?)" >&2
