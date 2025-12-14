#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for sequential repeat wildcard feature in character prompts
Tests the ##wildcard*N## syntax
"""

import os
import sys
import tempfile
import shutil

# Add parent directory to path to import wildcard_applier
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wildcard_applier import WildcardApplier

def setup_test_wildcards():
    """Create temporary wildcard folder and test files"""
    temp_dir = tempfile.mkdtemp(prefix="test_wildcards_")

    # Create a test wildcard file
    test_file = os.path.join(temp_dir, "1_chara.txt")
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("Character A Information\n")
        f.write("Character B Information\n")
        f.write("Character C Information\n")

    return temp_dir

def test_sequential_repeat_with_snapshot():
    """Test sequential repeat wildcard with snapshot (character prompt scenario)"""
    print("=" * 60)
    print("Testing Sequential Repeat Wildcard with Snapshot")
    print("=" * 60)

    # Setup
    wildcard_folder = setup_test_wildcards()
    applier = WildcardApplier(wildcard_folder)
    applier.load_wildcards()

    # Test pattern: ##1_chara*2## means repeat each character 2 times
    test_prompt = "1girl, ##1_chara*2##, solo"

    print(f"\nTest Prompt: {test_prompt}")
    print(f"Expected: Repeat each character 2 times before advancing\n")

    results = []

    # Simulate 6 generations (3 characters × 2 repeats each)
    for i in range(6):
        # Create snapshot (like gui.py does)
        applier.create_index_snapshot()

        # Apply wildcards with snapshot
        result = applier.apply_wildcards_with_snapshot(test_prompt)
        results.append(result)

        print(f"Generation {i+1}: {result}")

        # Advance indices (like gui.py does after processing all characters)
        applier.advance_loopcard_indices()

    # Verify results
    print("\n" + "=" * 60)
    print("Verification:")
    print("=" * 60)

    expected_sequence = [
        "1girl, Character A Information, solo",  # Character A, 1st time
        "1girl, Character A Information, solo",  # Character A, 2nd time
        "1girl, Character B Information, solo",  # Character B, 1st time
        "1girl, Character B Information, solo",  # Character B, 2nd time
        "1girl, Character C Information, solo",  # Character C, 1st time
        "1girl, Character C Information, solo",  # Character C, 2nd time
    ]

    all_passed = True
    for i, (result, expected) in enumerate(zip(results, expected_sequence)):
        match = result == expected
        status = "✓ PASS" if match else "✗ FAIL"
        print(f"Generation {i+1}: {status}")
        if not match:
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")
            all_passed = False

    # Cleanup
    shutil.rmtree(wildcard_folder)

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED!")
    print("=" * 60)

    return all_passed

def test_sequential_without_repeat():
    """Test regular sequential wildcard without repeat (baseline)"""
    print("\n\n" + "=" * 60)
    print("Testing Regular Sequential Wildcard (Baseline)")
    print("=" * 60)

    # Setup
    wildcard_folder = setup_test_wildcards()
    applier = WildcardApplier(wildcard_folder)
    applier.load_wildcards()

    # Test pattern: ##1_chara## means advance to next character each time
    test_prompt = "1girl, ##1_chara##, solo"

    print(f"\nTest Prompt: {test_prompt}")
    print(f"Expected: Advance to next character each time\n")

    results = []

    # Simulate 3 generations
    for i in range(3):
        applier.create_index_snapshot()
        result = applier.apply_wildcards_with_snapshot(test_prompt)
        results.append(result)
        print(f"Generation {i+1}: {result}")
        applier.advance_loopcard_indices()

    # Verify results
    print("\n" + "=" * 60)
    print("Verification:")
    print("=" * 60)

    expected_sequence = [
        "1girl, Character A Information, solo",
        "1girl, Character B Information, solo",
        "1girl, Character C Information, solo",
    ]

    all_passed = True
    for i, (result, expected) in enumerate(zip(results, expected_sequence)):
        match = result == expected
        status = "✓ PASS" if match else "✗ FAIL"
        print(f"Generation {i+1}: {status}")
        if not match:
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")
            all_passed = False

    # Cleanup
    shutil.rmtree(wildcard_folder)

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED!")
    print("=" * 60)

    return all_passed

def test_sequential_repeat_different_counts():
    """Test sequential repeat wildcard with different repeat counts"""
    print("\n\n" + "=" * 60)
    print("Testing Sequential Repeat with Different Counts")
    print("=" * 60)

    # Setup
    wildcard_folder = setup_test_wildcards()
    applier = WildcardApplier(wildcard_folder)
    applier.load_wildcards()

    # Test pattern: ##1_chara*3## means repeat each character 3 times
    test_prompt = "1girl, ##1_chara*3##, solo"

    print(f"\nTest Prompt: {test_prompt}")
    print(f"Expected: Repeat each character 3 times before advancing\n")

    results = []

    # Simulate 9 generations (3 characters × 3 repeats each)
    for i in range(9):
        applier.create_index_snapshot()
        result = applier.apply_wildcards_with_snapshot(test_prompt)
        results.append(result)
        print(f"Generation {i+1}: {result}")
        applier.advance_loopcard_indices()

    # Verify results
    print("\n" + "=" * 60)
    print("Verification:")
    print("=" * 60)

    expected_sequence = [
        "1girl, Character A Information, solo",  # A, 1st
        "1girl, Character A Information, solo",  # A, 2nd
        "1girl, Character A Information, solo",  # A, 3rd
        "1girl, Character B Information, solo",  # B, 1st
        "1girl, Character B Information, solo",  # B, 2nd
        "1girl, Character B Information, solo",  # B, 3rd
        "1girl, Character C Information, solo",  # C, 1st
        "1girl, Character C Information, solo",  # C, 2nd
        "1girl, Character C Information, solo",  # C, 3rd
    ]

    all_passed = True
    for i, (result, expected) in enumerate(zip(results, expected_sequence)):
        match = result == expected
        status = "✓ PASS" if match else "✗ FAIL"
        print(f"Generation {i+1}: {status}")
        if not match:
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")
            all_passed = False

    # Cleanup
    shutil.rmtree(wildcard_folder)

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED!")
    print("=" * 60)

    return all_passed

if __name__ == "__main__":
    print("Sequential Repeat Wildcard Feature Test")
    print("Testing ##wildcard*N## syntax for character prompts\n")

    # Run all tests
    test1_passed = test_sequential_without_repeat()
    test2_passed = test_sequential_repeat_with_snapshot()
    test3_passed = test_sequential_repeat_different_counts()

    # Final summary
    print("\n\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Test 1 (Regular Sequential):     {'✓ PASS' if test1_passed else '✗ FAIL'}")
    print(f"Test 2 (Repeat x2):              {'✓ PASS' if test2_passed else '✗ FAIL'}")
    print(f"Test 3 (Repeat x3):              {'✓ PASS' if test3_passed else '✗ FAIL'}")

    if test1_passed and test2_passed and test3_passed:
        print("\n✓✓✓ ALL TESTS PASSED! ✓✓✓")
        sys.exit(0)
    else:
        print("\n✗✗✗ SOME TESTS FAILED! ✗✗✗")
        sys.exit(1)
