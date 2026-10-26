#!/usr/bin/env bash
# Save the Gemini API key for the navigation chatbot. run.sh reads it when it starts myguro.
#
#   ./set-gemini-key.sh            asks for the key (what you type is not shown)
#   ./set-gemini-key.sh --remove   deletes the saved key

set -e
cd "$(dirname "$0")"

# instance/ is private and not committed to git (see .gitignore), so the key stays on this computer
file=instance/gemini.env
mkdir -p instance

if [ "$1" = "--remove" ]; then
  rm -f "$file"
  echo "Key removed."
  exit 0
fi

read -rsp "Paste your Gemini API key: " key
echo
if [ -z "$key" ]; then
  echo "No key entered. Nothing saved." >&2
  exit 1
fi

# Only the owner can read the file. The quotes keep odd characters safe when run.sh reads it.
umask 077
printf 'export GEMINI_API_KEY=%q\n' "$key" > "$file"
echo "Saved in $file. Restart myguro with ./run.sh, then turn the chatbot on in Settings."
