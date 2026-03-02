#!/bin/bash
# Collect system diagnostics for EmpireBox crash analysis
# Device: AZW EQ mini PC (Beelink EQR5) running Ubuntu Noble

OUTPUT="/tmp/empirebox_diagnostics.txt"

echo "=== EmpireBox System Diagnostics ===" > "$OUTPUT"
echo "Collected at: $(date)" >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "=== System Info ===" >> "$OUTPUT"
uname -a >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "=== OS Release ===" >> "$OUTPUT"
lsb_release -a >> "$OUTPUT" 2>&1
echo "" >> "$OUTPUT"

echo "=== Memory ===" >> "$OUTPUT"
free -h >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "=== CPU Info ===" >> "$OUTPUT"
lscpu | grep -E "Model name|Socket|Core|Thread|CPU MHz|NUMA" >> "$OUTPUT" 2>&1
echo "" >> "$OUTPUT"

echo "=== Temperatures ===" >> "$OUTPUT"
if command -v sensors &>/dev/null; then
    sensors >> "$OUTPUT" 2>&1
else
    echo "lm-sensors not installed; run: sudo apt install lm-sensors && sudo modprobe k10temp" >> "$OUTPUT"
fi
echo "" >> "$OUTPUT"

echo "=== Docker Containers ===" >> "$OUTPUT"
if command -v docker &>/dev/null; then
    docker ps -a >> "$OUTPUT" 2>&1
    echo "" >> "$OUTPUT"
    echo "=== Docker Stats (snapshot) ===" >> "$OUTPUT"
    docker stats --no-stream >> "$OUTPUT" 2>&1
else
    echo "Docker not available" >> "$OUTPUT"
fi
echo "" >> "$OUTPUT"

echo "=== Disk Usage ===" >> "$OUTPUT"
df -h >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "=== Swap Usage ===" >> "$OUTPUT"
swapon --show >> "$OUTPUT" 2>&1
echo "" >> "$OUTPUT"

echo "=== Loaded Kernel Modules (sensor-related) ===" >> "$OUTPUT"
lsmod | grep -E "k10temp|sp5100|w836|it87|f71|nct" >> "$OUTPUT" 2>&1
echo "" >> "$OUTPUT"

echo "=== Last Boot Errors ===" >> "$OUTPUT"
journalctl -b -1 -p err --no-pager >> "$OUTPUT" 2>/dev/null || echo "No previous boot logs available" >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "=== Current Boot Errors ===" >> "$OUTPUT"
journalctl -b 0 -p err --no-pager --since "1 hour ago" >> "$OUTPUT" 2>/dev/null
echo "" >> "$OUTPUT"

echo "=== Recent Kernel Log (tail 100) ===" >> "$OUTPUT"
dmesg | tail -100 >> "$OUTPUT"
echo "" >> "$OUTPUT"

echo "=== OOM Events ===" >> "$OUTPUT"
dmesg | grep -i "oom\|out of memory\|killed process" >> "$OUTPUT" 2>&1 || echo "No OOM events in dmesg" >> "$OUTPUT"

echo ""
echo "Diagnostics saved to $OUTPUT"
echo "Share this file when reporting crashes."
