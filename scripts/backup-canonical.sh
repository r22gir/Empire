#!/usr/bin/env bash
# backup-canonical.sh — Empire canonical backup (R2, 2026-08-22)
#
# Backs up the canonical data sources (~/empire-data/*) and the canonical
# MAX memory file. Uses SQLite's online backup API so the copy is safe
# against concurrent writers.
#
# HARD RULES (from dispatch R2):
#   * Canonical sources ONLY. Never the old lane (~/empire-repo/backend/data/).
#   * No deletion. Retention is a separate, deliberate decision.
#   * No git stash. No writes into any repo tree.
#   * Verify after writing: row count of one known table per DB + PRAGMA integrity_check.
#   * Exit non-zero if any check fails.
#   * Log to ~/backups/backup.log.
#
# NOT a replacement for ~/empire-repo/scripts/backup-daily.sh yet — that
# schedule is still on the user crontab; founder will swap it manually.

set -u  # NOTE: intentionally NOT `set -e` — we want to keep going through
        # per-file checks and report all failures, then exit non-zero if any.

# --- Config ------------------------------------------------------------------

PY="/home/rg/empire-repo-main/backend/venv/bin/python"
BACKUPS_ROOT="$HOME/backups"
LOGFILE="$BACKUPS_ROOT/backup.log"
TS="$(date +%Y-%m-%d_%H%M)"
DEST="$BACKUPS_ROOT/$TS"

# Each entry: source path | dest filename | verify-table ("" for plain files)
# verify-table is the single known table to COUNT(*) for the post-write check.
TARGETS=(
    "/home/rg/empire-data/empire.db|empire.db|quotes_v2"
    "/home/rg/empire-data/intake.db|intake.db|intake_projects"
    "/home/rg/empire-data/brain/memories.db|memories.db|memories"
    "/home/rg/empire-data/brain/token_usage.db|token_usage.db|token_usage"
    "/home/rg/empire-data/brain/unified_messages.db|unified_messages.db|unified_messages"
    "/home/rg/empire-repo-main/max/memory.md|memory.md|"
)

# --- Helpers -----------------------------------------------------------------

log() {
    local line="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$line" >> "$LOGFILE"
    echo "$line"
}

backup_sqlite() {
    # $1 = source path, $2 = dest path, $3 = verify-table
    local src="$1" dst="$2" table="$3"
    local verify_rc=0
    local verify_count="n/a"
    local integ="n/a"

    # 1. Write the backup via SQLite's online backup API.
    "$PY" - "$src" "$dst" <<'PYEOF'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
s = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
d = sqlite3.connect(dst)
with d:
    s.backup(d)
s.close()
d.close()
PYEOF
    local cp_rc=$?
    if [ $cp_rc -ne 0 ]; then
        log "  FAIL  cp(source=$src) exit=$cp_rc"
        return $cp_rc
    fi
    log "  ok    wrote $dst"

    # 2. Read-back row count + integrity check on the COPY (still read-only).
    if [ -n "$table" ]; then
        read verify_count integ < <("$PY" - "$dst" "$table" <<'PYEOF'
import sqlite3, sys
dst, table = sys.argv[1], sys.argv[2]
c = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
n = c.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
integ = c.execute("PRAGMA integrity_check").fetchone()[0]
c.close()
print(n, integ)
PYEOF
        )
        verify_rc=$?
        if [ $verify_rc -ne 0 ]; then
            log "  FAIL  verify(source=$dst table=$table) python-exit=$verify_rc"
            return $verify_rc
        fi
        if [ "$integ" != "ok" ]; then
            log "  FAIL  integrity_check(dst=$dst) = $integ"
            return 2
        fi
        log "  ok    verify dst=$dst table=$table rows=$verify_count integrity=ok"
    fi
    return 0
}

backup_plain() {
    # $1 = source, $2 = dest
    local src="$1" dst="$2"
    if cp -p "$src" "$dst"; then
        log "  ok    wrote $dst (plain cp)"
        return 0
    else
        local rc=$?
        log "  FAIL  cp(source=$src) exit=$rc"
        return $rc
    fi
}

# --- Main --------------------------------------------------------------------

log "========================================"
log "backup-canonical.sh START  dest=$DEST"

if [ ! -x "$PY" ]; then
    log "FATAL  python not found at $PY"
    exit 3
fi

mkdir -p "$DEST"
if [ ! -d "$DEST" ]; then
    log "FATAL  could not create $DEST"
    exit 3
fi

overall_rc=0
total=${#TARGETS[@]}
i=0
while [ $i -lt $total ]; do
    entry="${TARGETS[$i]}"
    src="${entry%%|*}"
    rest="${entry#*|}"
    name="${rest%%|*}"
    table="${rest#*|}"
    [ "$src" = "$entry" ] && table=""

    log "($((i+1))/$total) $src"
    if [ ! -e "$src" ]; then
        log "  SKIP  source missing: $src"
        overall_rc=4
    elif [ -n "$table" ]; then
        backup_sqlite "$src" "$DEST/$name" "$table" || overall_rc=1
    else
        backup_plain "$src" "$DEST/$name" || overall_rc=1
    fi
    i=$((i+1))
done

# --- Summary -----------------------------------------------------------------

if [ $overall_rc -eq 0 ]; then
    log "backup-canonical.sh OK     dest=$DEST files=$total"
else
    log "backup-canonical.sh FAIL   dest=$DEST files=$total rc=$overall_rc"
fi
log "========================================"
exit $overall_rc
