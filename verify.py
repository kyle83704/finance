#!/usr/bin/env python
"""Verification script - Confirms all components are working."""

import sys
import os

# Fix Windows encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_python_version():
    """Check Python version."""
    version = sys.version_info
    print(f"[OK] Python {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("[FAIL] Python 3.9+ required")
        return False
    return True

def check_imports():
    """Check all required imports."""
    modules = {
        'PySimpleGUI': 'GUI framework',
        'pandas': 'Data analysis',
        'numpy': 'Numerical computing',
        'scipy': 'Scientific computing',
        'matplotlib': 'Charting',
        'openpyxl': 'Excel support',
        'yaml': 'YAML serialization',
    }
    
    print("\nChecking imports:")
    all_good = True
    for module, description in modules.items():
        try:
            __import__(module)
            print(f"  [OK] {module:20} - {description}")
        except ImportError:
            print(f"  [FAIL] {module:20} - {description} (MISSING)")
            all_good = False
    
    return all_good

def check_project_modules():
    """Check project modules."""
    print("\nChecking project modules:")
    modules = [
        'src.constants',
        'src.models',
        'src.rules',
        'src.tax_calculator',
        'src.simulator',
        'src.optimizer',
        'src.gui',
    ]
    
    all_good = True
    for module in modules:
        try:
            __import__(module)
            print(f"  [OK] {module}")
        except ImportError as e:
            print(f"  [FAIL] {module} - {str(e)}")
            all_good = False
    
    return all_good

def check_tests():
    """Run basic unit tests."""
    print("\nRunning unit tests:")
    import unittest
    
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print(f"  [OK] All {result.testsRun} tests passed")
        return True
    else:
        print(f"  [FAIL] {len(result.failures)} failures, {len(result.errors)} errors")
        return False

def check_example():
    """Verify example can be imported."""
    print("\nChecking example analysis:")
    try:
        # Just check it imports without errors
        with open('example_analysis.py', 'r') as f:
            code = f.read()
        compile(code, 'example_analysis.py', 'exec')
        print("  [OK] example_analysis.py - Ready to run")
        return True
    except Exception as e:
        print(f"  [FAIL] example_analysis.py - {str(e)}")
        return False

def check_files():
    """Check all essential files exist."""
    print("\nChecking essential files:")
    files = [
        ('src/constants.py', 'Constants'),
        ('src/models.py', 'Data models'),
        ('src/tax_calculator.py', 'Tax engine'),
        ('src/simulator.py', 'Simulator'),
        ('src/optimizer.py', 'Optimizer'),
        ('src/gui.py', 'GUI interface'),
        ('tests/test_tax_calculator.py', 'Tax tests'),
        ('tests/test_simulator.py', 'Simulator tests'),
        ('main.py', 'GUI entry point'),
        ('example_analysis.py', 'Example'),
        ('requirements.txt', 'Dependencies'),
        ('README.md', 'README'),
        ('QUICKSTART.md', 'Quick start'),
        ('BUILD_SUMMARY.md', 'Build summary'),
        ('docs/TECHNICAL.md', 'Technical docs'),
    ]
    
    all_exist = True
    for filepath, description in files:
        if os.path.exists(filepath):
            print(f"  [OK] {filepath:40} - {description}")
        else:
            print(f"  [FAIL] {filepath:40} - {description} (MISSING)")
            all_exist = False
    
    return all_exist

def main():
    """Run all verification checks."""
    print("=" * 70)
    print("ROTH CONVERSION SIMULATOR - VERIFICATION")
    print("=" * 70)
    
    checks = [
        ("Python Version", check_python_version),
        ("Project Files", check_files),
        ("Dependencies", check_imports),
        ("Project Modules", check_project_modules),
        ("Unit Tests", check_tests),
        ("Example Script", check_example),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[FAIL] {name} - Error: {str(e)}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status:8} - {name}")
    
    print("=" * 70)
    
    if passed == total:
        print(f"\nALL CHECKS PASSED ({passed}/{total})")
        print("\nYou're ready to go! Try:")
        print("  python example_analysis.py    # Run example")
        print("  python main.py                 # Run GUI")
        return 0
    else:
        print(f"\nSOME CHECKS FAILED ({passed}/{total})")
        print("\nFix the issues above and try again.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
