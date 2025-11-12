#!/bin/bash
# Uruchamia wszystkie testy z poprawnym kodowaniem UTF-8

echo ""
echo "################################################################################"
echo "# URUCHAMIAM WSZYSTKIE TESTY"
echo "################################################################################"
echo ""

export PYTHONIOENCODING=utf-8
TEST_FAILED=0

echo "Uruchamiam test_strategy.py..."
python test_strategy.py
if [ $? -ne 0 ]; then
    echo "[FAILED] test_strategy.py"
    TEST_FAILED=1
else
    echo "[PASSED] test_strategy.py"
fi

echo ""
echo "Uruchamiam test_support_strategy.py..."
python test_support_strategy.py
if [ $? -ne 0 ]; then
    echo "[FAILED] test_support_strategy.py"
    TEST_FAILED=1
else
    echo "[PASSED] test_support_strategy.py"
fi

echo ""
echo "Uruchamiam impulse_detector.py --test..."
python ../impulse_detector.py --test
if [ $? -ne 0 ]; then
    echo "[FAILED] impulse_detector.py --test"
    TEST_FAILED=1
else
    echo "[PASSED] impulse_detector.py --test"
fi

echo ""
echo "################################################################################"
if [ $TEST_FAILED -eq 1 ]; then
    echo "# NIEKTORE TESTY FAILED"
    echo "################################################################################"
    exit 1
else
    echo "# WSZYSTKIE TESTY PASSED"
    echo "################################################################################"
    exit 0
fi
