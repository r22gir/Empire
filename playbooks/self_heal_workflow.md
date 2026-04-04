# Self-Heal Workflow Playbook
1. Error detected (500 on MAX route, renderer failure, capability mismatch)
2. Validate trigger class (auto-heal allowed vs blocked)
3. Validate file scope (ALLOWED_PATHS only)
4. Pre-patch snapshot of affected files
5. Apply patch function
6. Run canary tests (backend health, MAX chat, capability registry)
7. If canary passes → commit + push
8. If canary fails → git revert + log failure
9. Log incident to self_heal_log table
10. Send Telegram notification with result
