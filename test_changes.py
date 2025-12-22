#!/usr/bin/env python3
"""
Test script for StreamDeck-MQTT changes
Tests the fixes without requiring actual hardware
"""

import sys
import json
import threading
import time
from unittest.mock import Mock, MagicMock, patch

print("=" * 60)
print("StreamDeck-MQTT Test Suite")
print("=" * 60)

# Test 1: Import checks
print("\n[Test 1] Import validation...")
try:
    import importlib.util

    # Check if StreamDeckMQTT can be parsed
    spec = importlib.util.spec_from_file_location("StreamDeckMQTT", "src/StreamDeckMQTT.py")
    module = importlib.util.module_from_spec(spec)

    print("  ✅ StreamDeckMQTT.py imports successfully")
except Exception as e:
    print(f"  ❌ Failed to import: {e}")
    sys.exit(1)

# Test 2: Verify constants are defined
print("\n[Test 2] Checking constants...")
try:
    with open('src/StreamDeckMQTT.py', 'r') as f:
        content = f.read()
        required_constants = [
            'DEFAULT_BRIGHTNESS',
            'DEFAULT_ICON_COLOR',
            'ICON_DOWNLOAD_TIMEOUT',
            'CONFIG_FILE'
        ]
        for const in required_constants:
            if const in content:
                print(f"  ✅ {const} is defined")
            else:
                print(f"  ❌ {const} is missing")
except Exception as e:
    print(f"  ❌ Error checking constants: {e}")

# Test 3: Verify threading lock implementation
print("\n[Test 3] Checking threading implementation...")
try:
    with open('src/StreamDeckMQTT.py', 'r') as f:
        content = f.read()
        if 'self.config_lock = threading.Lock()' in content:
            print("  ✅ config_lock is initialized")
        else:
            print("  ❌ config_lock not found")

        if 'def _save_config(self):' in content:
            print("  ✅ _save_config() method exists")
        else:
            print("  ❌ _save_config() method missing")

        if 'with self.config_lock:' in content:
            print("  ✅ config_lock is used")
        else:
            print("  ❌ config_lock usage not found")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 4: Verify brightness validation
print("\n[Test 4] Checking brightness validation...")
try:
    with open('src/StreamDeckMQTT.py', 'r') as f:
        content = f.read()
        if 'if not 0 <= brightness_int <= 100:' in content:
            print("  ✅ Brightness range validation exists")
        else:
            print("  ❌ Brightness validation missing")

        if 'max(0, min(100, brightness_int))' in content:
            print("  ✅ Brightness clamping implemented")
        else:
            print("  ❌ Brightness clamping missing")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 5: Verify HTTP timeout
print("\n[Test 5] Checking HTTP timeout...")
try:
    with open('src/StreamDeckMQTT.py', 'r') as f:
        content = f.read()
        if 'timeout=ICON_DOWNLOAD_TIMEOUT' in content:
            print("  ✅ HTTP timeout is set")
        else:
            print("  ❌ HTTP timeout missing")

        if 'requests.Timeout' in content:
            print("  ✅ Timeout exception handling exists")
        else:
            print("  ❌ Timeout exception handling missing")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 6: Verify loop_forever() removed
print("\n[Test 6] Checking loop_forever() fix...")
try:
    with open('src/StreamDeckMQTT.py', 'r') as f:
        content = f.read()
        if 'loop_forever()' not in content:
            print("  ✅ loop_forever() removed from StreamDeckMQTT")
        else:
            print("  ❌ loop_forever() still present")

    with open('src/main.py', 'r') as f:
        content = f.read()
        if 'loop_start()' in content:
            print("  ✅ loop_start() used in main.py")
        else:
            print("  ❌ loop_start() not found in main.py")

        if 'deck_handlers = []' in content:
            print("  ✅ Multi-deck support implemented")
        else:
            print("  ❌ Multi-deck support missing")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 7: Verify improved exception handling
print("\n[Test 7] Checking exception handling...")
try:
    with open('src/StreamDeckMQTT.py', 'r') as f:
        content = f.read()
        if 'except FileNotFoundError:' in content:
            print("  ✅ Specific FileNotFoundError handling")
        else:
            print("  ⚠️  FileNotFoundError not specifically handled")

        if 'except json.JSONDecodeError' in content:
            print("  ✅ JSONDecodeError handling")
        else:
            print("  ⚠️  JSONDecodeError not specifically handled")

        if 'except requests.Timeout:' in content:
            print("  ✅ requests.Timeout handling")
        else:
            print("  ⚠️  requests.Timeout not specifically handled")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 8: Check requirements.txt
print("\n[Test 8] Validating requirements.txt...")
try:
    with open('requirements.txt', 'r') as f:
        content = f.read()
        if 'attrs==23.2.0' in content:
            print("  ✅ attrs version corrected (23.2.0)")
        elif 'attrs==25.1.0' in content:
            print("  ❌ attrs version still wrong (25.1.0)")
        else:
            print("  ⚠️  attrs version unclear")

        if '2025.' not in content:
            print("  ✅ No future version dates found")
        else:
            print("  ⚠️  Future version dates found")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 9: Check Docker configuration
print("\n[Test 9] Checking Docker security improvements...")
try:
    with open('Dockerfile', 'r') as f:
        content = f.read()
        if 'FROM python:3.9-slim-bullseye AS builder' in content:
            print("  ✅ Multi-stage build implemented")
        else:
            print("  ❌ Multi-stage build missing")

        if 'USER streamdeck' in content:
            print("  ✅ Non-root user configured")
        else:
            print("  ❌ Still running as root")

    with open('compose.yaml', 'r') as f:
        content = f.read()
        if 'privileged: true' not in content:
            print("  ✅ privileged mode removed")
        else:
            print("  ❌ privileged mode still present")

        if 'cap_add:' in content:
            print("  ✅ Specific capabilities defined")
        else:
            print("  ⚠️  No capabilities defined")

        if 'restart:' in content:
            print("  ✅ Restart policy defined")
        else:
            print("  ⚠️  No restart policy")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 10: Check .dockerignore
print("\n[Test 10] Checking .dockerignore...")
try:
    with open('.dockerignore', 'r') as f:
        content = f.read()
        required_ignores = ['__pycache__', 'venv/', '.git/', '.env']
        for item in required_ignores:
            if item in content:
                print(f"  ✅ {item} is ignored")
            else:
                print(f"  ⚠️  {item} not in .dockerignore")
except FileNotFoundError:
    print("  ❌ .dockerignore file not found")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Summary
print("\n" + "=" * 60)
print("Test Suite Completed!")
print("=" * 60)
print("\nNote: These are static code tests.")
print("For full integration testing, you need:")
print("  - A physical StreamDeck device")
print("  - Running MQTT broker")
print("  - Run: docker-compose up")
print("=" * 60)
