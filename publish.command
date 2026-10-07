#!/bin/zsh
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "$(dirname "$0")" || exit 1
echo "=== lecture-transcriber → GitHub ==="
set -e
if [ ! -d .git ]; then git init -q -b main; fi
echo "publish.command" >> .git/info/exclude
git add -A
git commit -qm "Initial release v1.0.0" || true
if ! gh repo view arif7esat/lecture-transcriber >/dev/null 2>&1; then
  gh repo create arif7esat/lecture-transcriber --public --source . --push \
    --description "Google Drive recordings → Whisper large-v3 transcripts → LLM-ready chunks. Free on Colab, one click."
else
  git remote get-url origin >/dev/null 2>&1 || git remote add origin "$(gh repo view arif7esat/lecture-transcriber --json sshUrl -q .sshUrl)"
  git push -u origin main
fi
gh repo edit arif7esat/lecture-transcriber --visibility public --accept-visibility-change-consequences 2>/dev/null || true
gh repo edit arif7esat/lecture-transcriber --add-topic whisper,faster-whisper,speech-to-text,transcription,google-colab,google-drive,lecture-notes,llm,study-tools
gh release view v1.0.0 -R arif7esat/lecture-transcriber >/dev/null 2>&1 || \
  gh release create v1.0.0 -R arif7esat/lecture-transcriber --title "v1.0.0" --notes "First public release. See CHANGELOG.md."
echo
gh repo view arif7esat/lecture-transcriber --json url,visibility -q '"DONE: " + .url + "  (" + .visibility + ")"'
rm -f -- "$0"
