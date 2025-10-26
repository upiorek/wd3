<?php
session_start();

/**
 * Simple Login System
 * Uses password files for authentication
 */

// Password file paths
define('PASS_P_FILE', '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/pass_p.txt');
define('PASS_R_FILE', '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader/MQL4/Files/pass_r.txt');

// Session timeout (24 hours)
define('SESSION_TIMEOUT', 24 * 60 * 60);

/**
 * Read password from file
 * @param string $file_path Path to password file
 * @return string|null Password or null if file not found
 */
function readPasswordFromFile($file_path) {
    if (file_exists($file_path)) {
        return trim(file_get_contents($file_path));
    }
    return null;
}

/**
 * Validate login credentials
 * @param string $password Provided password
 * @return string|false Returns 'P' if pass_p password, 'R' if pass_r password, false if invalid
 */
function validateLogin($password) {
    $passP = readPasswordFromFile(PASS_P_FILE);
    $passR = readPasswordFromFile(PASS_R_FILE);
    
    // Check if password matches pass_p.txt
    if ($passP !== null && $password === $passP) {
        return 'P';
    }
    
    // Check if password matches pass_r.txt
    if ($passR !== null && $password === $passR) {
        return 'R';
    }
    
    return false;
}

/**
 * Check if user is logged in
 * @return bool True if user is authenticated
 */
function isLoggedIn() {
    // Check if session exists and is not expired
    if (!isset($_SESSION['logged_in']) || $_SESSION['logged_in'] !== true) {
        return false;
    }
    
    // Check session timeout
    if (isset($_SESSION['login_time']) && (time() - $_SESSION['login_time']) > SESSION_TIMEOUT) {
        session_destroy();
        return false;
    }
    
    return true;
}

/**
 * Get the user type (P or R)
 * @return string|null User type or null if not logged in
 */
function getUserType() {
    if (isLoggedIn() && isset($_SESSION['user_type'])) {
        return $_SESSION['user_type'];
    }
    return null;
}

/**
 * Require login - redirect to login form if not authenticated
 */
function requireLogin() {
    if (!isLoggedIn()) {
        showLoginForm();
        exit;
    }
}

/**
 * Process login attempt
 */
function processLogin() {
    if (isset($_POST['password']) && !empty($_POST['password'])) {
        $password = $_POST['password'];
        
        $userType = validateLogin($password);
        if ($userType !== false) {
            $_SESSION['logged_in'] = true;
            $_SESSION['login_time'] = time();
            $_SESSION['user_type'] = $userType; // Store which password was used
            // Redirect to prevent form resubmission
            header('Location: ' . $_SERVER['PHP_SELF']);
            exit;
        } else {
            return 'Invalid password. Please try again.';
        }
    }
    return null;
}

/**
 * Logout user
 */
function logout() {
    session_destroy();
    header('Location: ' . $_SERVER['PHP_SELF']);
    exit;
}

/**
 * Display login form
 * @param string|null $error Error message to display
 */
function showLoginForm($error = null) {
    ?>
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - Watchdog Trading System</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                margin: 0;
                padding: 0;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .login-container {
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
                max-width: 400px;
                width: 100%;
                text-align: center;
            }
            
            .login-header {
                margin-bottom: 30px;
            }
            
            .login-header h1 {
                color: #333;
                margin: 0 0 10px 0;
                font-size: 28px;
                font-weight: 600;
            }
            
            .login-header p {
                color: #666;
                margin: 0;
                font-size: 14px;
            }
            
            .login-form {
                margin: 30px 0;
            }
            
            .form-group {
                margin-bottom: 20px;
                text-align: left;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: 500;
                font-size: 14px;
            }
            
            .form-group input {
                width: 100%;
                padding: 12px 16px;
                border: 2px solid #e1e5e9;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s ease;
                box-sizing: border-box;
            }
            
            .form-group input:focus {
                outline: none;
                border-color: #007bff;
                box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
            }
            
            .login-button {
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            
            .login-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0, 123, 255, 0.3);
            }
            
            .login-button:active {
                transform: translateY(0);
            }
            
            .error-message {
                background: #fff5f5;
                color: #c53030;
                padding: 12px 16px;
                border-radius: 8px;
                border-left: 4px solid #e53e3e;
                margin-bottom: 20px;
                text-align: left;
                font-size: 14px;
            }
            
            .login-footer {
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e1e5e9;
                font-size: 12px;
                color: #999;
            }
            
            @media (max-width: 480px) {
                .login-container {
                    margin: 20px;
                    padding: 30px 20px;
                }
                
                .login-header h1 {
                    font-size: 24px;
                }
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-header">
                <h1>🔒 Login</h1>
                <p>Enter your password to access the watchdog</p>
            </div>
            
            <?php if ($error): ?>
                <div class="error-message">
                    <?php echo htmlspecialchars($error); ?>
                </div>
            <?php endif; ?>
            
            <form method="POST" class="login-form">
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password" required autofocus>
                </div>
                
                <button type="submit" class="login-button">
                    Login
                </button>
            </form>
            
            <div class="login-footer">
                Watchdog Trading System &copy; <?php echo date('Y'); ?>
            </div>
        </div>
        
        <script>
            // Auto-focus password field
            document.addEventListener('DOMContentLoaded', function() {
                const passwordField = document.getElementById('password');
                if (passwordField) {
                    passwordField.focus();
                }
            });
        </script>
    </body>
    </html>
    <?php
}

// Handle logout request
if (isset($_GET['logout'])) {
    logout();
}

// Process login form submission
$loginError = null;
if (isset($_SERVER['REQUEST_METHOD']) && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $loginError = processLogin();
}

// Export functions for use in other files
if (!function_exists('requireLogin')) {
    // Functions are already defined above
}
?>