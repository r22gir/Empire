# 🚨 CRASH INCIDENT REPORT

**Date:** 2026-02-23
**Time:** ~Current session
**Reported by:** User
**Assigned to:** MAX (IT)

## Issue
System crashed during AI photo analysis testing with Ollama LLaVA.

## Likely Cause
- LLaVA model consuming too much RAM (uses 4-8GB)
- Multiple services running simultaneously

## Action Items for MAX
1. Check: `dmesg | grep -i "killed process"`
2. Check: `journalctl -xe | grep -i "out of memory"`
3. Add swap space if needed
4. Consider using smaller AI model

## Status
- [ ] Investigating
- [ ] Root cause identified
- [ ] Fix implemented
