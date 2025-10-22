<?php
// Set content type
header('Content-Type: text/html; charset=utf-8');

// Set timezone to match system timezone
date_default_timezone_set('Europe/Warsaw');

// File path constants
const ORDERS_FILE = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/orders.txt';
const APPROVED_FILE = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/approved.txt';
const ACCOUNT_LOG_FILE = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/account_log.txt';
const ORDERS_LOG_FILE = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/orders_log.txt';
const ORDER_HISTORY_LOG_FILE = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/order_history_log.txt';
const LOGS_DIR_MQL4 = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Logs';
const LOGS_DIR_MAIN = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/logs';

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
    
    foreach ($ordersLog as $index => $order) {
        $html .= '<tr class="selectable-row" onclick="selectOrderLogRow(' . $index . ', this)" data-order=\'' . htmlspecialchars(json_encode($order)) . '\'>';
        $html .= '<td>' . htmlspecialchars($order['ticket']) . '</td>';
        $html .= '<td>' . htmlspecialchars($order['type']) . '</td>';
        $html .= '<td>' . htmlspecialchars($order['symbol']) . '</td>';
        $html .= '<td>' . ($order['lots'] === 'N/A' ? '<span class="na-value">N/A</span>' : number_format(floatval($order['lots']), 2)) . '</td>';
        $html .= '<td>' . ($order['openPrice'] === 'N/A' ? '<span class="na-value">N/A</span>' : number_format(floatval($order['openPrice']), 2)) . '</td>';
        $html .= '<td>' . ($order['stopLoss'] === 'N/A' ? '<span class="na-value">N/A</span>' : number_format(floatval($order['stopLoss']), 2)) . '</td>';
        $html .= '<td>' . ($order['takeProfit'] === 'N/A' ? '<span class="na-value">N/A</span>' : number_format(floatval($order['takeProfit']), 2)) . '</td>';
        $html .= '<td class="' . (floatval($order['profit']) >= 0 ? 'profit-positive' : 'profit-negative') . '">' . number_format(floatval($order['profit']), 2) . '</td>';
        $html .= '</tr>';
    }
    
    $html .= '</tbody>';
    $html .= '</table>';
    
    // Generate mobile card layout
    $html .= '<div class="orders-log-cards">';
    foreach ($ordersLog as $index => $order) {
        $html .= '<div class="order-card selectable-card" onclick="selectOrderLogRow(' . $index . ', this)" data-order=\'' . htmlspecialchars(json_encode($order)) . '\'>';
        
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
        $html .= '<div>' . ($order['openPrice'] === 'N/A' ? '<span class="na-value">N/A</span>' : number_format(floatval($order['openPrice']), 2)) . '</div>';
        $html .= '<div>' . ($order['stopLoss'] === 'N/A' ? '<span class="na-value">N/A</span>' : number_format(floatval($order['stopLoss']), 2)) . '</div>';
        $html .= '<div>' . ($order['takeProfit'] === 'N/A' ? '<span class="na-value">N/A</span>' : number_format(floatval($order['takeProfit']), 2)) . '</div>';
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
        
        $html .= '<tr>';
        $html .= '<td>' . $symbol . '</td>';
        $html .= '<td>' . $type . '</td>';
        $html .= '<td>' . $lots . '</td>';
        $html .= '<td>' . $price . '</td>';
        $html .= '<td>' . $sl . '</td>';
        $html .= '<td>' . $tp . '</td>';
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

function refreshAccountLog() {
    global $timestamp;
    if (file_exists(ACCOUNT_LOG_FILE)) {
        $content = file_get_contents(ACCOUNT_LOG_FILE);
        $content = htmlspecialchars($content);
        // replace | with <br/>
        $content = str_replace('| ', '<br/>', $content);
        echo '<pre style="margin: 0; white-space: pre-wrap;">' . $content . '</pre>';
        //echo '<small class="timestamp">Last updated: ' . $timestamp . '</small>';
    } else {
        echo '<p class="error-message">Account log file not found.</p>';
    }
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
            echo json_encode([
                'value' => $accountProfit,
                'formatted' => $accountProfit !== null ? 
                    '<strong style="font-size: 1.2em;">otwarte: <span class="' . 
                    ((floatval($accountProfit) >= 0) ? 'profit-positive' : 'profit-negative') . 
                    '">' . htmlspecialchars($accountProfit) . '</span></strong>' :
                    '<strong style="color: #6c757d;">otwarte: N/A</strong>'
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
            
        case 'orders_log_list':
            $orders_log = getOrdersLogData();
            echo json_encode([
                'table' => generateOrdersLogTable($orders_log),
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
        case 'cancel_order':
        case 'remove_approved':
            if (!isset($_GET['row'])) {
                echo json_encode(['success' => false, 'message' => 'Row parameter required']);
                break;
            }
            
            $rowNumber = intval($_GET['row']);
            
            if ($action === 'remove_approved') {
                $approved_orders = getApprovedOrdersList();
                
                if ($rowNumber > 0 && $rowNumber <= count($approved_orders)) {
                    array_splice($approved_orders, $rowNumber - 1, 1);
                    file_put_contents(APPROVED_FILE, implode("\n", $approved_orders));
                    echo json_encode(['success' => true, 'message' => 'Approved order row ' . $rowNumber . ' removed']);
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
    <title>watchdog</title>
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
            if ($accountProfit !== null) {
                $profitClass = (floatval($accountProfit) >= 0) ? 'profit-positive' : 'profit-negative';
                echo '<strong style="font-size: 1.2em;">otwarte: <span class="' . $profitClass . '">' . htmlspecialchars($accountProfit) . '</span></strong>';
            } else {
                echo '<strong style="color: #6c757d;">otwarte: N/A</strong>';
            }
            ?>
        </div>
        
        <hr style="margin: 30px 0;">
        
        <h2>Account Log</h2>
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
        
        <div class="new-order-section">
            <h3>Add/Modify Order</h3>
            <form id="new-order-form" class="new-order-form">
                <div class="form-row">
                    <div class="form-group">
                        <label for="symbol">Symbol *</label>
                        <select id="symbol" name="symbol" required>
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
        
        <hr style="margin: 30px 0;">
        
        <h2 id="orders-list-heading">Review List (<?php $orders = getOrdersList(); echo count($orders); ?>)</h2>
        <div id="orders-list" class="content-section orders-list">
            <?php
            echo generateOrdersTable($orders, true);
            ?>
        </div>
        
        <button onclick="refreshOrdersList()" style="margin-top: 15px;">Refresh</button>
        
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
                order_history_log: { element: 'order-history-log', action: 'order_history_log', text: true, onSuccess: 'refreshProfits' }
            },
            actions: {
                add_p: { confirm: false, refresh: 'orders' },
                add_r: { confirm: false, refresh: 'orders' },
                cancel_order: { confirm: 'Are you sure you want to cancel and remove this order?', refresh: 'orders' },
                remove_approved: { confirm: 'Are you sure you want to remove this approved order?', refresh: 'approved' }
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
            ordersLog: () => refreshSection('orders_log', true),
            ordersList: () => refreshSection('orders_list', true),
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
            profits: () => {
                Promise.all([
                    utils.request('index.php?ajax=total_net_profit'),
                    utils.request('index.php?ajax=account_profit')
                ])
                .then(([total, account]) => {
                    utils.updateElement('total-net-profit-display', total.formatted + '<br/>' + account.formatted);
                })
                .catch(error => console.error('Error refreshing profits:', error));
            }
        };

        // Legacy function aliases for backward compatibility
        const refreshAccountLog = refresh.accountLog;
        const refreshOrdersLogList = refresh.ordersLog;
        const refreshOrdersList = refresh.ordersList;
        const refreshApprovedOrdersList = refresh.approvedOrders;
        const refreshOrderHistoryLog = refresh.orderHistoryLog;

        // Consolidated profit refresh
        function refreshProfits() {
            refresh.profits();
        }

        // Generic action handler
        function handleAction(actionKey, rowNumber) {
            const config = APP.actions[actionKey];
            if (config.confirm && !confirm(config.confirm)) return;
            
            utils.request(`index.php?ajax=${actionKey}&row=${rowNumber}`)
                .then(data => {
                    alert(data.success ? data.message : 'Error: ' + data.message);
                    if (data.success) {
                        if (config.refresh === 'approved') refresh.approvedOrders();
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

        // Order log row selection function
        function selectOrderLogRow(index, element) {
            // Remove previous selection
            document.querySelectorAll('.selectable-row, .selectable-card').forEach(el => {
                el.classList.remove('selected');
            });
            
            // Add selection to clicked element
            element.classList.add('selected');
            
            // Get order data
            const orderData = JSON.parse(element.getAttribute('data-order'));
            
            // Map order types
            const typeMapping = {
                'BUY': 'BUY',
                'SELL': 'SELL',
                'BUY LIMIT': 'BUYLIMIT',
                'SELL LIMIT': 'SELLLIMIT',
                'BUY STOP': 'BUYSTOP',
                'SELL STOP': 'SELLSTOP'
            };
            
            // Populate form fields
            const form = document.getElementById('new-order-form');
            if (form) {
                const symbolSelect = form.querySelector('#symbol');
                const typeSelect = form.querySelector('#orderType');
                const lotsInput = form.querySelector('#lots');
                const priceInput = form.querySelector('#price');
                const stopLossInput = form.querySelector('#stopLoss');
                const takeProfitInput = form.querySelector('#takeProfit');
                
                // Set symbol (add option if it doesn't exist)
                if (symbolSelect && orderData.symbol && orderData.symbol !== 'N/A') {
                    let optionExists = false;
                    for (let option of symbolSelect.options) {
                        if (option.value === orderData.symbol) {
                            optionExists = true;
                            break;
                        }
                    }
                    if (!optionExists) {
                        const newOption = new Option(orderData.symbol, orderData.symbol);
                        symbolSelect.add(newOption);
                    }
                    symbolSelect.value = orderData.symbol;
                }
                
                // Set type
                if (typeSelect && orderData.type) {
                    const mappedType = typeMapping[orderData.type.toUpperCase()] || orderData.type.toUpperCase();
                    typeSelect.value = mappedType;
                }
                
                // Set lots
                if (lotsInput && orderData.lots && orderData.lots !== 'N/A') {
                    lotsInput.value = orderData.lots;
                }
                
                // Set price
                if (priceInput && orderData.openPrice && orderData.openPrice !== 'N/A') {
                    priceInput.value = orderData.openPrice;
                }
                
                // Set stop loss
                if (stopLossInput && orderData.stopLoss && orderData.stopLoss !== 'N/A' && orderData.stopLoss !== '0') {
                    stopLossInput.value = orderData.stopLoss;
                }
                
                // Set take profit
                if (takeProfitInput && orderData.takeProfit && orderData.takeProfit !== 'N/A' && orderData.takeProfit !== '0') {
                    takeProfitInput.value = orderData.takeProfit;
                }
                
                // Scroll to form
                form.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }

        // Form and logs functions
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
            
            // Auto-refresh
            setInterval(() => {
                refresh.accountLog();
                refresh.ordersLog();
                refresh.orderHistoryLog();
            }, 1000);
        });
    </script>
</body>
</html>
