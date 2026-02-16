import sys
import os

# Test basic imports
try:
    print("Testing MarketForge Backend Setup...")
    print("-" * 50)
    
    # Add the backend directory to the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Test imports
    print("✓ Testing database module...")
    from app import database
    
    print("✓ Testing models module...")
    from app import models
    
    print("✓ Testing schemas module...")
    from app import schemas
    
    print("✓ Testing auth module...")
    from app import auth
    
    print("✓ Testing main app...")
    from app import main
    
    print("-" * 50)
    print("✅ All imports successful!")
    print("\nNext steps:")
    print("1. Set up your .env file (copy from .env.example)")
    print("2. Run: uvicorn app.main:app --reload")
    print("3. Visit http://localhost:8000/docs")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
