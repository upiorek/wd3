<?php require_once 'code.php'; ?>

<!DOCTYPE html>
<html>
<head>
    <title>Hello World</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" type="text/css" href="styles.css">
    <script src="code.js"></script>
    <script>
    // Cancel order function
    function cancelOrder(filename, button) {
        if (confirm('Are you sure you want to cancel the order: ' + filename + '?')) {
            // Create FormData object
            const formData = new FormData();
            formData.append('cancel_order', '1');
            formData.append('filename', filename);
            
            // Send AJAX request
            fetch('', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Order cancelled successfully');
                    // Reload the page to update the order count and list
                    window.location.reload();
                } else {
                    alert('Failed to cancel order');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error cancelling order');
            });
        }
    }
    </script>
</head>
<body>
    <h1>Pora zarobic! :) v1.3</h1>
    
    <script>
    // Update server time every second
    function updateTime() {
        const now = new Date();
        const timeString = now.getFullYear() + '-' + 
                          String(now.getMonth() + 1).padStart(2, '0') + '-' + 
                          String(now.getDate()).padStart(2, '0') + ' ' +
                          String(now.getHours()).padStart(2, '0') + ':' + 
                          String(now.getMinutes()).padStart(2, '0') + ':' + 
                          String(now.getSeconds()).padStart(2, '0');
        const timeElement = document.getElementById('current-time');
        if (timeElement) {
            timeElement.textContent = timeString;
        }
    }
    
    // Update account log data via AJAX
    function updateAccountLog() {
        const formData = new FormData();
        formData.append('get_account_log', '1');
        
        fetch('', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Update account time
            const accountTimeElement = document.getElementById('account-time');
            if (accountTimeElement) {
                accountTimeElement.innerHTML = data.accountTime;
            }
            
            // Update time difference
            const timeDifferenceElement = document.getElementById('time-difference');
            if (timeDifferenceElement) {
                timeDifferenceElement.innerHTML = data.timeDifference;
            }
            
            // Update account log content
            const accountLogElement = document.getElementById('account-log');
            if (accountLogElement) {
                accountLogElement.innerHTML = data.accountLogContent;
            }
        })
        .catch(error => {
            console.error('Error updating account log:', error);
        });
    }
    
    // Wait for DOM to be ready before starting the timers
    document.addEventListener('DOMContentLoaded', function() {
        // Update time immediately and then every second
        updateTime();
        setInterval(updateTime, 1000);
    });
    </script>
    
    <div class="content-box">
        <div class="file-content">
            <?php $systemTime = date('Y-m-d H:i:s'); $accountTime = getAccountTime(); ?>
            <h2>system time: <span id="current-time"><?php echo $systemTime; ?></span></h2>
            <h2>account time: <span id="account-time"><?php echo getAccountTime(); ?></span></h2>
            <h2>time difference: <span id="time-difference"><?php echo getTimeDifferenceDisplay(); ?></span></h2>
            <h2>account info:</h2>
            <div id="account-log"><?php displayAccountLog(); ?></div>
        </div>

    	<!--- orders that need review --->
        <div class="file-content">
            <h2>orders waiting for approval - <?php echo countWaitingOrders(); ?> orders</h2>
            <?php displayWaitingOrders(); ?>
        </div>

        <!-- button and dropdown -->
        <form method="post" class="button-form" style="display: flex; align-items: center; gap: 10px; justify-content: center;">
            <select name="order_type" style="padding: 15px; border-radius: 8px; border: 1px solid #ccc; font-size: 18px; min-height: 50px;">
                <option value="none" selected>none</option>
                <option value="buy">buy</option>
                <option value="buy stop">buy stop</option>
                <option value="buy limit">buy limit</option>
                <option value="sell">sell</option>
                <option value="sell stop">sell stop</option>
                <option value="sell limit">sell limit</option>
            </select>
            <button type="submit" name="create_order" class="create-button">Create New Order</button>
        </form>
        <div class="content-box">
            <?php handleRequests(); ?>
        </div>

	<!-- orders to be executed by mt4, now they are pending -->
        <div class="file-content">
            <h2>pending orders - not executed yet - <?php echo countPendingOrders(); ?> orders</h2>
	<?php displayPendingOrders(); ?>
        </div>
    </div>
</body>
</html>
