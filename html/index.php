<?php
// Include login system
require_once '/home/ubuntu/repo/login.php';

// Require authentication before accessing the main application
requireLogin();

// Include index-main.php from ~/repo
include '/home/ubuntu/repo/index-main.php';
?>