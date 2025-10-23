<?php
/**
 * Trading Application Configuration
 * Centralized configuration for all file paths and settings
 */

// Base paths
const BASE_MFOREX_PATH = '/home/ubuntu/.wine/drive_c/Program Files (x86)/mForex Trader';
const MQL4_FILES_PATH = BASE_MFOREX_PATH . '/MQL4/Files';
const MQL4_LOGS_PATH = BASE_MFOREX_PATH . '/MQL4/Logs';
const MAIN_LOGS_PATH = BASE_MFOREX_PATH . '/logs';

// File definitions - easier to maintain
const FILES = [
    'orders' => 'orders.txt',
    'approved' => 'approved.txt',
    'modified' => 'modified.txt',
    'account_log' => 'account_log.txt',
    'orders_log' => 'orders_log.txt',
    'order_history_log' => 'order_history_log.txt',
    'dropped' => 'dropped.txt'
];

// Generate full file paths
function getFilePath($fileKey) {
    if (!isset(FILES[$fileKey])) {
        throw new InvalidArgumentException("Unknown file key: $fileKey");
    }
    return MQL4_FILES_PATH . '/' . FILES[$fileKey];
}

// Legacy constants for backward compatibility
const ORDERS_FILE = MQL4_FILES_PATH . '/orders.txt';
const APPROVED_FILE = MQL4_FILES_PATH . '/approved.txt';
const MODIFIED_FILE = MQL4_FILES_PATH . '/modified.txt';
const ACCOUNT_LOG_FILE = MQL4_FILES_PATH . '/account_log.txt';
const ORDERS_LOG_FILE = MQL4_FILES_PATH . '/orders_log.txt';
const ORDER_HISTORY_LOG_FILE = MQL4_FILES_PATH . '/order_history_log.txt';
const DROPPED_FILE = MQL4_FILES_PATH . '/dropped.txt';
const LOGS_DIR_MQL4 = MQL4_LOGS_PATH;
const LOGS_DIR_MAIN = MAIN_LOGS_PATH;

// Application settings
const APP_TIMEZONE = 'Europe/Warsaw';
const APP_TITLE = 'watchdog';

// Order types configuration
const VALID_ORDER_TYPES = ['buy', 'sell', 'buylimit', 'selllimit', 'buystop', 'sellstop'];
const SYMBOLS = ['EURUSD', 'US100.f'];

?>