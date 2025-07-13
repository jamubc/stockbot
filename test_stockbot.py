#!/usr/bin/env python3
"""
Simple test script to verify stockbot functionality and security improvements.
"""

import sys
import json
import os

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from utils.security import validate_solana_address, sanitize_input, validate_file_path
        print("✓ Security utils imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import security utils: {e}")
        return False
    
    try:
        import launcher
        print("✓ Launcher module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import launcher: {e}")
        return False
    
    # Note: Don't test solpy import as it requires GUI libraries
    print("✓ Module imports test passed")
    return True

def test_config_validity():
    """Test that config.json is valid."""
    print("\nTesting config validity...")
    
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        # Check required keys
        if 'dev' not in config:
            print("✗ Config missing 'dev' key")
            return False
            
        if 'requirements' not in config:
            print("✗ Config missing 'requirements' key")
            return False
            
        if 'python_requirements' not in config:
            print("✗ Config missing 'python_requirements' key")
            return False
        
        print("✓ Config file is valid JSON with required keys")
        return True
        
    except json.JSONDecodeError as e:
        print(f"✗ Config file has invalid JSON: {e}")
        return False
    except FileNotFoundError:
        print("✗ Config file not found")
        return False

def test_security_functions():
    """Test security utility functions."""
    print("\nTesting security functions...")
    
    from utils.security import validate_solana_address, sanitize_input, validate_file_path
    
    # Test validate_solana_address
    if not validate_solana_address(""):
        print("✓ Empty address rejected")
    else:
        print("✗ Empty address should be rejected")
        return False
    
    if not validate_solana_address("invalid"):
        print("✓ Invalid address rejected")
    else:
        print("✗ Invalid address should be rejected")
        return False
    
    # Test sanitize_input
    sanitized = sanitize_input("  test input  ", 50)
    if sanitized == "test input":
        print("✓ Input sanitization works")
    else:
        print(f"✗ Input sanitization failed: '{sanitized}'")
        return False
    
    # Test validate_file_path
    if not validate_file_path("../etc/passwd"):
        print("✓ Directory traversal attempt blocked")
    else:
        print("✗ Directory traversal should be blocked")
        return False
    
    if validate_file_path("wallet.json"):
        print("✓ Valid file path accepted")
    else:
        print("✗ Valid file path should be accepted")
        return False
    
    print("✓ Security functions test passed")
    return True

def test_file_structure():
    """Test that required files exist."""
    print("\nTesting file structure...")
    
    required_files = [
        'launcher.py',
        'modules/solpy.py',
        'config.json',
        'requirements.txt',
        'README.md',
        '.gitignore',
        'utils/__init__.py',
        'utils/security.py'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            return False
    
    print("✓ File structure test passed")
    return True

def main():
    """Run all tests."""
    print("Running stockbot verification tests...\n")
    
    tests = [
        test_file_structure,
        test_config_validity,
        test_imports,
        test_security_functions,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print(f"Test {test.__name__} failed!")
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("✓ All tests passed! Stockbot is ready to use.")
        return 0
    else:
        print("✗ Some tests failed. Please fix the issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())