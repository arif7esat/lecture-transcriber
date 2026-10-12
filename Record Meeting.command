#!/bin/zsh
# Double-click in Finder to record a meeting. See docs/MEETING_RECORDER.md.
cd "$(dirname "$0")" || exit 1
echo "=== Meeting recorder ==="
read "NAME?Meeting name (optional): "
./recorder/record-meeting.sh "${NAME// /-}"
echo
read "?Press Enter to close this window..."
