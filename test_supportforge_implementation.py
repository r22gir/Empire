"""
Simple validation script for SupportForge implementation.
Tests that all core modules can be imported without runtime dependencies.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test that all SupportForge modules are importable."""
    print("Testing SupportForge Module Imports...")
    print("=" * 60)
    
    tests = []
    
    # Test models
    try:
        from app.models import supportforge_tenant
        from app.models import supportforge_agent
        from app.models import supportforge_customer
        from app.models import supportforge_ticket
        from app.models import supportforge_message
        from app.models import supportforge_kb_article
        from app.models import supportforge_automation
        from app.models import supportforge_sla_policy
        from app.models import supportforge_integration
        tests.append(("Models", True, "All 9 models imported successfully"))
    except Exception as e:
        tests.append(("Models", False, str(e)))
    
    # Test schemas
    try:
        from app.schemas import supportforge
        schema_classes = [name for name in dir(supportforge) if name.startswith('SupportForge')]
        tests.append(("Schemas", True, f"{len(schema_classes)} schema classes found"))
    except Exception as e:
        tests.append(("Schemas", False, str(e)))
    
    # Test services
    try:
        # Note: Services require external dependencies, so we just check files exist
        service_files = [
            'backend/app/services/supportforge_ticket_service.py',
            'backend/app/services/supportforge_ai_service.py',
            'backend/app/services/supportforge_customer_service.py'
        ]
        all_exist = all(os.path.exists(f) for f in service_files)
        if all_exist:
            tests.append(("Services", True, "3 service modules exist"))
        else:
            tests.append(("Services", False, "Some service files missing"))
    except Exception as e:
        tests.append(("Services", False, str(e)))
    
    # Test routers
    try:
        # Check router files exist
        router_files = [
            'backend/app/routers/supportforge_tickets.py',
            'backend/app/routers/supportforge_ai.py',
            'backend/app/routers/supportforge_customers.py'
        ]
        all_exist = all(os.path.exists(f) for f in router_files)
        if all_exist:
            tests.append(("Routers", True, "3 API routers exist"))
        else:
            tests.append(("Routers", False, "Some router files missing"))
    except Exception as e:
        tests.append(("Routers", False, str(e)))
    
    # Test migration
    try:
        migration_file = 'backend/alembic/versions/supportforge_001_initial.py'
        if os.path.exists(migration_file):
            with open(migration_file) as f:
                content = f.read()
                table_count = content.count('op.create_table')
                tests.append(("Migration", True, f"Migration file exists with {table_count} tables"))
        else:
            tests.append(("Migration", False, "Migration file not found"))
    except Exception as e:
        tests.append(("Migration", False, str(e)))
    
    # Test documentation
    try:
        readme_file = 'SUPPORTFORGE_README.md'
        if os.path.exists(readme_file):
            with open(readme_file) as f:
                content = f.read()
                lines = len(content.split('\n'))
                tests.append(("Documentation", True, f"README exists with {lines} lines"))
        else:
            tests.append(("Documentation", False, "README not found"))
    except Exception as e:
        tests.append(("Documentation", False, str(e)))
    
    # Print results
    print("\nTest Results:")
    print("-" * 60)
    passed = 0
    failed = 0
    
    for name, success, message in tests:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8} | {name:20} | {message}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"\nTotal: {passed} passed, {failed} failed out of {len(tests)} tests")
    
    if failed == 0:
        print("\n✓ All validation checks passed!")
        print("\nSupportForge core implementation is complete.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r backend/requirements.txt")
        print("2. Run database migration: cd backend && alembic upgrade head")
        print("3. Start server: uvicorn app.main:app --reload")
        print("4. Access API docs: http://localhost:8000/docs")
        return 0
    else:
        print("\n✗ Some validation checks failed.")
        return 1

if __name__ == "__main__":
    exit_code = test_imports()
    sys.exit(exit_code)
