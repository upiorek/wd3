import os

base = os.path.join(os.getenv('APPDATA'), 'MetaQuotes', 'Terminal')
dirs = ['A48580ECB7C25E0ED981B61A07DC4A64', 'E014E927B1217F5A561E0813A1C319F3']

print("\nChecking for tester folders:\n")
for d in dirs:
    tester = os.path.join(base, d, 'tester')
    reports = os.path.join(base, d, 'tester', 'reports')
    print(f"{d}:")
    print(f"  tester folder: {os.path.exists(tester)}")
    print(f"  reports folder: {os.path.exists(reports)}")
    
    if os.path.exists(tester):
        contents = os.listdir(tester)
        print(f"  tester contents: {contents[:5]}")
    print()
