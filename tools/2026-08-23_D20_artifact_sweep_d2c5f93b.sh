#!/usr/bin/env bash
# Artifact sweep — find delivered work and generators living outside git.
# READ ONLY. Deletes nothing, moves nothing, commits nothing.
# Doctrine §VIII: code born in a strategic session is committed the same day,
# or it does not exist. This finds what has not been.

set -uo pipefail
REPO="$HOME/empire-repo-main"
OUT="$HOME/artifact_sweep_$(date +%Y-%m-%d_%H%M%S).txt"

exec > >(tee "$OUT") 2>&1

echo "ARTIFACT SWEEP — $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "Repo: $REPO"
echo "Report: $OUT"
echo

# --- where to look -----------------------------------------------------
ROOTS=()
for d in "$HOME/Downloads" "$HOME/Desktop" "$HOME/Documents" "$HOME/Pictures" \
         /data /ssd /media/rg; do
  [ -d "$d" ] && ROOTS+=("$d")
done
echo "SEARCH ROOTS: ${ROOTS[*]}"
echo

# --- keywords that mark Empire work ------------------------------------
KEYS='willard|o.?neil|oneil|cst-23|bozzuto|EST-2026|mclean|whittington|walnut|sofa.?surround|xcarve|x-carve|slot.?bench|empire|woodcraft|drapery|roman.?shade|valance|cornice|banquette|headboard|presentation.?set|isometric|golden|flatfold|flat.?fold|delicias|label.?station|craftforge|relist'

echo "======================================================================"
echo "1. CANDIDATE FILES BY NAME (pdf, py, html, svg, dxf, stl, md, json)"
echo "======================================================================"
find "${ROOTS[@]}" -maxdepth 5 -type f \
     \( -iname '*.pdf' -o -iname '*.py' -o -iname '*.html' -o -iname '*.svg' \
        -o -iname '*.dxf' -o -iname '*.stl' -o -iname '*.md' -o -iname '*.json' \
        -o -iname '*.ipynb' -o -iname '*.zip' \) 2>/dev/null \
  | grep -iE "$KEYS" \
  | sort > /tmp/sweep_byname.txt
wc -l < /tmp/sweep_byname.txt | xargs echo "matches:"
echo

echo "======================================================================"
echo "2. PYTHON / HTML GENERATORS BY CONTENT (not caught by filename)"
echo "======================================================================"
find "${ROOTS[@]}" -maxdepth 5 -type f \( -iname '*.py' -o -iname '*.html' \) 2>/dev/null \
  | while read -r f; do
      if grep -qiE "$KEYS" "$f" 2>/dev/null; then echo "$f"; fi
    done | sort > /tmp/sweep_bycontent.txt
comm -13 /tmp/sweep_byname.txt /tmp/sweep_bycontent.txt > /tmp/sweep_contentonly.txt
wc -l < /tmp/sweep_contentonly.txt | xargs echo "content-only matches (name did not match):"
cat /tmp/sweep_contentonly.txt
echo

echo "======================================================================"
echo "3. THE ANSWER — WHICH OF THESE ARE ALREADY IN GIT?"
echo "======================================================================"
cat /tmp/sweep_byname.txt /tmp/sweep_bycontent.txt | sort -u > /tmp/sweep_all.txt
IN_GIT=0; NOT_IN_GIT=0
: > /tmp/sweep_missing.txt
while read -r f; do
  base="$(basename "$f")"
  # strip browser rename suffixes:  foo(1).pdf  foo-2.pdf
  stem="$(echo "$base" | sed -E 's/\(([0-9]+)\)//g; s/-[0-9]+(\.[A-Za-z0-9]+)$/\1/')"
  if git -C "$REPO" ls-files | grep -qiF "$stem"; then
    IN_GIT=$((IN_GIT+1))
  else
    NOT_IN_GIT=$((NOT_IN_GIT+1))
    printf '%10s  %s\n' "$(stat -c %s "$f" 2>/dev/null)" "$f" >> /tmp/sweep_missing.txt
  fi
done < /tmp/sweep_all.txt

echo "IN GIT:     $IN_GIT"
echo "NOT IN GIT: $NOT_IN_GIT"
echo
echo "--- NOT IN GIT, largest first (size bytes / path) ---"
sort -rn /tmp/sweep_missing.txt
echo

echo "======================================================================"
echo "4. DIRECTORIES WORTH A LOOK (3+ unversioned Empire files)"
echo "======================================================================"
awk '{ $1=""; sub(/^ +/,""); print }' /tmp/sweep_missing.txt \
  | xargs -r -n1 dirname 2>/dev/null | sort | uniq -c | sort -rn \
  | awk '$1 >= 3 { printf "%4d  %s\n", $1, substr($0, index($0,$2)) }'
echo

echo "======================================================================"
echo "5. ARCHIVES — may contain generators (not opened by this sweep)"
echo "======================================================================"
find "${ROOTS[@]}" -maxdepth 5 -type f -iname '*.zip' 2>/dev/null \
  | while read -r z; do printf '%10s  %s\n' "$(stat -c %s "$z")" "$z"; done | sort -rn
echo

echo "======================================================================"
echo "DONE. Nothing was moved, deleted or committed."
echo "Report saved to: $OUT"
echo "Next: review section 3, then commit what matters into reference/."
echo "======================================================================"
