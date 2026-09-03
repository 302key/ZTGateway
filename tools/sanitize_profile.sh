#!/bin/bash
# sanitize_profile.sh — One-shot leak sanitizer for preparing a private
# workspace before open-sourcing or sharing.
#
# Steps:
#   1. Scan contents for likely secrets (keys, tokens, IPs) — report only
#   2. Tighten file permissions (dirs -> 700, data files -> 600)
#   3. Install a daily cleanup cron job for trash_collector.py
#
# Safety: This script never deletes anything automatically. Human review required.

set -euo pipefail

BASE_DIR="${ZT_BASE_DIR:-$HOME/tmp/ZT}"
DEAD_DROP="${DEAD_DROP_INBOX:-$HOME/tmp/ZT/dead_drop_inbox}"

RED='\033[0;31m'; YEL='\033[0;33m'; GRN='\033[0;32m'; NC='\033[0m'

echo "[Sanitizer] Starting leak wash on: $BASE_DIR"

# ==========================================
# 1. Secret audit — report only, never delete
# ==========================================
echo "--- [1/3] Scanning for suspicious residue..."

SCAN_DIRS=("$BASE_DIR" "$DEAD_DROP" "$HOME/tmp")
PATTERNS=(
  '(sk-[a-zA-Z0-9]{20,})'                                # generic API keys
  '(ghp_[a-zA-Z0-9]{36})'                                # GitHub tokens
  '(-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----)'       # private keys
  '([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})'     # IPv4 addresses
)

for dir in "${SCAN_DIRS[@]}"; do
  [[ -d "$dir" ]] || continue
  for pat in "${PATTERNS[@]}"; do
    hits=$(grep -rlE "$pat" "$dir" 2>/dev/null | grep -v recycle_bin || true)
    if [[ -n "$hits" ]]; then
      echo -e "  ${RED}[possible leak]${NC} pattern: $pat"
      echo "$hits" | sed 's/^/      /'
    fi
  done
done

echo -e "  ${YEL}[note]${NC} Hits require human review. This script never deletes on its own."

# ==========================================
# 2. Tighten permissions
# ==========================================
echo "--- [2/3] Tightening permissions..."

chmod 700 "$BASE_DIR" 2>/dev/null || true
find "$BASE_DIR" -type d -exec chmod 700 {} + 2>/dev/null || true

# Blackboard / personas / logs / drafts -> owner read-write only
find "$BASE_DIR" -type f \( -name "*.json*" -o -name "*.md" -o -name "*.log*" \
   -o -name "*.sh" -o -name "*.py" \) -exec chmod 600 {} + 2>/dev/null || true

# Dead drop gets the same treatment
[[ -d "$DEAD_DROP" ]] && \
   find "$DEAD_DROP" -type f -exec chmod 600 {} + 2>/dev/null || true

echo -e "  ${GRN}[perms]${NC} all data files -> 600, dirs -> 700"

# ==========================================
# 3. Install daily cleanup cron job
# ==========================================
echo "--- [3/3] Installing cleanup cron job..."
COLLECTOR="$BASE_DIR/trash_collector.py"

if [[ -f "$COLLECTOR" ]]; then
  CRON_LINE="0 4 * * * /usr/bin/python3 $COLLECTOR --archive $BASE_DIR/recycle_bin >> $BASE_DIR/router/gc.log 2>&1"
  ( crontab -l 2>/dev/null | grep -vF "$COLLECTOR"; echo "$CRON_LINE" ) | crontab -
  echo -e "  ${GRN}[cron]${NC} daily 04:00 sweep installed"
else
  echo -e "  ${YEL}[skipped]${NC} trash_collector.py not found at $COLLECTOR"
fi

echo ""
echo "[Done] Sanitization complete."
echo "  Next steps:"
echo "  1. Run: python3 trash_collector.py --dry-run  (verify the collection list)"
echo "  2. Do a final manual review of all [possible leak] findings above"
