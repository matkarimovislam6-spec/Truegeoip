import sys
sys.path.insert(0, '/Users/islommatkarimov/Downloads/go')

try:
    print("Testing analytics import...")
    import analytics
    print("✓ Analytics imported successfully")
    
    print("\nTesting get_tier_limits...")
    limits = analytics.get_tier_limits("free")
    print(f"✓ get_tier_limits works: {limits}")
    
    print("\nTesting get_user_projects...")
    projects = analytics.get_user_projects(1)
    print(f"✓ get_user_projects works: {projects}")
    
    print("\nTesting licenses import...")
    import licenses
    print("✓ Licenses imported successfully")
    
    print("\nTesting get_user_licenses...")
    user_licenses = licenses.get_user_licenses(1)
    print(f"✓ get_user_licenses works: {user_licenses}")
   
    print("\n✅ All tests passed")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
