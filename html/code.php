<?php

// Define base paths as constants
define('BASE_DIR', '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/');
define('WAITING_DIR', BASE_DIR . 'php_waiting');
define('PENDING_DIR', BASE_DIR . 'php_pending');
define('ACCOUNT_LOG_FILE', BASE_DIR . 'account_log.txt');

// Define regex pattern for approval files
define('APPROVAL_FILE_PATTERN', '/_[rp]\.txt$/');

// Generic function to count order files in a directory
function countOrderFiles($directory) {
    $count = 0;
    if (is_dir($directory)) {
        $files = scandir($directory);
        foreach ($files as $file) {
            // Count only order files, not approval files (_r or _p suffix)
            if ($file !== '.' && $file !== '..' && !preg_match(APPROVAL_FILE_PATTERN, $file)) {
                $count++;
            }
        }
    }
    return $count;
}

// Handle cancel order request
function handleCancelOrder() {
    if (isset($_POST['cancel_order'])) {
        // Clear any output buffers and disable error reporting to avoid contaminating JSON response
        while (ob_get_level()) {
            ob_end_clean();
        }
        error_reporting(0);
        
        $filename = isset($_POST['filename']) ? $_POST['filename'] : '';
        $success = false;
        
        if (!empty($filename)) {
            $original_file_path = WAITING_DIR . '/' . $filename;
            
            if (file_exists($original_file_path)) {
                // Remove the original file
                $success = unlink($original_file_path);
                
                // Also remove any approval files
                $file_info = pathinfo($filename);
                $base_name = $file_info['filename'];
                $extension = isset($file_info['extension']) ? '.' . $file_info['extension'] : '';
                
                $rafal_approval_file = WAITING_DIR . '/' . $base_name . '_r' . $extension;
                $piotr_approval_file = WAITING_DIR . '/' . $base_name . '_p' . $extension;
                
                if (file_exists($rafal_approval_file)) {
                    unlink($rafal_approval_file);
                }
                if (file_exists($piotr_approval_file)) {
                    unlink($piotr_approval_file);
                }
            }
        }
        
        header('Content-Type: application/json');
        echo json_encode(['success' => $success]);
        exit();
    }
}

// Handle password verification AJAX request
function handlePasswordVerification() {
    if (isset($_POST['check_password'])) {
        // Clear any output buffers and disable error reporting to avoid contaminating JSON response
        while (ob_get_level()) {
            ob_end_clean();
        }
        error_reporting(0);
        
        $user = $_POST['user'];
        $password = $_POST['password'];
        $filename = isset($_POST['filename']) ? $_POST['filename'] : '';
        
        $password_file = '';
        if ($user === 'rafal') {
            $password_file = BASE_DIR . 'pass_r.txt';
        } elseif ($user === 'piotr') {
            $password_file = BASE_DIR . 'pass_p.txt';
        }
        
        $correct_password = '';
        if (file_exists($password_file)) {
            $correct_password = trim(file_get_contents($password_file));
        }
        
        $success = ($password === $correct_password);
        
        // If password is correct, create a file with user suffix next to the order file
        if ($success && !empty($filename)) {
            $original_file_path = WAITING_DIR . '/' . $filename;
            
            if (file_exists($original_file_path)) {
                // Create filename with user suffix
                $file_info = pathinfo($filename);
                $base_name = $file_info['filename'];
                $extension = isset($file_info['extension']) ? '.' . $file_info['extension'] : '';
                $user_suffix = ($user === 'rafal') ? '_r' : '_p';
                $approval_filename = $base_name . $user_suffix . $extension;
                $approval_file_path = WAITING_DIR . '/' . $approval_filename;
                
                // Create approval file with timestamp and user info
                $approval_content = "Approved by: $user\nTimestamp: " . date('Y-m-d H:i:s') . "\nOriginal file: $filename";
                file_put_contents($approval_file_path, $approval_content);
            }
        }
        
        header('Content-Type: application/json');
        echo json_encode(['success' => $success]);
        exit();
    }
}

// Display account log content
function displayAccountLog() {
    $original_file = ACCOUNT_LOG_FILE;
    
    if (file_exists($original_file) && is_readable($original_file)) {
        echo nl2br(htmlspecialchars(file_get_contents($original_file)));
    } else {
        echo "File not found.";
    }
}

// Extract account time from account log
function getAccountTime() {
    $original_file = ACCOUNT_LOG_FILE;
    
    if (file_exists($original_file) && is_readable($original_file)) {
        $content = file_get_contents($original_file);
        // Look for timestamp pattern like "2025.10.17 21:59:58"
        if (preg_match('/(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})/', $content, $matches)) {
            return $matches[1];
        }
    }
    return "N/A";
}

// Calculate and display time difference with color coding
function getTimeDifferenceDisplay() {
    $systemTime = time(); // Get current Unix timestamp
    $accountTime = getAccountTime();
    
    if ($accountTime === "N/A") {
        return '<span style="color: red;">Account time not available</span>';
    }
    
    // Convert account time format from "2025.10.17 21:59:58" to "2025-10-17 21:59:58"
    $accountTimeFormatted = str_replace('.', '-', $accountTime);
    
    // Convert account time to Unix timestamp (assuming account time is in UTC)
    $accountTimestamp = strtotime($accountTimeFormatted . ' CEST');
    
    // Calculate difference
    $timeDiff = $systemTime - $accountTimestamp;
    
    $color = (abs($timeDiff) > 30) ? 'red' : 'black';
    return '<span style="color: ' . $color . ';">' . $timeDiff . ' seconds</span>';
}

// Count waiting orders in php_waiting folder
function countWaitingOrders() {
    return countOrderFiles(WAITING_DIR);
}

// Count pending orders in php_pending folder
function countPendingOrders() {
    return countOrderFiles(PENDING_DIR);
}

// Display waiting orders from php_orders folder
function displayWaitingOrders() {
    if (is_dir(WAITING_DIR)) {
        $files = scandir(WAITING_DIR);
        foreach ($files as $file) {
            // do not display approval files
            if ($file !== '.' && $file !== '..' && !preg_match('/_[rp]\.txt$/', $file)) {
                // Check if approval files exist
                $file_info = pathinfo($file);
                $base_name = $file_info['filename'];
                $extension = isset($file_info['extension']) ? '.' . $file_info['extension'] : '';
                
                $rafal_approval_file = WAITING_DIR . '/' . $base_name . '_r' . $extension;
                $piotr_approval_file = WAITING_DIR . '/' . $base_name . '_p' . $extension;
                
                $rafal_approved = file_exists($rafal_approval_file);
                $piotr_approved = file_exists($piotr_approval_file);
                
                // If both approvals exist, move files to pending folder
                if ($rafal_approved && $piotr_approved) {
                    // Create pending directory if it doesn't exist
                    if (!is_dir(PENDING_DIR)) {
                        mkdir(PENDING_DIR, 0755, true);
                    }
                    
                    $source_path = WAITING_DIR . '/' . $file;
                    $target_path = PENDING_DIR . '/' . $file;
                    
                    // Move the original file
                    if (file_exists($source_path) && rename($source_path, $target_path)) {
                        chmod($target_path, 0666);
                        
                        // Also move the approval files
                        $rafal_target = PENDING_DIR . '/' . $base_name . '_r' . $extension;
                        $piotr_target = PENDING_DIR . '/' . $base_name . '_p' . $extension;

                        if (file_exists($rafal_approval_file)) {
                            rename($rafal_approval_file, $rafal_target);
                            chmod($rafal_target, 0666);
                        }
                        if (file_exists($piotr_approval_file)) {
                            rename($piotr_approval_file, $piotr_target);
                            chmod($piotr_target, 0666);
                        }
                        
                        // Skip displaying this file since it's been moved
                        continue;
                    }
                }
                
                $rafal_class = $rafal_approved ? 'user-button approved' : 'user-button';
                $piotr_class = $piotr_approved ? 'user-button approved' : 'user-button';
                
                echo '<h3 class="file-name">' . htmlspecialchars($file) . ' ';
                echo '<button class="' . $rafal_class . '" onclick="checkPassword(\'' . $file . '\', \'rafal\', this)">Rafal</button>';
                echo '<button class="' . $piotr_class . '" onclick="checkPassword(\'' . $file . '\', \'piotr\', this)">Piotr</button>';
                echo '<button class="user-button cancel" onclick="cancelOrder(\'' . $file . '\', this)">Cancel</button>';
                echo '</h3>';
                echo '<div class="file-content">' . nl2br(htmlspecialchars(file_get_contents(WAITING_DIR . '/' . $file))) . '</div>';
            }
        }
    } else {
        echo "Directory not found.";
    }
}

// Handle GET/POST requests and display messages
function handleRequests() {
    // Display success messages from GET parameters
    if (isset($_GET['created'])) {
        echo '<div style="color: green; margin-top: 10px;">File created successfully: ' . htmlspecialchars($_GET['created']) . '</div>';
    }

    if (isset($_POST['create_order'])) {
        $current_date = date('Y-m-d_H-i-s');
        $filename = $current_date . '.txt';
        $filepath = WAITING_DIR . '/' . $filename;
        $order_type = isset($_POST['order_type']) ? $_POST['order_type'] : 'none';
        $content = $order_type;

        // Create directory if it doesn't exist
        if (!is_dir(WAITING_DIR)) {
            mkdir(WAITING_DIR, 0755, true);
        }
        
        // Create the file
        if (file_put_contents($filepath, $content) !== false) {
            echo '<div style="color: green; margin-top: 10px;">File created successfully: ' . htmlspecialchars($filename) . '</div>';
        } else {
            echo '<div style="color: red; margin-top: 10px;">Error creating file.</div>';
        }
    }
}

// Display pending orders
function displayPendingOrders() {
    if (is_dir(PENDING_DIR)) {
        $files = scandir(PENDING_DIR);
        $found_files = false;
        foreach ($files as $file) {
            // Do not display approval files (_r or _p suffix)
            if ($file !== '.' && $file !== '..' && !preg_match('/_[rp]\.txt$/', $file)) {
                $found_files = true;
                echo '<h4>' . htmlspecialchars($file) . '</h4>';
                echo '<div class="file-content">' . nl2br(htmlspecialchars(file_get_contents(PENDING_DIR . '/' . $file))) . '</div>';
            }
        }
        if (!$found_files) {
            echo "No pending files found.";
        }
    } else {
        echo "Directory not found.";
    }
}

// Handle cancel and password verification first (before any HTML output)
handleCancelOrder();
handlePasswordVerification();

?>
