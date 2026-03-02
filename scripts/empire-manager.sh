#!/bin/bash
echo "🏰 EMPIRE MANAGER"
echo "================"
echo ""
echo "Memory: $(free -h | awk '/^Mem:/{print $3 "/" $2}')"
echo "Disk:   $(df -h / | awk 'NR==2{print $3 "/" $2}')"
echo ""
echo "Running services:"
ss -tlnp 2>/dev/null | grep -E "300[0-9]|800[0-9]" | while read line; do
  PORT=$(echo $line | grep -oE ":[0-9]+" | head -1 | tr -d ':')
  case $PORT in
    3000) echo "  ✓ Control Center (3000)" ;;
    3001) echo "  ✓ WorkroomForge (3001)" ;;
    3004) echo "  ✓ Inventory (3004)" ;;
    3005) echo "  ✓ Finance (3005)" ;;
    3006) echo "  ✓ Creations (3006)" ;;
    3007) echo "  ✓ CRM (3007)" ;;
    3009) echo "  ✓ MAX AI (3009)" ;;
    8000) echo "  ✓ Backend API (8000)" ;;
  esac
done
echo ""
echo "Commands:"
echo "  stop  - Stop all services"
echo "  start - Start all services"
