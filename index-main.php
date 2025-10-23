<?php
// Load configuration
require_once __DIR__ . '/config.php';

// Set content type
header('Content-Type: text/html; charset=utf-8');

// Set timezone from config
date_default_timezone_set(APP_TIMEZONE);

// Get current timestamp
$timestamp = date('Y-m-d H:i:s');

/**
 * Read orders from a file and return as array of rows
 * @param string $file_path Path to the file to read
 * @return array Array of order rows
 */
function getOrdersFromFile($file_path) {
    $orders = array();
    
    if (file_exists($file_path)) {
        $content = file_get_contents($file_path);
        $lines = explode("\n", trim($content));
        
        foreach ($lines as $line) {
            $line = trim($line);
            if (!empty($line)) {
                $orders[] = $line;
            }
        }
    }
    
    return $orders;
}

/**
 * Read orders from orders.txt file and return as array of rows
 * @return array Array of order rows
 */
function getOrdersList() {
    return getOrdersFromFile(ORDERS_FILE);
}

/**
 * Read approved orders from approved.txt file and return as array of rows
 * @return array Array of approved order rows
 */
function getApprovedOrdersList() {
    return getOrdersFromFile(APPROVED_FILE);
}

/**
 * Read modified orders from modified.txt file and return as array of rows
 * @return array Array of modified order rows
 */
function getModifiedOrdersList() {
    return getOrdersFromFile(MODIFIED_FILE);
}

/**
 * Read to be modified orders from to_be_modified.txt file and return as array of rows
 * @return array Array of to be modified order rows
 */
function getToBeModifiedOrdersList() {
    return getOrdersFromFile(TO_BE_MODIFIED_FILE);
}

/**
 * Parse orders log file and return structured data
 * @return array Array of order log entries with parsed data
 */
function getOrdersLogData() {
    $ordersLog = array();
    
    if (file_exists(ORDERS_LOG_FILE)) {
        $content = file_get_contents(ORDERS_LOG_FILE);
        $lines = explode("\n", trim($content));
        
        foreach ($lines as $line) {
            $line = trim($line);
            
            // Skip header lines and empty lines
            if (empty($line) || 
                strpos($line, '=== ORDERS LOG') === 0 || 
                strpos($line, '=== END') === 0 || 
                strpos($line, 'Total Orders:') === 0 ||
                strpos($line, 'Ticket | Type') === 0 ||
                strpos($line, '-------|------') === 0 ||
                strpos($line, 'No open orders') === 0) {
                continue;
            }
            
            // Parse data line (pipe-separated values)
            if (strpos($line, '|') !== false) {
                $parts = array_map('trim', explode('|', $line));
                
                // Handle different formats - current format has 5 parts, expected format has 8+ parts
                if (count($parts) >= 5) {
                    if (count($parts) >= 8) {
                        // Full format: Ticket | Type | Symbol | Lots | OpenPrice | StopLoss | TakeProfit | Profit
                        $ordersLog[] = array(
                            'ticket' => $parts[0],
                            'type' => $parts[1],
                            'symbol' => $parts[2],
                            'lots' => $parts[3],
                            'openPrice' => $parts[4],
                            'stopLoss' => $parts[5],
                            'takeProfit' => $parts[6],
                            'profit' => $parts[7]
                        );
                    } else {
                        // Simplified format: Ticket | Type | Symbol | Lots | Profit
                        $ordersLog[] = array(
                            'ticket' => $parts[0],
                            'type' => $parts[1],
                            'symbol' => $parts[2],
                            'lots' => $parts[3],
                            'openPrice' => 'N/A',
                            'stopLoss' => 'N/A',
                            'takeProfit' => 'N/A',
                            'profit' => $parts[4]
                        );
                    }
                }
            }
        }
    }
    
    return $ordersLog;
}

/**
 * Get precision for price formatting based on symbol
 * @param string $symbol The trading symbol
 * @return int Number of decimal places
 */
function getPricePrecision($symbol) {
    // Define precision rules for different symbols
    $precisionMap = array(
        'US100.f' => 2,  // 2 digits for US100.f
        'EURUSD' => 5,   // 5 digits for EURUSD
    );
    
    // Return specific precision if symbol is in map, otherwise default to 2
    return isset($precisionMap[$symbol]) ? $precisionMap[$symbol] : 2;
}

/**
 * Format price value with symbol-specific precision
 * @param float|string $value The value to format
 * @param string $symbol The trading symbol (optional, defaults to 2 decimal places)
 * @return string Formatted price
 */
function formatPrice($value, $symbol = '') {
    if ($value === 'N/A' || $value === '' || $value === null) {
        return 'N/A';
    }
    
    // Handle zero values
    if ($value === '0' || $value === 0 || floatval($value) === 0.0) {
        return '0';
    }
    
    $precision = empty($symbol) ? 2 : getPricePrecision($symbol);
    return number_format(floatval($value), $precision);
}

/**
 * Check if order contains specific flag (p or r)
 * @param string $order The order string
 * @param string $flag The flag to check for ('p' or 'r')
 * @return bool
 */
function orderHasFlag($order, $flag) {
    return in_array($flag, explode(' ', trim($order)));
}

/**
 * Check if order has both 'p' and 'r' flags set
 * @param string $order The order string
 * @return bool
 */
function orderHasBothFlags($order) {
    return orderHasFlag($order, 'p') && orderHasFlag($order, 'r');
}

/**
 * Read password from password file
 * @param string $action The action ('p' or 'r')
 * @return string|null The password or null if file not found
 */
function getPasswordForAction($action) {
    $passwordFile = '';
    if ($action === 'p') {
        $passwordFile = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/pass_p.txt';
    } elseif ($action === 'r') {
        $passwordFile = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/pass_r.txt';
    } else {
        return null;
    }
    
    if (file_exists($passwordFile)) {
        return trim(file_get_contents($passwordFile));
    }
    
    return null;
}

/**
 * Validate password for action
 * @param string $action The action ('p' or 'r')
 * @param string $password The provided password
 * @return bool True if password is correct
 */
function validatePassword($action, $password) {
    $correctPassword = getPasswordForAction($action);
    return $correctPassword !== null && $password === $correctPassword;
}

/**
 * Move an order from orders.txt to approved.txt
 * @param string $order The order to move
 * @return bool Success status
 */
function moveOrderToApproved($order) {
    // Remove the 'p' and 'r' flags from the order before moving to approved
    $orderParts = explode(' ', trim($order));
    $cleanedOrder = array();
    foreach ($orderParts as $part) {
        if ($part !== 'p' && $part !== 'r') {
            $cleanedOrder[] = $part;
        }
    }
    $cleanOrderString = implode(' ', $cleanedOrder);
    
    // Ensure proper newline handling - check if file exists and ends with newline
    $needsNewlineBefore = false;
    if (file_exists(APPROVED_FILE)) {
        $existingContent = file_get_contents(APPROVED_FILE);
        if (!empty($existingContent) && substr($existingContent, -1) !== "\n") {
            $needsNewlineBefore = true;
        }
    }
    
    // Prepare the content to append
    $contentToAppend = ($needsNewlineBefore ? "\n" : '') . $cleanOrderString . "\n";
    
    // Append to approved.txt
    $result = file_put_contents(APPROVED_FILE, $contentToAppend, FILE_APPEND | LOCK_EX);
    return $result !== false;
}

/**
 * Generate action buttons HTML for an order
 * @param int $rowNumber Row number (1-based)
 * @param string $order Order string
 * @param bool $isApproved Whether this is an approved order
 * @return string HTML for action buttons
 */
function generateActionButtons($rowNumber, $order, $isApproved = false) {
    if ($isApproved) {
        // For approved orders, only show a remove button
        return '<button onclick="handleRemoveApprovedAction(' . $rowNumber . ')" class="action-button btn-cancel">Remove</button>';
    } else {
        // For regular orders, show P, R, and Cancel buttons
        $hasP = orderHasFlag($order, 'p');
        $hasR = orderHasFlag($order, 'r');
        
        $pButtonClass = $hasP ? 'btn-p-active' : 'btn-p-inactive';
        $rButtonClass = $hasR ? 'btn-r-active' : 'btn-r-inactive';
        
        return '<button onclick="handlePAction(' . $rowNumber . ')" class="action-button ' . $pButtonClass . '">P</button>' .
               '<button onclick="handleRAction(' . $rowNumber . ')" class="action-button ' . $rButtonClass . '">R</button>' .
               '<button onclick="handleCancelAction(' . $rowNumber . ')" class="action-button btn-cancel">Cancel</button>';
    }
}

/**
 * Generate HTML table for orders log
 * @param array $ordersLog Array of parsed order log entries
 * @return string HTML table
 */
function generateOrdersLogTable($ordersLog) {
    if (empty($ordersLog)) {
        return '<p class="error-message">No orders log found or orders log file not found.</p>';
    }
    
    // Generate desktop table
    $html = '<table class="table orders-log-table">';
    $html .= '<thead>';
    $html .= '<tr>';
    $html .= '<th>Ticket</th>';
    $html .= '<th>Type</th>';
    $html .= '<th>Symbol</th>';
    $html .= '<th>Lots</th>';
    $html .= '<th>Open Price</th>';
    $html .= '<th>Stop Loss</th>';
    $html .= '<th>Take Profit</th>';
    $html .= '<th>Profit</th>';
    $html .= '</tr>';
    $html .= '</thead>';
    $html .= '<tbody>';
    
    foreach ($ordersLog as $order) {
        $html .= '<tr>';
        $html .= '<td>' . htmlspecialchars($order['ticket']) . '</td>';
        $html .= '<td>' . htmlspecialchars($order['type']) . '</td>';
        $html .= '<td>' . htmlspecialchars($order['symbol']) . '</td>';
        $html .= '<td>' . ($order['lots'] === 'N/A' ? '<span class="na-value">N/A</span>' : number_format(floatval($order['lots']), 2)) . '</td>';
        $html .= '<td>' . ($order['openPrice'] === 'N/A' ? '<span class="na-value">N/A</span>' : formatPrice($order['openPrice'], $order['symbol'])) . '</td>';
        $html .= '<td>' . ($order['stopLoss'] === 'N/A' ? '<span class="na-value">N/A</span>' : formatPrice($order['stopLoss'], $order['symbol'])) . '</td>';
        $html .= '<td>' . ($order['takeProfit'] === 'N/A' ? '<span class="na-value">N/A</span>' : formatPrice($order['takeProfit'], $order['symbol'])) . '</td>';
        $html .= '<td class="' . (floatval($order['profit']) >= 0 ? 'profit-positive' : 'profit-negative') . '">' . number_format(floatval($order['profit']), 2) . '</td>';
        $html .= '</tr>';
    }
    
    $html .= '</tbody>';
    $html .= '</table>';
    
    // Generate mobile card layout
    $html .= '<div class="orders-log-cards">';
    foreach ($ordersLog as $order) {
        $html .= '<div class="order-card">';
        
        // First row: Labels (Ticket, Type, Symbol, Lots)
        $html .= '<div class="card-row labels">';
        $html .= '<div>Ticket</div>';
        $html .= '<div>Type</div>';
        $html .= '<div>Symbol</div>';
        $html .= '<div>Lots</div>';
        $html .= '</div>';
        
        // Second row: Values (Ticket, Type, Symbol, Lots)
        $html .= '<div class="card-row values">';
        $html .= '<div>' . htmlspecialchars($order['ticket']) . '</div>';
        $html .= '<div>' . htmlspecialchars($order['type']) . '</div>';
        $html .= '<div>' . htmlspecialchars($order['symbol']) . '</div>';
        $html .= '<div>' . ($order['lots'] === 'N/A' ? '<span class="na-value">N/A</span>' : number_format(floatval($order['lots']), 2)) . '</div>';
        $html .= '</div>';
        
        // Third row: Labels (Open, SL, TP, Profit)
        $html .= '<div class="card-row labels">';
        $html .= '<div>Open</div>';
        $html .= '<div>SL</div>';
        $html .= '<div>TP</div>';
        $html .= '<div>Profit</div>';
        $html .= '</div>';
        
        // Fourth row: Values (Open, SL, TP, Profit)
        $html .= '<div class="card-row values">';
        $html .= '<div>' . ($order['openPrice'] === 'N/A' ? '<span class="na-value">N/A</span>' : formatPrice($order['openPrice'], $order['symbol'])) . '</div>';
        $html .= '<div>' . ($order['stopLoss'] === 'N/A' ? '<span class="na-value">N/A</span>' : formatPrice($order['stopLoss'], $order['symbol'])) . '</div>';
        $html .= '<div>' . ($order['takeProfit'] === 'N/A' ? '<span class="na-value">N/A</span>' : formatPrice($order['takeProfit'], $order['symbol'])) . '</div>';
        $html .= '<div class="' . (floatval($order['profit']) >= 0 ? 'card-profit-positive' : 'card-profit-negative') . '">' . number_format(floatval($order['profit']), 2) . '</div>';
        $html .= '</div>';
        
        $html .= '</div>'; // End order-card
    }
    $html .= '</div>'; // End orders-log-cards
    
    //global $timestamp;
    //$html .= '<small class="timestamp">Last updated: ' . $timestamp . '</small>';
    
    return $html;
}

/**
 * Generate HTML table for orders
 * @param array $orders Array of order strings
 * @param bool $showActions Whether to show action buttons
 * @param bool $isApproved Whether these are approved orders
 * @return string HTML table
 */
function generateOrdersTable($orders, $showActions = false, $isApproved = false) {
    if (empty($orders)) {
        $message = $showActions ? 'No orders found or orders file not found.' : 'No approved orders found or approved orders file not found.';
        return '<p class="error-message">' . $message . '</p>';
    }
    
    $html = '<table class="table">';
    $html .= '<thead>';
    $html .= '<tr>';
    $html .= '<th>Symbol</th>';
    $html .= '<th>Type</th>';
    $html .= '<th>Lots</th>';
    $html .= '<th>Price</th>';
    $html .= '<th>SL</th>';
    $html .= '<th>TP</th>';
    if ($showActions) {
        $html .= '<th>Actions</th>';
    }
    $html .= '</tr>';
    $html .= '</thead>';
    $html .= '<tbody>';
    
    foreach ($orders as $index => $order) {
        $parts = explode(' ', trim($order));
        $symbol = isset($parts[0]) ? htmlspecialchars($parts[0]) : '';
        $type = isset($parts[1]) ? htmlspecialchars($parts[1]) : '';
        $lots = isset($parts[2]) ? htmlspecialchars($parts[2]) : '';
        $price = isset($parts[3]) ? htmlspecialchars($parts[3]) : '';
        $sl = isset($parts[4]) ? htmlspecialchars($parts[4]) : '';
        $tp = isset($parts[5]) ? htmlspecialchars($parts[5]) : '';
        
        // Get symbol without HTML encoding for precision calculation
        $rawSymbol = isset($parts[0]) ? $parts[0] : '';
        
        $html .= '<tr>';
        $html .= '<td>' . $symbol . '</td>';
        $html .= '<td>' . $type . '</td>';
        $html .= '<td>' . $lots . '</td>';
        $html .= '<td>' . ($price === '0' ? '0' : formatPrice($price, $rawSymbol)) . '</td>';
        $html .= '<td>' . ($sl === '0' ? '0' : formatPrice($sl, $rawSymbol)) . '</td>';
        $html .= '<td>' . ($tp === '0' ? '0' : formatPrice($tp, $rawSymbol)) . '</td>';
        if ($showActions) {
            $html .= '<td>' . generateActionButtons($index + 1, $order, $isApproved) . '</td>';
        }
        $html .= '</tr>';
    }
    
    $html .= '</tbody>';
    $html .= '</table>';
    
    global $timestamp;
    $html .= '<small class="timestamp">Last updated: ' . $timestamp . '</small>';
    
    return $html;
}

/**
 * Generate HTML table for modified orders
 * @param array $modifiedOrders Array of modified order strings
 * @return string HTML table
 */
function generateModifiedOrdersTable($modifiedOrders) {
    if (empty($modifiedOrders)) {
        return '<p class="error-message">No modified orders found or modified orders file not found.</p>';
    }
    
    $html = '<table class="table">';
    $html .= '<thead>';
    $html .= '<tr>';
    $html .= '<th>Ticket</th>';
    $html .= '<th>Stop Loss</th>';
    $html .= '<th>Take Profit</th>';
    $html .= '<th>Actions</th>';
    $html .= '</tr>';
    $html .= '</thead>';
    $html .= '<tbody>';
    
    foreach ($modifiedOrders as $index => $modifiedOrder) {
        $parts = explode(' ', trim($modifiedOrder));
        $ticket = isset($parts[0]) ? htmlspecialchars($parts[0]) : '';
        $stopLoss = isset($parts[1]) ? htmlspecialchars($parts[1]) : '';
        $takeProfit = isset($parts[2]) ? htmlspecialchars($parts[2]) : '';
        
        $html .= '<tr>';
        $html .= '<td>' . $ticket . '</td>';
        $html .= '<td>' . ($stopLoss === '0' ? '<span class="na-value">0</span>' : $stopLoss) . '</td>';
        $html .= '<td>' . ($takeProfit === '0' ? '<span class="na-value">0</span>' : $takeProfit) . '</td>';
        $html .= '<td><button onclick="handleRemoveModifiedAction(' . ($index + 1) . ')" class="action-button btn-cancel">Remove</button></td>';
        $html .= '</tr>';
    }
    
    $html .= '</tbody>';
    $html .= '</table>';
    
    global $timestamp;
    $html .= '<small class="timestamp">Last updated: ' . $timestamp . '</small>';
    
    return $html;
}

/**
 * Generate HTML table for to be modified orders
 * @param array $toBeModifiedOrders Array of to be modified order strings
 * @return string HTML table
 */
function generateToBeModifiedOrdersTable($toBeModifiedOrders) {
    if (empty($toBeModifiedOrders)) {
        return '<p class="error-message">No orders to be modified found or to_be_modified orders file not found.</p>';
    }
    
    $html = '<table class="table">';
    $html .= '<thead>';
    $html .= '<tr>';
    $html .= '<th>Ticket</th>';
    $html .= '<th>Stop Loss</th>';
    $html .= '<th>Take Profit</th>';
    $html .= '<th>Actions</th>';
    $html .= '</tr>';
    $html .= '</thead>';
    $html .= '<tbody>';
    
    foreach ($toBeModifiedOrders as $index => $toBeModifiedOrder) {
        $parts = explode(' ', trim($toBeModifiedOrder));
        $ticket = isset($parts[0]) ? htmlspecialchars($parts[0]) : '';
        $stopLoss = isset($parts[1]) ? htmlspecialchars($parts[1]) : '';
        $takeProfit = isset($parts[2]) ? htmlspecialchars($parts[2]) : '';
        
        // Check for P and R flags
        $hasP = orderHasFlag($toBeModifiedOrder, 'p');
        $hasR = orderHasFlag($toBeModifiedOrder, 'r');
        
        $pButtonClass = $hasP ? 'btn-p-active' : 'btn-p-inactive';
        $rButtonClass = $hasR ? 'btn-r-active' : 'btn-r-inactive';
        
        $html .= '<tr>';
        $html .= '<td>' . $ticket . '</td>';
        $html .= '<td>' . ($stopLoss === '0' ? '<span class="na-value">0</span>' : $stopLoss) . '</td>';
        $html .= '<td>' . ($takeProfit === '0' ? '<span class="na-value">0</span>' : $takeProfit) . '</td>';
        $html .= '<td>';
        $html .= '<button onclick="handlePToBeModifiedAction(' . ($index + 1) . ')" class="action-button ' . $pButtonClass . '">P</button>';
        $html .= '<button onclick="handleRToBeModifiedAction(' . ($index + 1) . ')" class="action-button ' . $rButtonClass . '">R</button>';
        $html .= '<button onclick="handleRemoveToBeModifiedAction(' . ($index + 1) . ')" class="action-button btn-cancel">Remove</button>';
        $html .= '</td>';
        $html .= '</tr>';
    }
    
    $html .= '</tbody>';
    $html .= '</table>';
    
    global $timestamp;
    $html .= '<small class="timestamp">Last updated: ' . $timestamp . '</small>';
    
    return $html;
}

function refreshAccountLog() {
    global $timestamp;
    $output = '';
    
    // Read account log
    if (file_exists(ACCOUNT_LOG_FILE)) {
        $accountContent = file_get_contents(ACCOUNT_LOG_FILE);
        $accountContent = htmlspecialchars($accountContent);
        // replace | with <br/>
        $accountContent = str_replace('| ', '<br/>', $accountContent);
        $output .= $accountContent;
    } else {
        $output .= 'Account log file not found.';
    }
    
    // Add separator and market log
    $marketLogFile = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/market_log.txt';
    if (file_exists($marketLogFile)) {
        $marketContent = file_get_contents($marketLogFile);
        $marketContent = htmlspecialchars($marketContent);
        // replace | with <br/>
        $marketContent = str_replace('| ', '<br/>', $marketContent);
        $output .= '<br/><br/>' . $marketContent;
    } else {
        $output .= '<br/><br/>Market log file not found.';
    }
    
    if (strpos($output, 'not found') !== false && strpos($output, 'not found') === strpos($output, 'Account log file not found.')) {
        echo '<p class="error-message">' . $output . '</p>';
    } else {
        echo '<pre style="margin: 0; white-space: pre-wrap;">' . $output . '</pre>';
    }
    //echo '<small class="timestamp">Last updated: ' . $timestamp . '</small>';
}

/**
 * Extract total net profit from order history log content
 * @param string $content The raw content of the order history log
 * @return string|null The total net profit value or null if not found
 */
function extractTotalNetProfit($content) {
    // Look for "Total net profit:" pattern in the content
    if (preg_match('/Total net profit:\s*([-+]?\d*\.?\d+)/', $content, $matches)) {
        return $matches[1];
    }
    return null;
}

/**
 * Extract total orders count from order history log content
 * @param string $content The raw content of the order history log
 * @return int The total orders count or 0 if not found
 */
function extractTotalOrdersCount($content) {
    // Count the number of order lines (lines that contain ticket numbers and trading data)
    $lines = explode("\n", $content);
    $orderCount = 0;
    
    foreach ($lines as $line) {
        $line = trim($line);
        // Skip empty lines, headers, and summary lines
        if (empty($line) || 
            strpos($line, '=') === 0 || 
            strpos($line, 'Total') === 0 ||
            strpos($line, 'Account') === 0 ||
            strpos($line, 'Date') === 0 ||
            strpos($line, 'Symbol') === 0 ||
            strpos($line, '----') === 0) {
            continue;
        }
        
        // Look for lines that start with a ticket number (numeric)
        if (preg_match('/^\d+\s/', $line)) {
            $orderCount++;
        }
    }
    
    return $orderCount;
}

/**
 * Extract profit value from account log content
 * @param string $content The raw content of the account log
 * @return string|null The profit value or null if not found
 */
function extractAccountProfit($content) {
    // Look for "Profit:" pattern in the content
    if (preg_match('/Profit:\s*([-+]?\d*\.?\d+)/', $content, $matches)) {
        return $matches[1];
    }
    return null;
}

/**
 * Extract orders count from account log content
 * @param string $content The raw content of the account log
 * @return string|null The orders count or null if not found
 */
function extractAccountOrders($content) {
    // Look for "Orders:" pattern in the content
    if (preg_match('/Orders:\s*(\d+)/', $content, $matches)) {
        return $matches[1];
    }
    return null;
}

/**
 * Get profit value from account log
 * @return string|null The profit value or null if not found
 */
function getAccountProfit() {
    if (file_exists(ACCOUNT_LOG_FILE)) {
        $content = file_get_contents(ACCOUNT_LOG_FILE);
        return extractAccountProfit($content);
    }
    return null;
}

/**
 * Get orders count from account log
 * @return string|null The orders count or null if not found
 */
function getAccountOrders() {
    if (file_exists(ACCOUNT_LOG_FILE)) {
        $content = file_get_contents(ACCOUNT_LOG_FILE);
        return extractAccountOrders($content);
    }
    return null;
}

/**
 * Get total net profit value from order history log
 * @return string|null The total net profit value or null if not found
 */
function getTotalNetProfit() {
    if (file_exists(ORDER_HISTORY_LOG_FILE)) {
        $content = file_get_contents(ORDER_HISTORY_LOG_FILE);
        return extractTotalNetProfit($content);
    }
    return null;
}

/**
 * Get total orders count from order history log
 * @return int The total orders count or 0 if not found
 */
function getTotalOrdersCount() {
    if (file_exists(ORDER_HISTORY_LOG_FILE)) {
        $content = file_get_contents(ORDER_HISTORY_LOG_FILE);
        return extractTotalOrdersCount($content);
    }
    return 0;
}

/**
 * Read and display order history log content
 */
function refreshOrderHistoryLog() {
    global $timestamp;
    if (file_exists(ORDER_HISTORY_LOG_FILE)) {
        $content = file_get_contents(ORDER_HISTORY_LOG_FILE);
        $content = htmlspecialchars($content);
        echo '<pre style="margin: 0; white-space: pre-wrap;">' . $content . '</pre>';
        echo '<small class="timestamp">Last updated: ' . $timestamp . '</small>';
    } else {
        echo '<p class="error-message">Order history log file not found.</p>';
    }
}

/**
 * Get list of available log files from both log directories
 * @return array Array of log files with details
 */
function getLogFilesList() {
    $logFiles = array();
    
    $directories = array(
        'MQL4' => LOGS_DIR_MQL4,
        'Main' => LOGS_DIR_MAIN
    );
    
    foreach ($directories as $dirType => $dirPath) {
        if (is_dir($dirPath)) {
            $files = scandir($dirPath);
            foreach ($files as $file) {
                if ($file !== '.' && $file !== '..' && pathinfo($file, PATHINFO_EXTENSION) === 'log') {
                    $filePath = $dirPath . '/' . $file;
                    $logFiles[] = array(
                        'name' => $file,
                        'displayName' => '[' . $dirType . '] ' . $file,
                        'path' => $filePath,
                        'directory' => $dirType,
                        'directoryPath' => $dirPath,
                        'size' => filesize($filePath),
                        'modified' => filemtime($filePath)
                    );
                }
            }
        }
    }
    
    // Sort by modification time (newest first)
    usort($logFiles, function($a, $b) {
        return $b['modified'] - $a['modified'];
    });
    
    return $logFiles;
}

/**
 * Read and format log file content
 * @param string $logFile The log file identifier in format "directory:filename"
 * @param int $lines Number of lines to read from end (0 = all)
 * @return string Formatted log content
 */
function readLogFile($logFile, $lines = 0) {
    global $timestamp;
    
    // Parse the log file identifier
    if (strpos($logFile, ':') !== false) {
        list($directory, $fileName) = explode(':', $logFile, 2);
        if ($directory === 'MQL4') {
            $logPath = LOGS_DIR_MQL4 . '/' . $fileName;
        } elseif ($directory === 'Main') {
            $logPath = LOGS_DIR_MAIN . '/' . $fileName;
        } else {
            return '<p class="error-message">Invalid directory: ' . htmlspecialchars($directory) . '</p>';
        }
        $displayName = '[' . $directory . '] ' . $fileName;
    } else {
        // Fallback for old format - try MQL4 directory first
        $logPath = LOGS_DIR_MQL4 . '/' . $logFile;
        if (!file_exists($logPath)) {
            $logPath = LOGS_DIR_MAIN . '/' . $logFile;
        }
        $displayName = $logFile;
        $fileName = $logFile;
    }
    
    if (!file_exists($logPath)) {
        return '<p class="error-message">Log file not found: ' . htmlspecialchars($displayName) . '</p>';
    }
    
    if (!is_readable($logPath)) {
        return '<p class="error-message">Cannot read log file: ' . htmlspecialchars($displayName) . '</p>';
    }
    
    $content = '';
    
    if ($lines > 0) {
        // Read last N lines
        $file = new SplFileObject($logPath);
        $file->seek(PHP_INT_MAX);
        $totalLines = $file->key();
        
        $startLine = max(0, $totalLines - $lines);
        $file->seek($startLine);
        
        while (!$file->eof()) {
            $content .= $file->current();
            $file->next();
        }
    } else {
        // Read entire file
        $content = file_get_contents($logPath);
    }
    
    $content = htmlspecialchars($content);
    
    $html = '<div class="log-file-header">';
    $html .= '<h4>Log File: ' . htmlspecialchars($displayName) . '</h4>';
    $html .= '<div class="log-file-info">';
    $html .= '<span>Size: ' . formatBytes(filesize($logPath)) . '</span>';
    $html .= '<span>Modified: ' . date('Y-m-d H:i:s', filemtime($logPath)) . '</span>';
    if ($lines > 0) {
        $html .= '<span>Showing last ' . $lines . ' lines</span>';
    }
    $html .= '</div>';
    $html .= '</div>';
    
    $html .= '<pre class="log-content">' . $content . '</pre>';
    $html .= '<small class="timestamp">Last updated: ' . $timestamp . '</small>';
    
    return $html;
}

/**
 * Format bytes to human readable format
 * @param int $bytes Size in bytes
 * @return string Formatted size
 */
function formatBytes($bytes) {
    if ($bytes >= 1073741824) {
        return number_format($bytes / 1073741824, 2) . ' GB';
    } elseif ($bytes >= 1048576) {
        return number_format($bytes / 1048576, 2) . ' MB';
    } elseif ($bytes >= 1024) {
        return number_format($bytes / 1024, 2) . ' KB';
    } else {
        return $bytes . ' bytes';
    }
}

// Unified AJAX handler
if (isset($_GET['ajax']) || isset($_POST['ajax'])) {
    $action = isset($_GET['ajax']) ? $_GET['ajax'] : $_POST['ajax'];
    
    switch ($action) {
        case 'account_log':
            refreshAccountLog();
            break;
            
        case 'total_net_profit':
            $totalNetProfit = getTotalNetProfit();
            $ordersCount = getTotalOrdersCount();
            echo json_encode([
                'value' => $totalNetProfit,
                'formatted' => $totalNetProfit !== null ? 
                    '<strong style="font-size: 1.2em;">zamknięte (' . $ordersCount . '): <span class="' . 
                    ((floatval($totalNetProfit) >= 0) ? 'profit-positive' : 'profit-negative') . 
                    '">' . htmlspecialchars($totalNetProfit) . '</span></strong>' :
                    '<strong style="color: #6c757d;">zamknięte (' . $ordersCount . '): N/A</strong>'
            ]);
            break;
            
        case 'account_profit':
            $accountProfit = getAccountProfit();
            $accountOrders = getAccountOrders();
            echo json_encode([
                'value' => $accountProfit,
                'orders' => $accountOrders,
                'formatted' => $accountProfit !== null ? 
                    '<strong style="font-size: 1.2em;">otwarte (' . ($accountOrders !== null ? $accountOrders : '0') . '): <span class="' . 
                    ((floatval($accountProfit) >= 0) ? 'profit-positive' : 'profit-negative') . 
                    '">' . htmlspecialchars($accountProfit) . '</span></strong>' :
                    '<strong style="color: #6c757d;">otwarte (' . ($accountOrders !== null ? $accountOrders : '0') . '): N/A</strong>'
            ]);
            break;
            
        case 'order_history_log':
            refreshOrderHistoryLog();
            break;
            
        case 'orders_list':
            $orders = getOrdersList();
            echo json_encode([
                'table' => generateOrdersTable($orders, true),
                'count' => count($orders)
            ]);
            break;
            
        case 'approved_orders_list':
            $approved_orders = getApprovedOrdersList();
            echo json_encode([
                'table' => generateOrdersTable($approved_orders, true, true),
                'count' => count($approved_orders)
            ]);
            break;
            
        case 'modified_orders_list':
            $modified_orders = getModifiedOrdersList();
            echo json_encode([
                'table' => generateModifiedOrdersTable($modified_orders),
                'count' => count($modified_orders)
            ]);
            break;
            
        case 'to_be_modified_orders_list':
            $to_be_modified_orders = getToBeModifiedOrdersList();
            echo json_encode([
                'table' => generateToBeModifiedOrdersTable($to_be_modified_orders),
                'count' => count($to_be_modified_orders)
            ]);
            break;
            
        case 'orders_log_list':
            $orders_log = getOrdersLogData();
            echo json_encode([
                'table' => generateOrdersLogTable($orders_log),
                'count' => count($orders_log)
            ]);
            break;
            
        case 'orders_log_data':
            $orders_log = getOrdersLogData();
            echo json_encode([
                'orders' => $orders_log,
                'count' => count($orders_log)
            ]);
            break;
            
        case 'logs_list':
            $logFiles = getLogFilesList();
            echo json_encode([
                'files' => $logFiles,
                'count' => count($logFiles)
            ]);
            break;
            
        case 'read_log':
            if (!isset($_GET['file'])) {
                echo json_encode(['success' => false, 'message' => 'File parameter required']);
                break;
            }
            
            $logFile = $_GET['file'];
            $lines = isset($_GET['lines']) ? intval($_GET['lines']) : 0;
            
            // Validate file name
            if (strpos($logFile, ':') !== false) {
                list($directory, $fileName) = explode(':', $logFile, 2);
                if (!in_array($directory, ['MQL4', 'Main']) || !preg_match('/^[a-zA-Z0-9_.-]+\.log$/', $fileName)) {
                    echo json_encode(['success' => false, 'message' => 'Invalid log file identifier']);
                    break;
                }
            } else {
                if (!preg_match('/^[a-zA-Z0-9_.-]+\.log$/', $logFile)) {
                    echo json_encode(['success' => false, 'message' => 'Invalid log file name']);
                    break;
                }
            }
            
            $content = readLogFile($logFile, $lines);
            echo json_encode(['success' => true, 'content' => $content]);
            break;
            
        case 'add_new_order':
            // Get and validate form data
            $symbol = isset($_POST['symbol']) ? trim($_POST['symbol']) : '';
            $orderType = isset($_POST['type']) ? trim($_POST['type']) : '';
            $lots = isset($_POST['lots']) ? trim($_POST['lots']) : '';
            $price = isset($_POST['price']) ? trim($_POST['price']) : '';
            $stopLoss = isset($_POST['stop_loss']) ? trim($_POST['stop_loss']) : '';
            $takeProfit = isset($_POST['take_profit']) ? trim($_POST['take_profit']) : '';
            
            // Validate required fields
            if (empty($symbol)) {
                echo json_encode(['success' => false, 'message' => 'Symbol is required']);
                break;
            }
            
            // Validate order type
            $validOrderTypes = ['buy', 'sell', 'buylimit', 'selllimit', 'buystop', 'sellstop'];
            if (!in_array(strtolower($orderType), $validOrderTypes)) {
                echo json_encode(['success' => false, 'message' => 'Invalid order type']);
                break;
            }
            
            if (empty($lots) || !is_numeric($lots) || floatval($lots) <= 0) {
                echo json_encode(['success' => false, 'message' => 'Valid lots value is required']);
                break;
            }    
            
            // Validate optional numeric fields
            if (!empty($stopLoss) && !is_numeric($stopLoss)) {
                echo json_encode(['success' => false, 'message' => 'Stop Loss must be a valid number']);
                break;
            }
            
            if (!empty($takeProfit) && !is_numeric($takeProfit)) {
                echo json_encode(['success' => false, 'message' => 'Take Profit must be a valid number']);
                break;
            }
            
            // Set default values for empty optional fields
            $price = empty($price) ? '0' : $price;
            $stopLoss = empty($stopLoss) ? '0' : $stopLoss;
            $takeProfit = empty($takeProfit) ? '0' : $takeProfit;
            
            // Create new order string
            $newOrder = $symbol . ' ' . $orderType . ' ' . $lots . ' ' . $price . ' ' . $stopLoss . ' ' . $takeProfit;
            
            // Ensure proper newline handling
            $needsNewlineBefore = false;
            if (file_exists(ORDERS_FILE)) {
                $existingContent = file_get_contents(ORDERS_FILE);
                if (!empty($existingContent) && substr($existingContent, -1) !== "\n") {
                    $needsNewlineBefore = true;
                }
            }
            
            $contentToAppend = ($needsNewlineBefore ? "\n" : '') . $newOrder . "\n";
            $result = file_put_contents(ORDERS_FILE, $contentToAppend, FILE_APPEND | LOCK_EX);
            
            if ($result !== false) {
                echo json_encode(['success' => true, 'message' => 'New ' . $orderType . ' order added for ' . $symbol]);
            } else {
                echo json_encode(['success' => false, 'message' => 'Failed to add new order to file']);
            }
            break;
            
        case 'add_p':
        case 'add_r':
        case 'add_p_to_be_modified':
        case 'add_r_to_be_modified':
        case 'cancel_order':
        case 'remove_approved':
        case 'remove_modified':
        case 'remove_to_be_modified':
            if (!isset($_GET['row'])) {
                echo json_encode(['success' => false, 'message' => 'Row parameter required']);
                break;
            }
            
            $rowNumber = intval($_GET['row']);
            
            // Check password for P and R actions
            if (in_array($action, ['add_p', 'add_r', 'add_p_to_be_modified', 'add_r_to_be_modified'])) {
                $actionType = (strpos($action, '_p') !== false) ? 'p' : 'r';
                $password = isset($_GET['password']) ? $_GET['password'] : '';
                
                if (!validatePassword($actionType, $password)) {
                    echo json_encode(['success' => false, 'message' => 'Invalid password for action ' . strtoupper($actionType)]);
                    break;
                }
            }
            
            if ($action === 'remove_approved') {
                $approved_orders = getApprovedOrdersList();
                
                if ($rowNumber > 0 && $rowNumber <= count($approved_orders)) {
                    array_splice($approved_orders, $rowNumber - 1, 1);
                    file_put_contents(APPROVED_FILE, implode("\n", $approved_orders));
                    echo json_encode(['success' => true, 'message' => 'Approved order row ' . $rowNumber . ' removed']);
                } else {
                    echo json_encode(['success' => false, 'message' => 'Invalid row number']);
                }
            } elseif ($action === 'remove_modified') {
                $modified_orders = getModifiedOrdersList();
                
                if ($rowNumber > 0 && $rowNumber <= count($modified_orders)) {
                    array_splice($modified_orders, $rowNumber - 1, 1);
                    file_put_contents(MODIFIED_FILE, implode("\n", $modified_orders));
                    echo json_encode(['success' => true, 'message' => 'Modified order row ' . $rowNumber . ' removed']);
                } else {
                    echo json_encode(['success' => false, 'message' => 'Invalid row number']);
                }
            } elseif ($action === 'remove_to_be_modified') {
                $to_be_modified_orders = getToBeModifiedOrdersList();
                
                if ($rowNumber > 0 && $rowNumber <= count($to_be_modified_orders)) {
                    array_splice($to_be_modified_orders, $rowNumber - 1, 1);
                    file_put_contents(TO_BE_MODIFIED_FILE, implode("\n", $to_be_modified_orders));
                    echo json_encode(['success' => true, 'message' => 'To be modified order row ' . $rowNumber . ' removed']);
                } else {
                    echo json_encode(['success' => false, 'message' => 'Invalid row number']);
                }
            } elseif ($action === 'add_p_to_be_modified' || $action === 'add_r_to_be_modified') {
                $to_be_modified_orders = getToBeModifiedOrdersList();
                
                if ($rowNumber > 0 && $rowNumber <= count($to_be_modified_orders)) {
                    $orderIndex = $rowNumber - 1;
                    $flag = ($action === 'add_p_to_be_modified') ? 'p' : 'r';
                    $flagName = strtoupper($flag);
                    
                    if (!orderHasFlag($to_be_modified_orders[$orderIndex], $flag)) {
                        $to_be_modified_orders[$orderIndex] .= ' ' . $flag;
                        
                        if (orderHasBothFlags($to_be_modified_orders[$orderIndex])) {
                            // Move to modified.txt when both P and R flags are set
                            $orderToMove = $to_be_modified_orders[$orderIndex];
                            
                            // Remove the 'p' and 'r' flags from the order before moving to modified
                            $orderParts = explode(' ', trim($orderToMove));
                            $cleanedOrder = array();
                            foreach ($orderParts as $part) {
                                if ($part !== 'p' && $part !== 'r') {
                                    $cleanedOrder[] = $part;
                                }
                            }
                            $cleanOrderString = implode(' ', $cleanedOrder);
                            
                            // Ensure proper newline handling for modified.txt
                            $needsNewlineBefore = false;
                            if (file_exists(MODIFIED_FILE)) {
                                $existingContent = file_get_contents(MODIFIED_FILE);
                                if (!empty($existingContent) && substr($existingContent, -1) !== "\n") {
                                    $needsNewlineBefore = true;
                                }
                            }
                            
                            // Prepare the content to append to modified.txt
                            $contentToAppend = ($needsNewlineBefore ? "\n" : '') . $cleanOrderString . "\n";
                            
                            // Append to modified.txt
                            $result = file_put_contents(MODIFIED_FILE, $contentToAppend, FILE_APPEND | LOCK_EX);
                            
                            if ($result !== false) {
                                // Remove from to_be_modified.txt
                                array_splice($to_be_modified_orders, $orderIndex, 1);
                                file_put_contents(TO_BE_MODIFIED_FILE, implode("\n", $to_be_modified_orders));
                                echo json_encode(['success' => true, 'message' => $flagName . ' added to row ' . $rowNumber . '. Order moved to modified list (both P and R flags set)']);
                            } else {
                                echo json_encode(['success' => false, 'message' => 'Failed to move order to modified list']);
                            }
                        } else {
                            file_put_contents(TO_BE_MODIFIED_FILE, implode("\n", $to_be_modified_orders));
                            echo json_encode(['success' => true, 'message' => $flagName . ' added to row ' . $rowNumber]);
                        }
                    } else {
                        echo json_encode(['success' => false, 'message' => $flagName . ' already exists in row ' . $rowNumber]);
                    }
                } else {
                    echo json_encode(['success' => false, 'message' => 'Invalid row number']);
                }
            } else {
                $orders = getOrdersList();
                
                if ($rowNumber > 0 && $rowNumber <= count($orders)) {
                    $orderIndex = $rowNumber - 1;
                    
                    if ($action === 'cancel_order') {
                        array_splice($orders, $orderIndex, 1);
                        file_put_contents(ORDERS_FILE, implode("\n", $orders));
                        echo json_encode(['success' => true, 'message' => 'Order row ' . $rowNumber . ' canceled and removed']);
                    } else {
                        $flag = ($action === 'add_p') ? 'p' : 'r';
                        $flagName = strtoupper($flag);
                        
                        if (!orderHasFlag($orders[$orderIndex], $flag)) {
                            $orders[$orderIndex] .= ' ' . $flag;
                            
                            if (orderHasBothFlags($orders[$orderIndex])) {
                                if (moveOrderToApproved($orders[$orderIndex])) {
                                    array_splice($orders, $orderIndex, 1);
                                    file_put_contents(ORDERS_FILE, implode("\n", $orders));
                                    echo json_encode(['success' => true, 'message' => $flagName . ' added to row ' . $rowNumber . '. Order moved to approved list (both P and R flags set)']);
                                } else {
                                    echo json_encode(['success' => false, 'message' => 'Failed to move order to approved list']);
                                }
                            } else {
                                file_put_contents(ORDERS_FILE, implode("\n", $orders));
                                echo json_encode(['success' => true, 'message' => $flagName . ' added to row ' . $rowNumber]);
                            }
                        } else {
                            echo json_encode(['success' => false, 'message' => $flagName . ' already exists in row ' . $rowNumber]);
                        }
                    }
                } else {
                    echo json_encode(['success' => false, 'message' => 'Invalid row number']);
                }
            }
            break;
            
        case 'drop_order':
            if (!isset($_POST['ticket'])) {
                echo json_encode(['success' => false, 'message' => 'Ticket parameter required']);
                break;
            }
            
            $ticket = trim($_POST['ticket']);
            
            if (empty($ticket)) {
                echo json_encode(['success' => false, 'message' => 'Valid ticket ID is required']);
                break;
            }
            
            // Ensure proper newline handling
            $needsNewlineBefore = false;
            if (file_exists(DROPPED_FILE)) {
                $existingContent = file_get_contents(DROPPED_FILE);
                if (!empty($existingContent) && substr($existingContent, -1) !== "\n") {
                    $needsNewlineBefore = true;
                }
            }
            
            $contentToAppend = ($needsNewlineBefore ? "\n" : '') . $ticket . "\n";
            $result = file_put_contents(DROPPED_FILE, $contentToAppend, FILE_APPEND | LOCK_EX);
            
            if ($result !== false) {
                echo json_encode(['success' => true, 'message' => 'Ticket ' . $ticket . ' added to dropped orders']);
            } else {
                echo json_encode(['success' => false, 'message' => 'Failed to add ticket to dropped orders file']);
            }
            break;
            
        case 'modify_order':
            if (!isset($_POST['ticket']) || !isset($_POST['stop_loss']) || !isset($_POST['take_profit'])) {
                echo json_encode(['success' => false, 'message' => 'Ticket, stop loss, and take profit parameters required']);
                break;
            }
            
            $ticket = trim($_POST['ticket']);
            $stopLoss = trim($_POST['stop_loss']);
            $takeProfit = trim($_POST['take_profit']);
            
            if (empty($ticket)) {
                echo json_encode(['success' => false, 'message' => 'Valid ticket ID is required']);
                break;
            }
            
            // Validate numeric fields
            if (!empty($stopLoss) && !is_numeric($stopLoss)) {
                echo json_encode(['success' => false, 'message' => 'Stop Loss must be a valid number']);
                break;
            }
            
            if (!empty($takeProfit) && !is_numeric($takeProfit)) {
                echo json_encode(['success' => false, 'message' => 'Take Profit must be a valid number']);
                break;
            }
            
            // Set default values for empty fields
            $stopLoss = empty($stopLoss) ? '0' : $stopLoss;
            $takeProfit = empty($takeProfit) ? '0' : $takeProfit;
            
            // Create modification string: TICKET STOPLOSS TAKEPROFIT
            $modificationLine = $ticket . ' ' . $stopLoss . ' ' . $takeProfit;
            
            // Ensure proper newline handling
            $needsNewlineBefore = false;
            if (file_exists(TO_BE_MODIFIED_FILE)) {
                $existingContent = file_get_contents(TO_BE_MODIFIED_FILE);
                if (!empty($existingContent) && substr($existingContent, -1) !== "\n") {
                    $needsNewlineBefore = true;
                }
            }
            
            $contentToAppend = ($needsNewlineBefore ? "\n" : '') . $modificationLine . "\n";
            $result = file_put_contents(TO_BE_MODIFIED_FILE, $contentToAppend, FILE_APPEND | LOCK_EX);
            
            if ($result !== false) {
                echo json_encode(['success' => true, 'message' => 'Modification request for ticket ' . $ticket . ' added (SL: ' . $stopLoss . ', TP: ' . $takeProfit . ')']);
            } else {
                echo json_encode(['success' => false, 'message' => 'Failed to add modification request to file']);
            }
            break;
            
        default:
            echo json_encode(['success' => false, 'message' => 'Invalid action']);
            break;
    }
    exit;
}

// Main page content
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo APP_TITLE; ?>: <?php 
        $accountProfit = getAccountProfit();
        if ($accountProfit !== null) {
            echo htmlspecialchars($accountProfit);
        } else {
            echo 'N/A';
        }
    ?></title>
    <style>
        <?php echo file_get_contents('/home/ubuntu/repo/styles.css'); ?>
    </style>
</head>
<body>
    <div class="container">
        <h1>pora zarobić</h1>
        
        <!-- Total Net Profit Display -->
        <div id="total-net-profit-display" style="margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #007bff; border-radius: 4px; text-align: center;">
            <?php 
            $totalNetProfit = getTotalNetProfit();
            $ordersCount = getTotalOrdersCount();
            if ($totalNetProfit !== null) {
                $profitClass = (floatval($totalNetProfit) >= 0) ? 'profit-positive' : 'profit-negative';
                echo '<strong style="font-size: 1.2em;">zamknięte (' . $ordersCount . '): <span class="' . $profitClass . '">' . htmlspecialchars($totalNetProfit) . '</span></strong>';
            } else {
                echo '<strong style="color: #6c757d;">zamknięte (' . $ordersCount . '): N/A</strong>';
            }
            ?>
            <br/>
            <?php 
            $accountProfit = getAccountProfit();
            $accountOrders = getAccountOrders();
            if ($accountProfit !== null) {
                $profitClass = (floatval($accountProfit) >= 0) ? 'profit-positive' : 'profit-negative';
                echo '<strong style="font-size: 1.2em;">otwarte (' . ($accountOrders !== null ? $accountOrders : '0') . '): <span class="' . $profitClass . '">' . htmlspecialchars($accountProfit) . '</span></strong>';
            } else {
                echo '<strong style="color: #6c757d;">otwarte (' . ($accountOrders !== null ? $accountOrders : '0') . '): N/A</strong>';
            }
            ?>
        </div>
        
        <hr style="margin: 30px 0;">
        
        <h2>Account and Market Log</h2>
        <div id="account-log" class="content-section account-log">
            <?php refreshAccountLog(); ?>
        </div>

        <!--<button onclick="refreshAccountLog()" style="margin-top: 15px;">Refresh</button>-->

        <hr style="margin: 30px 0;">
        
        <h2 id="orders-log-heading">Orders Log (<?php $orders_log = getOrdersLogData(); echo count($orders_log); ?>)</h2>
        <div id="orders-log-list" class="content-section orders-log">
            <?php
            echo generateOrdersLogTable($orders_log);
            ?>
        </div>

        <!--<button onclick="refreshOrdersLogList()" style="margin-top: 15px;">Refresh</button>-->
        
        <hr style="margin: 30px 0;">
        
        <div class="modify-order-section">
            <h3>Modify Order</h3>
            <div class="modify-order-form">
                <div class="form-group">
                    <label for="modify-ticket-select">Select Ticket</label>
                    <select id="modify-ticket-select" name="modify_ticket" onchange="loadOrderDetails()">
                        <option value="">Select Ticket</option>
                        <?php
                        $orders_log = getOrdersLogData();
                        foreach ($orders_log as $order) {
                            echo '<option value="' . htmlspecialchars($order['ticket']) . '" 
                                    data-sl="' . htmlspecialchars($order['stopLoss']) . '" 
                                    data-tp="' . htmlspecialchars($order['takeProfit']) . '">' . 
                                 htmlspecialchars($order['ticket']) . ' - ' . 
                                 htmlspecialchars($order['symbol']) . ' (' . 
                                 htmlspecialchars($order['type']) . ')</option>';
                        }
                        ?>
                    </select>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="modify-stop-loss">Stop Loss</label>
                        <input type="number" id="modify-stop-loss" name="stop_loss" step="0.00001" min="0" placeholder="0.00000">
                    </div>
                    <div class="form-group">
                        <label for="modify-take-profit">Take Profit</label>
                        <input type="number" id="modify-take-profit" name="take_profit" step="0.00001" min="0" placeholder="0.00000">
                    </div>
                </div>
                <div class="form-group">
                    <button type="button" onclick="modifyOrder()" class="modify-order-btn">Modify</button>
                </div>
            </div>
        </div>
        
        <?php $to_be_modified_orders = getToBeModifiedOrdersList(); ?>
        <div id="to-be-modified-orders-section" <?php if (empty($to_be_modified_orders)): ?>style="display: none;"<?php endif; ?>>
            <hr style="margin: 30px 0;">
            
            <h2 id="to-be-modified-orders-heading">Orders To Be Modified (<?php echo count($to_be_modified_orders); ?>)</h2>
            <div id="to-be-modified-orders-list" class="content-section to-be-modified-orders">
                <?php
                echo generateToBeModifiedOrdersTable($to_be_modified_orders);
                ?>
            </div>
            
            <button onclick="refreshToBeModifiedOrdersList()" style="margin-top: 15px;">Refresh</button>
        </div>
	
        <?php $modified_orders = getModifiedOrdersList(); ?>
        <div id="modified-orders-section" <?php if (empty($modified_orders)): ?>style="display: none;"<?php endif; ?>>
            <hr style="margin: 30px 0;">
            
            <h2 id="modified-orders-heading">Modified Orders (<?php echo count($modified_orders); ?>)</h2>
            <div id="modified-orders-list" class="content-section modified-orders">
                <?php
                echo generateModifiedOrdersTable($modified_orders);
                ?>
            </div>
            
            <button onclick="refreshModifiedOrdersList()" style="margin-top: 15px;">Refresh</button>
        </div>
        <hr style="margin: 30px 0;">
        
        <div class="drop-order-section">
            <h3>Drop Order</h3>
            <div class="drop-order-form">
                <div class="form-group">
                    <label for="ticket-select">Select Ticket</label>
                    <select id="ticket-select" name="ticket">
                        <option value="">Select Ticket</option>
                        <?php
                        $orders_log = getOrdersLogData();
                        foreach ($orders_log as $order) {
                            echo '<option value="' . htmlspecialchars($order['ticket']) . '">' . 
                                 htmlspecialchars($order['ticket']) . ' - ' . 
                                 htmlspecialchars($order['symbol']) . ' (' . 
                                 htmlspecialchars($order['type']) . ')</option>';
                        }
                        ?>
                    </select>
                </div>
                <div class="form-group">
                    <button type="button" onclick="dropOrder()" class="drop-order-btn">Drop</button>
                </div>
            </div>
        </div>        <hr style="margin: 30px 0;">
        
        <div class="new-order-section">
            <h3>Add New Order</h3>
            <form id="new-order-form" class="new-order-form">
                <div class="form-row">
                    <div class="form-group">
                        <label for="symbol">Symbol *</label>
                        <select id="symbol" name="symbol" required onchange="updateFormPrecision()">
                            <option value="">Select Symbol</option>
                            <option value="EURUSD">EURUSD</option>
                            <option value="US100.f">US100.f</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="orderType">Type *</label>
                        <select id="orderType" name="type" required>
                            <option value="BUY">Buy</option>
                            <option value="SELL">Sell</option>
                            <option value="BUYLIMIT">Buy Limit</option>
                            <option value="SELLLIMIT">Sell Limit</option>
                            <option value="BUYSTOP">Buy Stop</option>
                            <option value="SELLSTOP">Sell Stop</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="lots">Lots *</label>
                        <input type="number" id="lots" name="lots" step="0.01" min="0.01" placeholder="0.01" required>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="price">Price/Level *</label>
                        <input type="number" id="price" name="price" step="0.00001" min="0.00001" placeholder="0 (optional)">
                    </div>
                    <div class="form-group">
                        <label for="stopLoss">Stop Loss</label>
                        <input type="number" id="stopLoss" name="stop_loss" step="0.00001" min="0" placeholder="0 (optional)">
                    </div>
                    <div class="form-group">
                        <label for="takeProfit">Take Profit</label>
                        <input type="number" id="takeProfit" name="take_profit" step="0.00001" min="0" placeholder="0 (optional)">
                    </div>
                </div>
                <div class="form-row">
                    <button type="submit" class="add-order-btn">Add Order</button>
                </div>
            </form>
        </div>
        
        <?php $orders = getOrdersList(); ?>
        <div id="orders-list-section" <?php if (empty($orders)): ?>style="display: none;"<?php endif; ?>>
            <hr style="margin: 30px 0;">
            
            <h2 id="orders-list-heading">Review New Orders (<?php echo count($orders); ?>)</h2>
            <div id="orders-list" class="content-section orders-list">
                <?php
                echo generateOrdersTable($orders, true);
                ?>
            </div>
            
            <button onclick="refreshOrdersList()" style="margin-top: 15px;">Refresh</button>
        </div>
        
        <?php $approved_orders = getApprovedOrdersList(); ?>
        <div id="approved-orders-section" <?php if (empty($approved_orders)): ?>style="display: none;"<?php endif; ?>>
            <hr style="margin: 30px 0;">
            
            <h2 id="approved-orders-heading">Approved Orders (<?php echo count($approved_orders); ?>)</h2>
            <div id="approved-orders-list" class="content-section approved-orders">
                <?php
                echo generateOrdersTable($approved_orders, true, true);
                ?>
            </div>
            
            <button onclick="refreshApprovedOrdersList()" style="margin-top: 15px;">Refresh</button>
        </div>        
	
        <hr style="margin: 30px 0;">
        
        <h2>Daily Order History Log</h2>
        <div id="order-history-log" class="content-section order-history-log">
            <?php refreshOrderHistoryLog(); ?>
        </div>

        <!--<button onclick="refreshOrderHistoryLog()" style="margin-top: 15px;">Refresh</button>-->

        <hr style="margin: 30px 0;">
        
        <h2 id="logs-heading">Logs (<?php $logFiles = getLogFilesList(); echo count($logFiles); ?> files)</h2>
        <div class="content-section logs-section">
            <div class="logs-controls">
                <div class="form-group">
                    <label for="log-file-select">Select Log File:</label>
                    <select id="log-file-select" onchange="loadLogFile()">
                        <option value="">-- Select a log file --</option>
                        <?php
                        foreach ($logFiles as $logFile) {
                            $fileId = $logFile['directory'] . ':' . $logFile['name'];
                            echo '<option value="' . htmlspecialchars($fileId) . '">' . 
                                 htmlspecialchars($logFile['displayName']) . ' (' . formatBytes($logFile['size']) . ')</option>';
                        }
                        ?>
                    </select>
                </div>
                <div class="form-group">
                    <label for="log-lines-select">Lines to show:</label>
                    <select id="log-lines-select" onchange="loadLogFile()">
                        <option value="0">All lines</option>
                        <option value="50">Last 50 lines</option>
                        <option value="100" selected>Last 100 lines</option>
                        <option value="200">Last 200 lines</option>
                        <option value="500">Last 500 lines</option>
                        <option value="1000">Last 1000 lines</option>
                    </select>
                </div>
                <button onclick="refreshLogsList()" class="refresh-logs-btn">Refresh Files List</button>
            </div>
            
            <div id="log-content" class="log-content-area">
                <p class="info-message">Select a log file to view its contents.</p>
            </div>
        </div>
    </div>

    <script>
        // App configuration
        const APP = {
            sections: {
                account_log: { element: 'account-log', action: 'account_log', text: true, onSuccess: 'refreshProfits' },
                orders_log: { element: 'orders-log-list', action: 'orders_log_list', heading: 'orders-log-heading', prefix: 'Orders Log' },
                orders_list: { element: 'orders-list', action: 'orders_list', heading: 'orders-list-heading', prefix: 'Review List' },
                approved_orders: { element: 'approved-orders-list', action: 'approved_orders_list', heading: 'approved-orders-heading', prefix: 'Approved Orders' },
                modified_orders: { element: 'modified-orders-list', action: 'modified_orders_list', heading: 'modified-orders-heading', prefix: 'Modified Orders' },
                to_be_modified_orders: { element: 'to-be-modified-orders-list', action: 'to_be_modified_orders_list', heading: 'to-be-modified-orders-heading', prefix: 'Orders To Be Modified' },
                order_history_log: { element: 'order-history-log', action: 'order_history_log', text: true, onSuccess: 'refreshProfits' }
            },
            actions: {
                add_p: { confirm: false, refresh: 'orders' },
                add_r: { confirm: false, refresh: 'orders' },
                add_p_to_be_modified: { confirm: false, refresh: 'to_be_modified' },
                add_r_to_be_modified: { confirm: false, refresh: 'to_be_modified' },
                cancel_order: { confirm: 'Are you sure you want to cancel and remove this order?', refresh: 'orders' },
                remove_approved: { confirm: 'Are you sure you want to remove this approved order?', refresh: 'approved' },
                remove_modified: { confirm: 'Are you sure you want to remove this modified order?', refresh: 'modified' },
                remove_to_be_modified: { confirm: 'Are you sure you want to remove this order to be modified?', refresh: 'to_be_modified' }
            }
        };

        // Utility functions
        const utils = {
            request: (url, options = {}) => {
                return fetch(url, { method: options.method || 'GET', body: options.body || null })
                    .then(response => response.ok ? (options.text ? response.text() : response.json()) : Promise.reject(new Error('Network error')));
            },
            
            formatBytes: (bytes) => {
                if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(2) + ' GB';
                if (bytes >= 1048576) return (bytes / 1048576).toFixed(2) + ' MB';
                if (bytes >= 1024) return (bytes / 1024).toFixed(2) + ' KB';
                return bytes + ' bytes';
            },
            
            updateElement: (id, content) => {
                const el = document.getElementById(id);
                if (el) el.innerHTML = content;
            },
            
            showError: (element, message) => {
                utils.updateElement(element, `<p style="color: #dc3545;">Error: ${message}</p>`);
            },
            
            // Get step value for price inputs based on symbol
            getPriceStep: (symbol) => {
                switch(symbol) {
                    case 'US100.f':
                        return '0.01';  // 2 decimal places
                    case 'EURUSD':
                        return '0.00001';  // 5 decimal places
                    default:
                        return '0.00001';  // Default to 5 decimal places
                }
            },
            
            // Get placeholder text based on symbol
            getPricePlaceholder: (symbol) => {
                switch(symbol) {
                    case 'US100.f':
                        return '0.00';
                    case 'EURUSD':
                        return '0.00000';
                    default:
                        return '0.00000';
                }
            }
        };

        // Core refresh function
        function refreshSection(sectionKey, updateHeading = false) {
            const config = APP.sections[sectionKey];
            if (!config) return;
            
            utils.request(`index.php?ajax=${config.action}`, { text: config.text })
                .then(data => {
                    if (config.text) {
                        utils.updateElement(config.element, data);
                    } else {
                        utils.updateElement(config.element, data.table);
                        if (config.heading && updateHeading) {
                            utils.updateElement(config.heading, `${config.prefix} (${data.count})`);
                        }
                    }
                    if (config.onSuccess === 'refreshProfits') refresh.profits();
                })
                .catch(error => utils.showError(config.element, error.message));
        }

        // Consolidated refresh functions
        const refresh = {
            accountLog: () => refreshSection('account_log'),
            ordersLog: () => {
                refreshSection('orders_log', true);
                // Also refresh the drop order list when orders log updates
                refreshDropOrderList();
            },
            ordersList: () => {
                utils.request('index.php?ajax=orders_list')
                    .then(data => {
                        const section = document.getElementById('orders-list-section');
                        section.style.display = data.count > 0 ? 'block' : 'none';
                        if (data.count > 0) {
                            utils.updateElement('orders-list', data.table);
                            utils.updateElement('orders-list-heading', `Review New Orders (${data.count})`);
                        }
                    })
                    .catch(error => {
                        console.error('Error refreshing orders list:', error);
                        utils.showError('orders-list', error.message);
                    });
            },
            orderHistoryLog: () => refreshSection('order_history_log'),
            approvedOrders: () => {
                utils.request('index.php?ajax=approved_orders_list')
                    .then(data => {
                        const section = document.getElementById('approved-orders-section');
                        section.style.display = data.count > 0 ? 'block' : 'none';
                        if (data.count > 0) {
                            utils.updateElement('approved-orders-list', data.table);
                            utils.updateElement('approved-orders-heading', `Approved Orders (${data.count})`);
                        }
                    })
                    .catch(error => {
                        console.error('Error refreshing approved orders:', error);
                        utils.showError('approved-orders-list', error.message);
                    });
            },
            modifiedOrders: () => {
                utils.request('index.php?ajax=modified_orders_list')
                    .then(data => {
                        const section = document.getElementById('modified-orders-section');
                        section.style.display = data.count > 0 ? 'block' : 'none';
                        if (data.count > 0) {
                            utils.updateElement('modified-orders-list', data.table);
                            utils.updateElement('modified-orders-heading', `Modified Orders (${data.count})`);
                        }
                    })
                    .catch(error => {
                        console.error('Error refreshing modified orders:', error);
                        utils.showError('modified-orders-list', error.message);
                    });
            },
            toBeModifiedOrders: () => {
                utils.request('index.php?ajax=to_be_modified_orders_list')
                    .then(data => {
                        const section = document.getElementById('to-be-modified-orders-section');
                        section.style.display = data.count > 0 ? 'block' : 'none';
                        if (data.count > 0) {
                            utils.updateElement('to-be-modified-orders-list', data.table);
                            utils.updateElement('to-be-modified-orders-heading', `Orders To Be Modified (${data.count})`);
                        }
                    })
                    .catch(error => {
                        console.error('Error refreshing to be modified orders:', error);
                        utils.showError('to-be-modified-orders-list', error.message);
                    });
            },
            profits: () => {
                Promise.all([
                    utils.request('index.php?ajax=total_net_profit'),
                    utils.request('index.php?ajax=account_profit')
                ])
                .then(([total, account]) => {
                    utils.updateElement('total-net-profit-display', total.formatted + '<br/>' + account.formatted);
                    // Update page title with current profit
                    document.title = 'watchdog: ' + (account.value !== null ? account.value : 'N/A');
                })
                .catch(error => console.error('Error refreshing profits:', error));
            }
        };

        // Legacy function aliases for backward compatibility
        const refreshAccountLog = refresh.accountLog;
        const refreshOrdersLogList = refresh.ordersLog;
        const refreshOrdersList = refresh.ordersList;
        const refreshApprovedOrdersList = refresh.approvedOrders;
        const refreshModifiedOrdersList = refresh.modifiedOrders;
        const refreshToBeModifiedOrdersList = refresh.toBeModifiedOrders;
        const refreshOrderHistoryLog = refresh.orderHistoryLog;

        // Consolidated profit refresh
        function refreshProfits() {
            refresh.profits();
        }

        // Generic action handler
        function handleAction(actionKey, rowNumber) {
            const config = APP.actions[actionKey];
            if (config.confirm && !confirm(config.confirm)) return;
            
            // Check if this is a P or R action that requires password
            const isPasswordAction = ['add_p', 'add_r', 'add_p_to_be_modified', 'add_r_to_be_modified'].includes(actionKey);
            let password = '';
            
            if (isPasswordAction) {
                const actionType = actionKey.includes('_p') ? 'P' : 'R';
                password = prompt(`Enter password for action ${actionType}:`);
                
                if (password === null) {
                    // User cancelled the prompt
                    return;
                }
                
                if (password === '') {
                    alert('Password cannot be empty');
                    return;
                }
            }
            
            const url = isPasswordAction 
                ? `index.php?ajax=${actionKey}&row=${rowNumber}&password=${encodeURIComponent(password)}`
                : `index.php?ajax=${actionKey}&row=${rowNumber}`;
                
            utils.request(url)
                .then(data => {
                    alert(data.success ? data.message : 'Error: ' + data.message);
                    if (data.success) {
                        if (config.refresh === 'approved') refresh.approvedOrders();
                        else if (config.refresh === 'modified') refresh.modifiedOrders();
                        else if (config.refresh === 'to_be_modified') {
                            refresh.toBeModifiedOrders();
                            if (data.message.includes('moved to modified list')) refresh.modifiedOrders();
                        }
                        else {
                            refresh.ordersList();
                            if (data.message.includes('moved to approved list')) refresh.approvedOrders();
                        }
                    }
                })
                .catch(error => alert('Error: ' + error.message));
        }

        // Action wrappers
        const handlePAction = (row) => handleAction('add_p', row);
        const handleRAction = (row) => handleAction('add_r', row);
        const handleCancelAction = (row) => handleAction('cancel_order', row);
        const handleRemoveApprovedAction = (row) => handleAction('remove_approved', row);
        const handleRemoveModifiedAction = (row) => handleAction('remove_modified', row);
        const handleRemoveToBeModifiedAction = (row) => handleAction('remove_to_be_modified', row);
        const handlePToBeModifiedAction = (row) => handleAction('add_p_to_be_modified', row);
        const handleRToBeModifiedAction = (row) => handleAction('add_r_to_be_modified', row);

        // Form and logs functions
        function updateFormPrecision() {
            const symbolSelect = document.getElementById('symbol');
            const selectedSymbol = symbolSelect.value;
            
            // Update price input fields based on selected symbol
            const priceField = document.getElementById('price');
            const stopLossField = document.getElementById('stopLoss');
            const takeProfitField = document.getElementById('takeProfit');
            
            const step = utils.getPriceStep(selectedSymbol);
            const placeholder = utils.getPricePlaceholder(selectedSymbol);
            
            if (priceField) {
                priceField.step = step;
                priceField.placeholder = placeholder + ' (optional)';
            }
            if (stopLossField) {
                stopLossField.step = step;
                stopLossField.placeholder = placeholder + ' (optional)';
            }
            if (takeProfitField) {
                takeProfitField.step = step;
                takeProfitField.placeholder = placeholder + ' (optional)';
            }
            
            // Also update modify order form fields
            const modifyStopLossField = document.getElementById('modify-stop-loss');
            const modifyTakeProfitField = document.getElementById('modify-take-profit');
            
            if (modifyStopLossField) {
                modifyStopLossField.step = step;
                modifyStopLossField.placeholder = placeholder;
            }
            if (modifyTakeProfitField) {
                modifyTakeProfitField.step = step;
                modifyTakeProfitField.placeholder = placeholder;
            }
        }

        function addNewOrder(formData) {
            utils.request('index.php', { method: 'POST', body: formData })
                .then(data => {
                    alert(data.success ? data.message : 'Error: ' + data.message);
                    if (data.success) {
                        refresh.ordersList();
                        document.getElementById('new-order-form').reset();
                    }
                })
                .catch(error => alert('Error adding order: ' + error.message));
        }

        function dropOrder() {
            const ticketSelect = document.getElementById('ticket-select');
            const selectedTicket = ticketSelect.value;
            
            if (!selectedTicket) {
                alert('Please select a ticket to drop.');
                return;
            }
            
            if (!confirm('Are you sure you want to drop ticket ' + selectedTicket + '?')) {
                return;
            }
            
            const formData = new FormData();
            formData.append('ajax', 'drop_order');
            formData.append('ticket', selectedTicket);
            
            utils.request('index.php', { method: 'POST', body: formData })
                .then(data => {
                    alert(data.success ? data.message : 'Error: ' + data.message);
                    if (data.success) {
                        // Reset the dropdown to default selection
                        ticketSelect.value = '';
                    }
                })
                .catch(error => alert('Error dropping order: ' + error.message));
        }

        function loadOrderDetails() {
            const modifyTicketSelect = document.getElementById('modify-ticket-select');
            const selectedOption = modifyTicketSelect.options[modifyTicketSelect.selectedIndex];
            
            if (selectedOption && selectedOption.value) {
                const stopLoss = selectedOption.getAttribute('data-sl');
                const takeProfit = selectedOption.getAttribute('data-tp');
                
                // Pre-fill the fields with current values (if not 'N/A' or '0')
                const slField = document.getElementById('modify-stop-loss');
                const tpField = document.getElementById('modify-take-profit');
                
                slField.value = (stopLoss && stopLoss !== 'N/A' && stopLoss !== '0') ? stopLoss : '';
                tpField.value = (takeProfit && takeProfit !== 'N/A' && takeProfit !== '0') ? takeProfit : '';
            } else {
                // Clear fields if no selection
                document.getElementById('modify-stop-loss').value = '';
                document.getElementById('modify-take-profit').value = '';
            }
        }

        function modifyOrder() {
            const ticketSelect = document.getElementById('modify-ticket-select');
            const selectedTicket = ticketSelect.value;
            const stopLoss = document.getElementById('modify-stop-loss').value;
            const takeProfit = document.getElementById('modify-take-profit').value;
            
            if (!selectedTicket) {
                alert('Please select a ticket to modify.');
                return;
            }
            
            if (!stopLoss && !takeProfit) {
                alert('Please enter at least one value (Stop Loss or Take Profit) to modify.');
                return;
            }
            
            const confirmMessage = `Are you sure you want to modify ticket ${selectedTicket}?\n` +
                                 `Stop Loss: ${stopLoss || '0'}\n` +
                                 `Take Profit: ${takeProfit || '0'}`;
            
            if (!confirm(confirmMessage)) {
                return;
            }
            
            const formData = new FormData();
            formData.append('ajax', 'modify_order');
            formData.append('ticket', selectedTicket);
            formData.append('stop_loss', stopLoss || '0');
            formData.append('take_profit', takeProfit || '0');
            
            utils.request('index.php', { method: 'POST', body: formData })
                .then(data => {
                    alert(data.success ? data.message : 'Error: ' + data.message);
                    if (data.success) {
                        // Reset the form
                        ticketSelect.value = '';
                        document.getElementById('modify-stop-loss').value = '';
                        document.getElementById('modify-take-profit').value = '';
                        // Refresh to be modified orders list to show the new modification
                        refresh.toBeModifiedOrders();
                    }
                })
                .catch(error => alert('Error modifying order: ' + error.message));
        }

        function refreshDropOrderList() {
            utils.request('index.php?ajax=orders_log_data')
                .then(data => {
                    // Update Drop Order dropdown
                    const ticketSelect = document.getElementById('ticket-select');
                    const currentDropValue = ticketSelect.value;
                    
                    // Clear existing options except the first one
                    ticketSelect.innerHTML = '<option value="">Select Ticket</option>';
                    
                    // Update Modify Order dropdown
                    const modifyTicketSelect = document.getElementById('modify-ticket-select');
                    const currentModifyValue = modifyTicketSelect.value;
                    
                    // Clear existing options except the first one
                    modifyTicketSelect.innerHTML = '<option value="">Select Ticket</option>';
                    
                    // Add options from orders data to both dropdowns
                    if (data && data.orders) {
                        data.orders.forEach(order => {
                            // Drop order option
                            const dropOption = new Option(
                                `${order.ticket} - ${order.symbol} (${order.type})`,
                                order.ticket
                            );
                            if (dropOption.value === currentDropValue) dropOption.selected = true;
                            ticketSelect.add(dropOption);
                            
                            // Modify order option with data attributes
                            const modifyOption = new Option(
                                `${order.ticket} - ${order.symbol} (${order.type})`,
                                order.ticket
                            );
                            modifyOption.setAttribute('data-sl', order.stopLoss || '0');
                            modifyOption.setAttribute('data-tp', order.takeProfit || '0');
                            if (modifyOption.value === currentModifyValue) modifyOption.selected = true;
                            modifyTicketSelect.add(modifyOption);
                        });
                    }
                    
                    // Note: We don't automatically reload order details during refresh
                    // to avoid overwriting user input in the modify form fields
                })
                .catch(error => console.error('Error refreshing order lists:', error));
        }

        function refreshLogsList() {
            const select = document.getElementById('log-file-select');
            const currentValue = select.value;
            
            utils.request('index.php?ajax=logs_list')
                .then(data => {
                    utils.updateElement('logs-heading', `Logs (${data.count} files)`);
                    select.innerHTML = '<option value="">-- Select a log file --</option>';
                    data.files.forEach(file => {
                        const option = new Option(
                            `${file.displayName} (${utils.formatBytes(file.size)})`,
                            `${file.directory}:${file.name}`
                        );
                        if (option.value === currentValue) option.selected = true;
                        select.add(option);
                    });
                    alert('Log files refreshed');
                })
                .catch(error => alert('Error: ' + error.message));
        }

        function loadLogFile() {
            const fileSelect = document.getElementById('log-file-select');
            const linesSelect = document.getElementById('log-lines-select');
            const contentDiv = document.getElementById('log-content');
            
            if (!fileSelect.value) {
                contentDiv.innerHTML = '<p class="info-message">Select a log file to view its contents.</p>';
                return;
            }
            
            contentDiv.innerHTML = '<p style="color: #856404;">Loading...</p>';
            
            utils.request(`index.php?ajax=read_log&file=${encodeURIComponent(fileSelect.value)}&lines=${linesSelect.value}`)
                .then(data => {
                    contentDiv.innerHTML = data.success ? data.content : `<p class="error-message">Error: ${data.message}</p>`;
                })
                .catch(error => utils.showError('log-content', error.message));
        }

        // Initialize app
        document.addEventListener('DOMContentLoaded', () => {
            // Form handler
            const form = document.getElementById('new-order-form');
            if (form) {
                form.addEventListener('submit', (e) => {
                    e.preventDefault();
                    const formData = new FormData(form);
                    formData.append('ajax', 'add_new_order');
                    addNewOrder(formData);
                });
            }
            
            // Initialize form precision
            updateFormPrecision();
            
            // Auto-refresh
            setInterval(() => {
                refresh.accountLog();
                refresh.ordersLog();
                refresh.orderHistoryLog();
                refresh.profits();
            }, 1000);
            
            // Additional interval for title updates every 10 seconds
            setInterval(() => {
                refresh.profits();
            }, 1000);
        });
    </script>
</body>
</html>
