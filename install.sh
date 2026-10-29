#!/usr/bin/env bash
# Link every skill under skills/ into ~/.claude/skills/ so it can be called as /<name>.
#   ./install.sh            link (or refresh) all skills
#   ./install.sh uninstall  remove only the links this script created
# Existing directories that are not links are never touched.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mode="${1:-install}"
mkdir -p "$dest"
for dir in "$here"/skills/*/; do
  src="${dir%/}"
  [ -f "$src/SKILL.md" ] || continue
  name="$(basename "$src")"
  target="$dest/$name"
  case "$mode" in
    install)
      if [ -L "$target" ]; then
        ln -sfn "$src" "$target"; echo "updated  /$name -> $src"
      elif [ -e "$target" ]; then
        echo "skipped  /$name: $target exists and is not a link" >&2
      else
        ln -s "$src" "$target"; echo "linked   /$name -> $src"
      fi ;;
    uninstall)
      if [ -L "$target" ] && [ "$(readlink "$target")" = "$src" ]; then
        unlink "$target"; echo "unlinked /$name"
      fi ;;
    *) echo "usage: $0 [install|uninstall]" >&2; exit 2 ;;
  esac
done
