<?php
// Set content type
header('Content-Type: text/html; charset=utf-8');

// File path constants
const ORDERS_FILE = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/orders.txt';
const APPROVED_FILE = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/approved.txt';
const ACCOUNT_LOG_FILE = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/account_log.txt';
const ORDERS_LOG_FILE = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/orders_log.txt';

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
        
        $inDataSection = false;
        foreach ($lines as $line) {
            $line = trim($line);
            
            // Skip header lines and empty lines
            if (empty($line) || 
                strpos($line, '=== ORDERS LOG') === 0 || 
                strpos($line, '=== END ORDERS LOG') === 0 || 
                strpos($line, 'Total Orders:') === 0 ||
                strpos($line, 'Ticket | Type') === 0 ||
                strpos($line, '-------|------') === 0) {
                continue;
            }
            
            // Parse data line (pipe-separated values)
            if (strpos($line, '|') !== false) {
                $parts = array_map('trim', explode('|', $line));
                if (count($parts) >= 8) {
                    $ordersLog[] = array(
                        'ticket' => $parts[0],
                        'type' => $parts[1],
                        'symbol' => $parts[2],
                        'lots' => $parts[3],
                        'openPrice' => $parts[4],
                        'stopLoss' => $parts[5],
                        'takeProfit' => $parts[6],
                        'profit' => $parts[7],
                        'comment' => isset($parts[8]) ? $parts[8] : ''
                    );
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
 * @return string HTML for action buttons
 */
function generateActionButtons($rowNumber, $order) {
    $hasP = orderHasFlag($order, 'p');
    $hasR = orderHasFlag($order, 'r');
    
    $pButtonClass = $hasP ? 'btn-p-active' : 'btn-p-inactive';
    $rButtonClass = $hasR ? 'btn-r-active' : 'btn-r-inactive';
    
    return '<button onclick="handlePAction(' . $rowNumber . ')" class="action-button ' . $pButtonClass . '">P</button>' .
           '<button onclick="handleRAction(' . $rowNumber . ')" class="action-button ' . $rButtonClass . '">R</button>' .
           '<button onclick="handleCancelAction(' . $rowNumber . ')" class="action-button btn-cancel">Cancel</button>';
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
    $html .= '<th>Comment</th>';
    $html .= '</tr>';
    $html .= '</thead>';
    $html .= '<tbody>';
    
    foreach ($ordersLog as $order) {
        $html .= '<tr>';
        $html .= '<td>' . htmlspecialchars($order['ticket']) . '</td>';
        $html .= '<td>' . htmlspecialchars($order['type']) . '</td>';
        $html .= '<td>' . htmlspecialchars($order['symbol']) . '</td>';
        $html .= '<td>' . htmlspecialchars($order['lots']) . '</td>';
        $html .= '<td>' . htmlspecialchars($order['openPrice']) . '</td>';
        $html .= '<td>' . htmlspecialchars($order['stopLoss']) . '</td>';
        $html .= '<td>' . htmlspecialchars($order['takeProfit']) . '</td>';
        $html .= '<td class="' . (floatval($order['profit']) >= 0 ? 'profit-positive' : 'profit-negative') . '">' . htmlspecialchars($order['profit']) . '</td>';
        $html .= '<td>' . htmlspecialchars($order['comment']) . '</td>';
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
        $html .= '<div>' . htmlspecialchars($order['lots']) . '</div>';
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
        $html .= '<div>' . htmlspecialchars($order['openPrice']) . '</div>';
        $html .= '<div>' . htmlspecialchars($order['stopLoss']) . '</div>';
        $html .= '<div>' . htmlspecialchars($order['takeProfit']) . '</div>';
        $html .= '<div class="' . (floatval($order['profit']) >= 0 ? 'card-profit-positive' : 'card-profit-negative') . '">' . htmlspecialchars($order['profit']) . '</div>';
        $html .= '</div>';
        
        // Comment section (if exists)
        if (!empty(trim($order['comment']))) {
            $html .= '<div class="card-comment">';
            $html .= '<strong>Comment:</strong> ' . htmlspecialchars($order['comment']);
            $html .= '</div>';
        }
        
        $html .= '</div>'; // End order-card
    }
    $html .= '</div>'; // End orders-log-cards
    
    global $timestamp;
    $html .= '<small class="timestamp">Last updated: ' . $timestamp . '</small>';
    
    return $html;
}

/**
 * Generate HTML table for orders
 * @param array $orders Array of order strings
 * @param bool $showActions Whether to show action buttons
 * @return string HTML table
 */
function generateOrdersTable($orders, $showActions = false) {
    if (empty($orders)) {
        $message = $showActions ? 'No orders found or orders file not found.' : 'No approved orders found or approved orders file not found.';
        return '<p class="error-message">' . $message . '</p>';
    }
    
    $html = '<table class="table">';
    $html .= '<thead>';
    $html .= '<tr>';
    $html .= '<th>#</th>';
    $html .= '<th>ID</th>';
    $html .= '<th>Type</th>';
    if ($showActions) {
        $html .= '<th>Actions</th>';
    }
    $html .= '</tr>';
    $html .= '</thead>';
    $html .= '<tbody>';
    
    foreach ($orders as $index => $order) {
        $parts = explode(' ', trim($order));
        $orderId = isset($parts[0]) ? htmlspecialchars($parts[0]) : '';
        $type = isset($parts[1]) ? htmlspecialchars($parts[1]) : '';
        
        $html .= '<tr>';
        $html .= '<td>' . ($index + 1) . '</td>';
        $html .= '<td>' . $orderId . '</td>';
        $html .= '<td>' . $type . '</td>';
        if ($showActions) {
            $html .= '<td>' . generateActionButtons($index + 1, $order) . '</td>';
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
    if (file_exists(ACCOUNT_LOG_FILE)) {
        $content = file_get_contents(ACCOUNT_LOG_FILE);
        $content = htmlspecialchars($content);
        // replace | with <br/>
        $content = str_replace('| ', '<br/>', $content);
        echo '<pre style="margin: 0; white-space: pre-wrap;">' . $content . '</pre>';
        echo '<small class="timestamp">Last updated: ' . $timestamp . '</small>';
    } else {
        echo '<p class="error-message">Account log file not found.</p>';
    }
}

// For AJAX requests to refresh account log
if (isset($_GET['ajax']) && $_GET['ajax'] === 'account_log') {
    refreshAccountLog();
    exit; // Exit here for AJAX requests
}

// For AJAX requests to refresh orders list
if (isset($_GET['ajax']) && $_GET['ajax'] === 'orders_list') {
    $orders = getOrdersList();
    $response = array(
        'table' => generateOrdersTable($orders, true),
        'count' => count($orders)
    );
    echo json_encode($response);
    exit; // Exit here for AJAX requests
}

// For AJAX requests to refresh approved orders list
if (isset($_GET['ajax']) && $_GET['ajax'] === 'approved_orders_list') {
    $approved_orders = getApprovedOrdersList();
    $response = array(
        'table' => generateOrdersTable($approved_orders, false),
        'count' => count($approved_orders)
    );
    echo json_encode($response);
    exit; // Exit here for AJAX requests
}

// For AJAX requests to refresh orders log
if (isset($_GET['ajax']) && $_GET['ajax'] === 'orders_log_list') {
    $orders_log = getOrdersLogData();
    $response = array(
        'table' => generateOrdersLogTable($orders_log),
        'count' => count($orders_log)
    );
    echo json_encode($response);
    exit; // Exit here for AJAX requests
}

// For AJAX requests to add new orders
if (isset($_GET['ajax']) && $_GET['ajax'] === 'add_new_order' && isset($_GET['type'])) {
    $orderType = $_GET['type'];
    
    // Validate order type
    if ($orderType !== 'buy' && $orderType !== 'sell') {
        echo json_encode(['success' => false, 'message' => 'Invalid order type']);
        exit;
    }
    
    // Generate timestamp-based ID
    $orderId = time(); // Unix timestamp
    
    // Create new order string
    $newOrder = $orderId . ' ' . $orderType;
    
    // Ensure proper newline handling - check if file exists and ends with newline
    $needsNewlineBefore = false;
    if (file_exists(ORDERS_FILE)) {
        $existingContent = file_get_contents(ORDERS_FILE);
        if (!empty($existingContent) && substr($existingContent, -1) !== "\n") {
            $needsNewlineBefore = true;
        }
    }
    
    // Prepare the content to append
    $contentToAppend = ($needsNewlineBefore ? "\n" : '') . $newOrder . "\n";
    
    // Append to orders.txt file
    $result = file_put_contents(ORDERS_FILE, $contentToAppend, FILE_APPEND | LOCK_EX);
    
    if ($result !== false) {
        echo json_encode(['success' => true, 'message' => 'New ' . $orderType . ' order added with ID: ' . $orderId]);
    } else {
        echo json_encode(['success' => false, 'message' => 'Failed to add new order to file']);
    }
    exit;
}

// Unified function to handle adding flags (P or R) to orders or canceling orders
if (isset($_GET['ajax']) && in_array($_GET['ajax'], ['add_p', 'add_r', 'cancel_order']) && isset($_GET['row'])) {
    $rowNumber = intval($_GET['row']);
    $orders = getOrdersList();
    
    if ($rowNumber > 0 && $rowNumber <= count($orders)) {
        $orderIndex = $rowNumber - 1;
        
        if ($_GET['ajax'] === 'cancel_order') {
            // Remove the order from the array
            array_splice($orders, $orderIndex, 1);
            
            // Write back to file
            $orders_file = ORDERS_FILE;
            file_put_contents($orders_file, implode("\n", $orders));
            echo json_encode(['success' => true, 'message' => 'Order row ' . $rowNumber . ' canceled and removed']);
        } else {
            // Handle adding flags (P or R)
            $flag = ($_GET['ajax'] === 'add_p') ? 'p' : 'r';
            $flagName = strtoupper($flag);
            
            if (!orderHasFlag($orders[$orderIndex], $flag)) {
                // Add flag to the order
                $orders[$orderIndex] .= ' ' . $flag;
                
                // Check if order now has both flags
                if (orderHasBothFlags($orders[$orderIndex])) {
                    // Move order to approved.txt
                    if (moveOrderToApproved($orders[$orderIndex])) {
                        // Remove from orders.txt
                        array_splice($orders, $orderIndex, 1);
                        
                        // Write back to orders file
                        $orders_file = ORDERS_FILE;
                        file_put_contents($orders_file, implode("\n", $orders));
                        
                        echo json_encode(['success' => true, 'message' => $flagName . ' added to row ' . $rowNumber . '. Order moved to approved list (both P and R flags set)']);
                    } else {
                        echo json_encode(['success' => false, 'message' => 'Failed to move order to approved list']);
                    }
                } else {
                    // Just update the orders file
                    $orders_file = ORDERS_FILE;
                    file_put_contents($orders_file, implode("\n", $orders));
                    echo json_encode(['success' => true, 'message' => $flagName . ' added to row ' . $rowNumber]);
                }
            } else {
                echo json_encode(['success' => false, 'message' => $flagName . ' already exists in row ' . $rowNumber]);
            }
        }
    } else {
        echo json_encode(['success' => false, 'message' => 'Invalid row number']);
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
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        button {
            background-color: #007cba;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px;
        }
        button:hover {
            background-color: #005a87;
        }
        #response {
            margin-top: 20px;
            padding: 15px;
            border-radius: 5px;
            min-height: 20px;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .loading {
            background-color: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }
        .content-section {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            text-align: left;
            font-size: 14px;
        }
        .account-log {
            border-left: 4px solid #007cba;
            font-family: 'Courier New', monospace;
        }
        .orders-list {
            border-left: 4px solid #28a745;
            font-family: Arial, sans-serif;
        }
        .approved-orders {
            border-left: 4px solid #ffc107;
            font-family: Arial, sans-serif;
        }
        .orders-log {
            border-left: 4px solid #6f42c1;
            font-family: Arial, sans-serif;
        }
        .orders-log-table {
            font-size: 12px;
        }
        .orders-log-table th, .orders-log-table td {
            padding: 6px;
            text-align: left;
        }
        .orders-log-table th:nth-child(2), .orders-log-table td:nth-child(2) {
            width: 60px !important;
            min-width: 60px !important;
            max-width: 60px !important;
        }
        
        /* Mobile card layout for orders log */
        .orders-log-cards {
            display: none;
        }
        
        .order-card {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            margin-bottom: 15px;
            padding: 12px;
        }
        
        .card-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 8px;
            margin-bottom: 8px;
            font-size: 12px;
        }
        
        .card-row.labels {
            font-weight: bold;
            color: #6c757d;
            font-size: 11px;
            text-transform: uppercase;
        }
        
        .card-row.values {
            font-size: 13px;
            font-weight: 500;
        }
        
        .card-comment {
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid #dee2e6;
            font-size: 12px;
            color: #6c757d;
        }
        
        .card-comment strong {
            color: #495057;
        }
        
        .card-profit-positive {
            color: #28a745;
            font-weight: bold;
        }
        
        .card-profit-negative {
            color: #dc3545;
            font-weight: bold;
        }
        
        /* on small screen show orders as cards */
        @media (max-width: 768px) {
            .orders-log-table {
                display: none;
            }
            .orders-log-cards {
                display: block;
            }
        }

        .profit-positive {
            color: #28a745;
            font-weight: bold;
        }
        .profit-negative {
            color: #dc3545;
            font-weight: bold;
        }
        .action-button {
            color: white;
            border: none;
            padding: 4px 8px;
            margin: 2px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
        }
        .btn-p-active { background-color: #28a745; }
        .btn-p-inactive { background-color: #6c757d; }
        .btn-r-active { background-color: #28a745; }
        .btn-r-inactive { background-color: #6c757d; }
        .btn-cancel { background-color: #dc3545; }
        .table {
            width: 100%;
            border-collapse: collapse;
            margin: 0;
        }
        .table th, .table td {
            border: 1px solid #dee2e6;
            padding: 8px;
            text-align: left;
        }
        .table th:nth-child(1), .table td:nth-child(1) {
            width: 50px;
            min-width: 50px;
        }
        .table th:nth-child(2), .table td:nth-child(2) {
            width: 120px;
            min-width: 120px;
        }
        .table thead tr {
            background-color: #e9ecef;
        }
        .table tbody tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        .error-message {
            color: #dc3545;
        }
        .timestamp {
            color: #666;
            display: block;
            margin-top: 10px;
            font-size: 12px;
        }
        .new-order-section {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #17a2b8;
        }
        .new-order-form {
            display: flex;
            align-items: center;
            gap: 20px;
            justify-content: center;
        }
        .order-type-selection {
            display: flex;
            gap: 15px;
        }
        .order-type-selection label {
            display: flex;
            align-items: center;
            gap: 5px;
            cursor: pointer;
            font-weight: normal;
        }
        .order-type-selection input[type="radio"] {
            margin: 0;
        }
        .add-order-btn {
            background-color: #17a2b8;
            color: white;
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .add-order-btn:hover {
            background-color: #138496;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>pora zarobić :) v2.0</h1>
        <hr style="margin: 30px 0;">
        
        <h2>Account Log Information</h2>
        <div id="account-log" class="content-section account-log">
            <?php refreshAccountLog(); ?>
        </div>
        
        <button onclick="refreshAccountLog()" style="margin-top: 15px;">Refresh Account Log</button>
        
        <hr style="margin: 30px 0;">
        
        <h2 id="orders-list-heading">Orders List (<?php $orders = getOrdersList(); echo count($orders); ?>)</h2>
        <div id="orders-list" class="content-section orders-list">
            <?php
            echo generateOrdersTable($orders, true);
            ?>
        </div>
        
        <button onclick="refreshOrdersList()" style="margin-top: 15px;">Refresh Orders List</button>
        
        <div class="new-order-section" style="margin-top: 20px;">
            <h3>Add New Order</h3>
            <form id="new-order-form" class="new-order-form">
                <div class="order-type-selection">
                    <label>
                        <input type="radio" name="orderType" value="buy" checked> Buy
                    </label>
                    <label>
                        <input type="radio" name="orderType" value="sell"> Sell
                    </label>
                </div>
                <button type="submit" class="add-order-btn">Add Order</button>
            </form>
        </div>
        
        <hr style="margin: 30px 0;">
        
        <h2 id="approved-orders-heading">Approved Orders (<?php $approved_orders = getApprovedOrdersList(); echo count($approved_orders); ?>)</h2>
        <div id="approved-orders-list" class="content-section approved-orders">
            <?php
            echo generateOrdersTable($approved_orders, false);
            ?>
        </div>
        
        <button onclick="refreshApprovedOrdersList()" style="margin-top: 15px;">Refresh Approved Orders</button>
        
        <hr style="margin: 30px 0;">
        
        <h2 id="orders-log-heading">Orders Log (<?php $orders_log = getOrdersLogData(); echo count($orders_log); ?>)</h2>
        <div id="orders-log-list" class="content-section orders-log">
            <?php
            echo generateOrdersLogTable($orders_log);
            ?>
        </div>
        
        <button onclick="refreshOrdersLogList()" style="margin-top: 15px;">Refresh Orders Log</button>
    </div>

    <script>       
        function refreshAccountLog() {
            const accountLogDiv = document.getElementById('account-log');
            const originalContent = accountLogDiv.innerHTML;
            accountLogDiv.innerHTML = '<p style="color: #856404;">Refreshing account log...</p>';
            
            fetch('index.php?ajax=account_log', {
                method: 'GET'
            })
            .then(response => response.text())
            .then(data => {
                accountLogDiv.innerHTML = data;
            })
            .catch(error => {
                accountLogDiv.innerHTML = '<p style="color: #dc3545;">Error refreshing account log: ' + error.message + '</p>';
            });
        }
        function refreshOrdersList() {
            const ordersListDiv = document.getElementById('orders-list');
            const ordersListHeading = document.getElementById('orders-list-heading');
            const originalContent = ordersListDiv.innerHTML;
            ordersListDiv.innerHTML = '<p style="color: #856404;">Refreshing orders list...</p>';

            fetch('index.php?ajax=orders_list', {
                method: 'GET'
            })
            .then(response => response.json())
            .then(data => {
                ordersListDiv.innerHTML = data.table;
                ordersListHeading.textContent = 'Orders List (' + data.count + ')';
            })
            .catch(error => {
                ordersListDiv.innerHTML = '<p style="color: #dc3545;">Error refreshing orders list: ' + error.message + '</p>';
            });
        }

        function refreshApprovedOrdersList() {
            const approvedOrdersListDiv = document.getElementById('approved-orders-list');
            const approvedOrdersHeading = document.getElementById('approved-orders-heading');
            const originalContent = approvedOrdersListDiv.innerHTML;
            approvedOrdersListDiv.innerHTML = '<p style="color: #856404;">Refreshing approved orders list...</p>';

            fetch('index.php?ajax=approved_orders_list', {
                method: 'GET'
            })
            .then(response => response.json())
            .then(data => {
                approvedOrdersListDiv.innerHTML = data.table;
                approvedOrdersHeading.textContent = 'Approved Orders (' + data.count + ')';
            })
            .catch(error => {
                approvedOrdersListDiv.innerHTML = '<p style="color: #dc3545;">Error refreshing approved orders list: ' + error.message + '</p>';
            });
        }

        function refreshOrdersLogList() {
            const ordersLogListDiv = document.getElementById('orders-log-list');
            const ordersLogHeading = document.getElementById('orders-log-heading');
            const originalContent = ordersLogListDiv.innerHTML;
            ordersLogListDiv.innerHTML = '<p style="color: #856404;">Refreshing orders log...</p>';

            fetch('index.php?ajax=orders_log_list', {
                method: 'GET'
            })
            .then(response => response.json())
            .then(data => {
                ordersLogListDiv.innerHTML = data.table;
                ordersLogHeading.textContent = 'Orders Log (' + data.count + ')';
            })
            .catch(error => {
                ordersLogListDiv.innerHTML = '<p style="color: #dc3545;">Error refreshing orders log: ' + error.message + '</p>';
            });
        }

        function handleFlagAction(flag, rowNumber) {
            const flagName = flag.toUpperCase();
            
            fetch('index.php?ajax=add_' + flag + '&row=' + rowNumber, {
                method: 'GET'
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    refreshOrdersList();
                    // If order was moved to approved list, refresh approved orders too
                    if (data.message.includes('moved to approved list')) {
                        refreshApprovedOrdersList();
                    }
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(error => {
                alert('Error adding ' + flagName + ': ' + error.message);
                console.error('Error:', error);
            });
        }
        
        function handlePAction(rowNumber) {
            handleFlagAction('p', rowNumber);
        }
        
        function handleRAction(rowNumber) {
            handleFlagAction('r', rowNumber);
        }
        
        function handleCancelAction(rowNumber) {
            if (confirm('Are you sure you want to cancel and remove this order?')) {
                fetch('index.php?ajax=cancel_order&row=' + rowNumber, {
                    method: 'GET'
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        refreshOrdersList();
                    } else {
                        alert('Error: ' + data.message);
                    }
                })
                .catch(error => {
                    alert('Error canceling order: ' + error.message);
                    console.error('Error:', error);
                });
            }
        }
        
        function addNewOrder(orderType) {
            fetch('index.php?ajax=add_new_order&type=' + orderType, {
                method: 'GET'
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    refreshOrdersList();
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(error => {
                alert('Error adding new order: ' + error.message);
                console.error('Error:', error);
            });
        }
        
        // Handle new order form submission
        document.addEventListener('DOMContentLoaded', function() {
            const newOrderForm = document.getElementById('new-order-form');
            if (newOrderForm) {
                newOrderForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const selectedType = document.querySelector('input[name="orderType"]:checked');
                    if (selectedType) {
                        addNewOrder(selectedType.value);
                    } else {
                        alert('Please select an order type');
                    }
                });
            }
        });
    </script>
</body>
</html>
