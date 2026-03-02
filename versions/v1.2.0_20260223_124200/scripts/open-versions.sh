#!/bin/bash
# Open versions folder
if command -v nautilus &> /dev/null; then
    nautilus ~/Empire/versions &
elif command -v dolphin &> /dev/null; then
    dolphin ~/Empire/versions &
elif command -v thunar &> /dev/null; then
    thunar ~/Empire/versions &
else
    xdg-open ~/Empire/versions &
fi
