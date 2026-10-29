#!/usr/bin/env bash
# Upload a rendered video as a GitHub release asset and print its public download URL.
# Usage: scripts/publish_video.sh <day-number> <path/to/video.mp4> "<title>"
set -euo pipefail
DAY=$(printf "%02d" "$1"); FILE="$2"; TITLE="${3:-Day $DAY}"
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
TAG="day$DAY"
NAME="day${DAY}.mp4"
cp "$FILE" "/tmp/$NAME"
if gh release view "$TAG" >/dev/null 2>&1; then
  gh release upload "$TAG" "/tmp/$NAME" --clobber >/dev/null
else
  gh release create "$TAG" "/tmp/$NAME" --title "Day $DAY · $TITLE" --notes "Sounds Fake short, day $DAY." >/dev/null
fi
URL="https://github.com/$REPO/releases/download/$TAG/$NAME"
# confirm it is publicly downloadable (follows the redirect to GitHub's file host)
CODE=$(curl -sSL -o /dev/null -w "%{http_code}" -r 0-1023 "$URL" || true)
echo "$URL"
[ "$CODE" = "200" ] || [ "$CODE" = "206" ] || echo "WARNING: public URL returned HTTP $CODE (is the repo public?)" >&2
