#!/bin/bash
cd ~/Empire
VERSION=$(cat VERSION 2>/dev/null || echo "unknown")
echo "🏰 Empire v${VERSION}"
echo ""
echo "Recent versions:"
ls -1td versions/v* 2>/dev/null | head -5 | while read dir; do
    echo "  📦 $(basename $dir)"
done
