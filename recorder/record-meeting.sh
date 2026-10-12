#!/bin/zsh
# Record a meeting on macOS: system audio (whatever you hear) + your microphone
# -> one mono .m4a, ready to drop into the Drive folder for transcribe.py.
#
# Usage:  recorder/record-meeting.sh [meeting-name]
# Stop:   press q (or Ctrl+C)
#
# Environment:
#   MEETINGS_DIR   where recordings are saved (default: ~/Meetings)

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
HERE="${0:A:h}"
SOURCE="$HERE/main.swift"
BINARY="$HERE/bin/meeting-recorder"
OUT_DIR="${MEETINGS_DIR:-$HOME/Meetings}"

# --- Requirements -------------------------------------------------------------
if ! command -v swiftc >/dev/null; then
  echo "❌ Swift compiler not found. Install Apple's Command Line Tools once with:"
  echo "   xcode-select --install"
  exit 1
fi
if ! command -v ffmpeg >/dev/null; then
  echo "❌ ffmpeg not found. Install it with:  brew install ffmpeg"
  echo "   (or see docs/MEETING_RECORDER.md for a pre-built download)"
  exit 1
fi

# Build on first run, and again whenever main.swift changes.
if [[ ! -x "$BINARY" || "$SOURCE" -nt "$BINARY" ]]; then
  echo "🔧 Building the recorder (first run only)..."
  mkdir -p "${BINARY:h}"
  swiftc -O -parse-as-library -target "$(uname -m)-apple-macos13.0" "$SOURCE" -o "$BINARY" || exit 1
fi

# --- Record -------------------------------------------------------------------
mkdir -p "$OUT_DIR"
NAME="${1:-meeting}"
BASE="$OUT_DIR/$(date +%Y-%m-%d_%H-%M)_${NAME}"
SYSTEM="$BASE.system.caf"
MIC="$BASE.mic.caf"
OUTPUT="$BASE.m4a"

"$BINARY" "$SYSTEM" "$MIC" || exit 1

# --- Mix ----------------------------------------------------------------------
# Mixing happens after recording, not in real time: real-time mixing of two
# devices with different clocks is what caused clicks in earlier versions.
# Each track is levelled on its own (dynaudnorm), so a quiet side — a soft-spoken
# participant, a low call volume, a distant mic — comes up to speech level;
# alimiter then keeps the sum from clipping.
echo "🎚  Mixing..."
for f label in "$SYSTEM" "System audio" "$MIC" "Microphone"; do
  if [[ -s "$f" ]]; then
    peak=$(ffmpeg -hide_banner -i "$f" -af astats=measure_perchannel=none -f null - 2>&1 \
      | awk -F': ' '/Peak level dB/ {print $2}')
    echo "   $label: peak ${peak%.*} dB"
  else
    echo "   ⚠️  $label: nothing recorded!"
  fi
done

INPUTS=() ; FILTER="" ; n=0
for f in "$SYSTEM" "$MIC"; do
  [[ -s "$f" ]] || continue
  INPUTS+=(-i "$f")
  # ${n}, not $n: in zsh "$n:a" means "absolute path of $n".
  FILTER+="[${n}:a]aresample=48000,aformat=channel_layouts=stereo,pan=mono|c0=0.5*c0+0.5*c1,"
  FILTER+="dynaudnorm=f=300:g=15:p=0.9:m=12:t=0.001[a${n}];"
  n=$((n + 1))
done
if (( n == 0 )); then
  echo "❌ Nothing was recorded."; exit 1
elif (( n == 1 )); then
  FILTER+="[a0]alimiter=limit=0.95[out]"
else
  FILTER+="[a0][a1]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[out]"
fi

if ffmpeg -hide_banner -loglevel error -y "${INPUTS[@]}" -filter_complex "$FILTER" \
     -map "[out]" -c:a aac -b:a 96k "$OUTPUT"; then
  rm -f "$SYSTEM" "$MIC"
  echo "✅ Saved: $OUTPUT"
else
  echo "❌ Mixing failed. The raw tracks were kept:"
  echo "   $SYSTEM"
  echo "   $MIC"
  exit 1
fi
