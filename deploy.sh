#!/usr/bin/env bash
# Move code between this Mac and the PiCar over SSH. Only changed files transfer.
# NEVER deletes files on either side. Push previews first, then asks before sending.
#
# Usage:
#   ./deploy.sh diff [folder...]    # show which files differ (safe, read-only)
#   ./deploy.sh pull [folder...]    # copy robot's files DOWN to this Mac (preview, then confirm)
#   ./deploy.sh push [folder...]    # send Mac files UP to the robot (preview, then confirm)
#
# folder defaults to:  ai_control web
# Examples:
#   ./deploy.sh diff web            # what differs in web/ ?
#   ./deploy.sh pull web            # grab robot-side edits (e.g. move.py) before pushing
#   ./deploy.sh push ai_control     # push only ai_control
set -euo pipefail

PI="${PICAR_SSH:-giannisp09@192.168.1.82}"
SSH_KEY="${PICAR_KEY:-$HOME/.ssh/picar_ed25519}"
REMOTE_DIR="/home/giannisp09/Desktop/adeept_picar-b2"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_TARGETS=(ai_control web)

# Use the dedicated PiCar key if it exists; otherwise fall back to default ssh.
if [ -f "$SSH_KEY" ]; then
  SSH_CMD="ssh -i $SSH_KEY"
else
  SSH_CMD="ssh"
fi
RSH=(-e "$SSH_CMD")

EXCLUDES=(--exclude '__pycache__/' --exclude '*.pyc' --exclude '.DS_Store' --exclude '._*' --exclude 'dist/')

CMD="${1:-diff}"
shift || true
TARGETS=("$@")
[ ${#TARGETS[@]} -eq 0 ] && TARGETS=("${DEFAULT_TARGETS[@]}")

confirm() {
  read -r -p "$1 [y/N] " ans
  [[ "$ans" == "y" || "$ans" == "Y" ]]
}

# run_sync <src> <dst> : preview (dry-run) then confirm then real run. No --delete, ever.
run_sync() {
  local src="$1" dst="$2"
  echo "--- preview: $src  ->  $dst"
  rsync -azi --dry-run "${RSH[@]}" "${EXCLUDES[@]}" "$src" "$dst" || true
  echo
  if confirm "apply the above transfer?"; then
    rsync -azi "${RSH[@]}" "${EXCLUDES[@]}" "$src" "$dst"
    echo "applied."
  else
    echo "skipped."
  fi
}

for t in "${TARGETS[@]}"; do
  local_path="$LOCAL_DIR/$t"
  remote_path="$PI:$REMOTE_DIR/$t"
  case "$CMD" in
    diff)
      echo "== diff $t (i = differs/new; '>' would go to robot, '<' robot has newer) =="
      echo "-- Mac vs Robot (what push WOULD change on robot):"
      rsync -azin "${RSH[@]}" "${EXCLUDES[@]}" "$local_path/" "$remote_path/" || true
      echo "-- Robot vs Mac (what robot has that differs — pull candidates):"
      rsync -azin "${RSH[@]}" "${EXCLUDES[@]}" "$remote_path/" "$local_path/" || true
      echo
      ;;
    pull)
      [ -e "$local_path" ] || mkdir -p "$local_path"
      run_sync "$remote_path/" "$local_path/"
      ;;
    push)
      if [ ! -e "$local_path" ]; then echo "skip: $t not found locally" >&2; continue; fi
      run_sync "$local_path/" "$remote_path/"
      ;;
    *)
      echo "unknown command: $CMD (use diff | pull | push)" >&2; exit 1 ;;
  esac
done
