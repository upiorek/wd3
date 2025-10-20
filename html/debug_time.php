<?php

// Debug the actual time difference calculation with your exact data
function debugTimeDifference() {
    $systemTime = '2025-10-20 10:04:53';
    $accountTime = '2025.10.20 10:04:40';
    
    echo "=== DEBUGGING TIME DIFFERENCE ===\n";
    echo "System time: $systemTime\n";
    echo "Account time: $accountTime\n\n";
    
    // Test the current regex method
    $accountTimeFormatted = preg_replace('/^(\d{4})\.(\d{2})\.(\d{2})/', '$1-$2-$3', $accountTime);
    echo "Formatted account time: $accountTimeFormatted\n";
    
    // Check if both times can be parsed
    $systemTimestamp = strtotime($systemTime);
    $accountTimestamp = strtotime($accountTimeFormatted);
    
    echo "System timestamp: $systemTimestamp (" . date('Y-m-d H:i:s', $systemTimestamp) . ")\n";
    echo "Account timestamp: $accountTimestamp (" . date('Y-m-d H:i:s', $accountTimestamp) . ")\n";
    
    if ($systemTimestamp === false) {
        echo "ERROR: System time could not be parsed!\n";
    }
    if ($accountTimestamp === false) {
        echo "ERROR: Account time could not be parsed!\n";
    }
    
    if ($systemTimestamp && $accountTimestamp) {
        $timeDiff = $systemTimestamp - $accountTimestamp;
        echo "Time difference: $timeDiff seconds\n";
        echo "Expected: 13 seconds (53 - 40 = 13)\n";
        echo "Result: " . ($timeDiff == 13 ? "CORRECT" : "INCORRECT - Something is wrong!") . "\n";
    }
    
    echo "\n=== TESTING DIFFERENT APPROACHES ===\n";
    
    // Method 1: Simple string replacement of first 3 dots
    $parts = explode(' ', $accountTime);
    $datePart = str_replace('.', '-', $parts[0]);
    $timePart = isset($parts[1]) ? $parts[1] : '';
    $method1 = $datePart . ' ' . $timePart;
    echo "Method 1 (split and replace): $method1\n";
    $method1Timestamp = strtotime($method1);
    echo "Method 1 timestamp: $method1Timestamp (" . date('Y-m-d H:i:s', $method1Timestamp) . ")\n";
    if ($method1Timestamp) {
        $method1Diff = $systemTimestamp - $method1Timestamp;
        echo "Method 1 difference: $method1Diff seconds\n";
    }
    
    // Method 2: More specific regex
    $method2 = preg_replace('/^(\d{4})\.(\d{2})\.(\d{2})(\s+.*)$/', '$1-$2-$3$4', $accountTime);
    echo "Method 2 (specific regex): $method2\n";
    $method2Timestamp = strtotime($method2);
    echo "Method 2 timestamp: $method2Timestamp (" . date('Y-m-d H:i:s', $method2Timestamp) . ")\n";
    if ($method2Timestamp) {
        $method2Diff = $systemTimestamp - $method2Timestamp;
        echo "Method 2 difference: $method2Diff seconds\n";
    }
}

debugTimeDifference();

?>