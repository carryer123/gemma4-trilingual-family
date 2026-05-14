#!/usr/bin/env bash
set -euo pipefail

ROOT="<repo-root>/Gemma4Good_iPad/vendor/llama.cpp"
PROJECT="$ROOT/examples/llama.swiftui/llama.swiftui.xcodeproj"

if [ ! -d "$PROJECT" ]; then
  echo "missing Xcode project: $PROJECT" >&2
  exit 1
fi

if ! xcodebuild -version >/dev/null 2>&1; then
  echo "Full Xcode is not active. Install Xcode, then run:" >&2
  echo "sudo xcode-select -s /Applications/Xcode.app/Contents/Developer" >&2
  exit 1
fi

cd "$ROOT"
if [ ! -d "$ROOT/build-apple/llama.xcframework" ]; then
  ./build-xcframework.sh
fi

open "$PROJECT"

