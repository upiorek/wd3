<?php
require_once '/home/ubuntu/repo/login.php';
requireLogin();
require_once '/home/ubuntu/repo/config.php';

header('Content-Type: text/html; charset=utf-8');
date_default_timezone_set(APP_TIMEZONE);

function extractTotalNetProfit($content) {
    if (preg_match('/Total net profit:\s*([-+]?\d*\.?\d+)/', $content, $matches)) {
        return $matches[1];
    }
    return null;
}

function extractTotalOrdersCount($content) {
    $lines = explode("\n", $content);
    $orderCount = 0;
    foreach ($lines as $line) {
        $line = trim($line);
        if (empty($line) ||
            strpos($line, '=') === 0 ||
            strpos($line, 'Total') === 0 ||
            strpos($line, 'Account') === 0 ||
            strpos($line, 'Date') === 0 ||
            strpos($line, 'Symbol') === 0 ||
            strpos($line, '----') === 0) {
            continue;
        }
        if (preg_match('/^\d+\s/', $line)) {
            $orderCount++;
        }
    }
    return $orderCount;
}

function extractAccountProfit($content) {
    if (preg_match('/Profit:\s*([-+]?\d*\.?\d+)/', $content, $matches)) {
        return $matches[1];
    }
    return null;
}

function extractAccountOrders($content) {
    if (preg_match('/Orders:\s*(\d+)/', $content, $matches)) {
        return $matches[1];
    }
    return null;
}

function getAccountProfit() {
    if (file_exists(ACCOUNT_LOG_FILE)) {
        return extractAccountProfit(file_get_contents(ACCOUNT_LOG_FILE));
    }
    return null;
}

function getAccountOrders() {
    if (file_exists(ACCOUNT_LOG_FILE)) {
        return extractAccountOrders(file_get_contents(ACCOUNT_LOG_FILE));
    }
    return null;
}

function getTotalNetProfit() {
    if (file_exists(ORDER_HISTORY_LOG_FILE)) {
        return extractTotalNetProfit(file_get_contents(ORDER_HISTORY_LOG_FILE));
    }
    return null;
}

function getTotalOrdersCount() {
    if (file_exists(ORDER_HISTORY_LOG_FILE)) {
        return extractTotalOrdersCount(file_get_contents(ORDER_HISTORY_LOG_FILE));
    }
    return 0;
}

/**
 * Parse a single order file and return an associative array of fields.
 */
function parseOrderFile($filePath) {
    $content = file_get_contents($filePath);
    if ($content === false) return null;
    $order = [];
    foreach (explode("\n", $content) as $line) {
        $line = trim($line);
        if (strpos($line, ':') === false) continue;
        [$key, $val] = explode(':', $line, 2);
        $order[trim($key)] = trim($val);
    }
    return $order;
}

/**
 * Load all CLOSED orders from the orders directory, grouped by full Mon-Sun week.
 * Only full weeks (where Sunday has already passed) are included.
 * Returns array keyed by week start (Monday) as 'Y-m-d', each entry has:
 *   label, mon, sun, orders[], net, wins, losses
 */
function getOrdersByFullWeek() {
    $ordersDir = MQL4_FILES_PATH . '/orders';
    if (!is_dir($ordersDir)) return [];

    $now = new DateTime();
    // Start of current week (Monday 00:00:00)
    $currentWeekMon = clone $now;
    $currentWeekMon->modify('monday this week');
    $currentWeekMon->setTime(0, 0, 0);

    $weeks = [];

    foreach (scandir($ordersDir) as $file) {
        if ($file === '.' || $file === '..') continue;
        $path = $ordersDir . '/' . $file;
        if (!is_file($path)) continue;

        $order = parseOrderFile($path);
        if (!$order) continue;
        if (($order['Status'] ?? '') !== 'CLOSED') continue;
        if (($order['Type'] ?? '') === 'UNKNOWN') continue;

        $closeTimeStr = $order['Close Time'] ?? '';
        if (!$closeTimeStr) continue;

        // Parse "2026.04.21 17:27:08"
        $closeTime = DateTime::createFromFormat('Y.m.d H:i:s', $closeTimeStr);
        if (!$closeTime) continue;

        // Find the Monday of this order's close week
        $weekMon = clone $closeTime;
        $weekMon->modify('monday this week');
        $weekMon->setTime(0, 0, 0);

        // Only include full weeks (week must be strictly before current week)
        if ($weekMon >= $currentWeekMon) continue;

        $weekKey = $weekMon->format('Y-m-d');

        if (!isset($weeks[$weekKey])) {
            $weekSun = clone $weekMon;
            $weekSun->modify('+6 days');
            $weeks[$weekKey] = [
                'label' => $weekMon->format('d.m') . ' – ' . $weekSun->format('d.m.Y'),
                'mon'   => $weekMon->format('Y-m-d'),
                'sun'   => $weekSun->format('Y-m-d'),
                'orders' => [],
                'net'   => 0.0,
                'wins'  => 0,
                'losses' => 0,
            ];
        }

        $net = floatval($order['Result (Net)'] ?? 0);
        $weeks[$weekKey]['orders'][] = $order;
        $weeks[$weekKey]['net'] += $net;
        if ($net >= 0) {
            $weeks[$weekKey]['wins']++;
        } else {
            $weeks[$weekKey]['losses']++;
        }
    }

    // Sort descending (newest week first)
    krsort($weeks);
    return $weeks;
}

/**
 * Load CLOSED orders from the current (ongoing) week.
 */
function getCurrentWeekStats() {
    $ordersDir = MQL4_FILES_PATH . '/orders';
    if (!is_dir($ordersDir)) return null;

    $now = new DateTime();
    $currentWeekMon = clone $now;
    $currentWeekMon->modify('monday this week');
    $currentWeekMon->setTime(0, 0, 0);
    $currentWeekSun = clone $currentWeekMon;
    $currentWeekSun->modify('+6 days');

    $orders = [];
    $net = 0.0;
    $wins = 0;
    $losses = 0;

    foreach (scandir($ordersDir) as $file) {
        if ($file === '.' || $file === '..') continue;
        $path = $ordersDir . '/' . $file;
        if (!is_file($path)) continue;

        $order = parseOrderFile($path);
        if (!$order) continue;
        if (($order['Status'] ?? '') !== 'CLOSED') continue;
        if (($order['Type'] ?? '') === 'UNKNOWN') continue;

        $closeTimeStr = $order['Close Time'] ?? '';
        if (!$closeTimeStr) continue;

        $closeTime = DateTime::createFromFormat('Y.m.d H:i:s', $closeTimeStr);
        if (!$closeTime) continue;

        $weekMon = clone $closeTime;
        $weekMon->modify('monday this week');
        $weekMon->setTime(0, 0, 0);

        if ($weekMon->format('Y-m-d') !== $currentWeekMon->format('Y-m-d')) continue;

        $orderNet = floatval($order['Result (Net)'] ?? 0);
        $orders[] = $order;
        $net += $orderNet;
        if ($orderNet >= 0) $wins++; else $losses++;
    }

    return [
        'label' => $currentWeekMon->format('d.m') . ' – ' . $currentWeekSun->format('d.m.Y'),
        'orders' => $orders,
        'net'    => $net,
        'wins'   => $wins,
        'losses' => $losses,
    ];
}

/**
 * Aggregate login audit entries by week (Monday-based).
 * Returns array keyed by week start 'Y-m-d':
 *   ['total' => int, 'users' => ['P' => int, 'R' => int, ...]]
 */
function getLoginCountsByWeek() {
    $loginFile = defined('LOGIN_AUDIT_FILE') ? LOGIN_AUDIT_FILE : '/home/ubuntu/repo/login_history.log';
    if (!is_file($loginFile) || !is_readable($loginFile)) {
        return [];
    }

    $result = [];
    $lines = file($loginFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    if ($lines === false) {
        return [];
    }

    foreach ($lines as $line) {
        $line = trim((string)$line);
        if ($line === '' || strpos($line, '#') === 0) {
            continue;
        }

        $parts = explode('|', $line, 2);
        if (count($parts) < 2) {
            continue;
        }

        $ts = trim($parts[0]);
        $user = strtoupper(trim($parts[1]));
        if ($user === '') {
            $user = 'UNKNOWN';
        }

        $dt = DateTime::createFromFormat('Y-m-d H:i:s', $ts);
        if (!$dt) {
            continue;
        }

        $weekMon = clone $dt;
        $weekMon->modify('monday this week');
        $weekMon->setTime(0, 0, 0);
        $weekKey = $weekMon->format('Y-m-d');

        if (!isset($result[$weekKey])) {
            $result[$weekKey] = [
                'total' => 0,
                'users' => [],
            ];
        }

        $result[$weekKey]['total']++;
        if (!isset($result[$weekKey]['users'][$user])) {
            $result[$weekKey]['users'][$user] = 0;
        }
        $result[$weekKey]['users'][$user]++;
    }

    return $result;
}

// AJAX handler
if (isset($_GET['ajax']) || isset($_POST['ajax'])) {
    $action = isset($_GET['ajax']) ? $_GET['ajax'] : $_POST['ajax'];

    if ($action === 'total_net_profit') {
        $totalNetProfit = getTotalNetProfit();
        $ordersCount = getTotalOrdersCount();
        if ($totalNetProfit !== null) {
            $profitClass = (floatval($totalNetProfit) >= 0) ? 'profit-positive' : 'profit-negative';
            $formatted = '<strong style="font-size: 1.2em;">zamknięte (' . $ordersCount . '): <span class="' . $profitClass . '">' . htmlspecialchars($totalNetProfit) . '</span></strong>';
        } else {
            $formatted = '<strong style="color: #6c757d;">zamknięte (' . $ordersCount . '): N/A</strong>';
        }
        echo json_encode(['value' => $totalNetProfit, 'formatted' => $formatted]);
        exit;
    }

    if ($action === 'account_profit') {
        $accountProfit = getAccountProfit();
        $accountOrders = getAccountOrders();
        if ($accountProfit !== null) {
            $profitClass = (floatval($accountProfit) >= 0) ? 'profit-positive' : 'profit-negative';
            $formatted = '<strong style="font-size: 1.2em;">otwarte (' . ($accountOrders !== null ? $accountOrders : '0') . '): <span class="' . $profitClass . '">' . htmlspecialchars($accountProfit) . '</span></strong>';
        } else {
            $formatted = '<strong style="color: #6c757d;">otwarte (' . ($accountOrders !== null ? $accountOrders : '0') . '): N/A</strong>';
        }
        echo json_encode(['value' => $accountProfit, 'formatted' => $formatted]);
        exit;
    }

    echo json_encode(['success' => false, 'message' => 'Invalid action']);
    exit;
}

$accountProfit = getAccountProfit();
$totalNetProfit = getTotalNetProfit();
$ordersCount = getTotalOrdersCount();
$accountOrders = getAccountOrders();
$weeklyStats = getOrdersByFullWeek();
$currentWeekStats = getCurrentWeekStats();
$loginCountsByWeek = getLoginCountsByWeek();
$currentWeekMon = new DateTime();
$currentWeekMon->modify('monday this week');
$currentWeekMon->setTime(0, 0, 0);
$currentWeekKey = $currentWeekMon->format('Y-m-d');
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo APP_TITLE; ?>: stats</title>
    <style>
        <?php echo file_get_contents('/home/ubuntu/repo/styles.css'); ?>
        .stats-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            margin-top: 10px;
        }
        .stats-table th, .stats-table td {
            padding: 8px 10px;
            border: 1px solid #dee2e6;
            text-align: right;
        }
        .stats-table th {
            background: #f1f3f5;
            font-weight: 600;
            text-align: center;
        }
        .stats-table td:first-child {
            text-align: left;
            font-weight: 500;
        }
        .stats-table tr:hover td {
            background: #f8f9fa;
        }
        .week-net-positive { color: #28a745; font-weight: bold; }
        .week-net-negative { color: #dc3545; font-weight: bold; }
        .orders-detail-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            margin-top: 8px;
        }
        .orders-detail-table th, .orders-detail-table td {
            padding: 4px 8px;
            border: 1px solid #e9ecef;
            text-align: right;
        }
        .orders-detail-table th {
            background: #f8f9fa;
            font-weight: 600;
        }
        .orders-detail-table td:first-child,
        .orders-detail-table th:first-child { text-align: left; }
        .orders-detail-table tr.win td { background: #f0fff4; }
        .orders-detail-table tr.loss td { background: #fff5f5; }
        .week-section {
            margin-bottom: 20px;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            overflow: hidden;
        }
        .week-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            background: #f1f3f5;
            cursor: pointer;
            user-select: none;
        }
        .week-header:hover { background: #e9ecef; }
        .week-body { padding: 12px 15px; display: none; }
        .week-body.open { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <div style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h1 style="margin: 0;">stats</h1>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <a href="index.php" style="color: #007bff; text-decoration: none; font-size: 14px; padding: 8px 16px; border: 1px solid #007bff; border-radius: 4px; transition: all 0.3s ease;"
                       onmouseover="this.style.backgroundColor='#007bff'; this.style.color='white';"
                       onmouseout="this.style.backgroundColor='transparent'; this.style.color='#007bff';">
                        pora zarobić?
                    </a>
                </div>
            </div>
        </div>

        <!-- Total Net Profit Display -->
        <div id="total-net-profit-display" style="margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #007bff; border-radius: 4px; text-align: center;">
            <?php
            if ($totalNetProfit !== null) {
                $profitClass = (floatval($totalNetProfit) >= 0) ? 'profit-positive' : 'profit-negative';
                echo '<strong style="font-size: 1.2em;">zamknięte (' . $ordersCount . '): <span class="' . $profitClass . '">' . htmlspecialchars($totalNetProfit) . '</span></strong>';
            } else {
                echo '<strong style="color: #6c757d;">zamknięte (' . $ordersCount . '): N/A</strong>';
            }
            ?>
            <br/>
            <?php
            if ($accountProfit !== null) {
                $profitClass = (floatval($accountProfit) >= 0) ? 'profit-positive' : 'profit-negative';
                echo '<strong style="font-size: 1.2em;">otwarte (' . ($accountOrders !== null ? $accountOrders : '0') . '): <span class="' . $profitClass . '">' . htmlspecialchars($accountProfit) . '</span></strong>';
            } else {
                echo '<strong style="color: #6c757d;">otwarte (' . ($accountOrders !== null ? $accountOrders : '0') . '): N/A</strong>';
            }
            ?>
        </div>

        <hr style="margin: 30px 0;">

        <h2>Statystyki tygodniowe</h2>

        <?php if (empty($weeklyStats)): ?>
            <p style="color: #6c757d;">Brak danych o zamkniętych orderach z pełnych tygodni.</p>
        <?php else: ?>
            <!-- Summary table -->
            <table class="stats-table" style="margin-bottom: 24px;">
                <thead>
                    <tr>
                        <th>Tydzień</th>
                        <th>#</th>
                        <th>win</th>
                        <th>loss</th>
                        <th>Win %</th>
                        <th>Net</th>
                        <th>Avg</th>
                    </tr>
                </thead>
                <tbody>
                <?php
                $totalAllNet = 0;
                $totalAllOrders = 0;
                $totalAllWins = 0;
                $totalAllLosses = 0;
                $cwCount = count($currentWeekStats['orders']);
                $cwNet   = $currentWeekStats['net'];
                $cwWins  = $currentWeekStats['wins'];
                $cwLoss  = $currentWeekStats['losses'];
                $cwWinPct = $cwCount > 0 ? round($cwWins / $cwCount * 100, 1) : 0;
                $cwAvg   = $cwCount > 0 ? $cwNet / $cwCount : 0;
                $cwNetClass = $cwNet >= 0 ? 'week-net-positive' : 'week-net-negative';
                ?>
                    <tr style="background: #fffbe6; font-style: italic;">
                        <td style="color: #856404;"><?php echo htmlspecialchars($currentWeekStats['label']); ?></td>
                        <td><?php echo $cwCount; ?></td>
                        <td style="color: #28a745;"><?php echo $cwWins; ?></td>
                        <td style="color: #dc3545;"><?php echo $cwLoss; ?></td>
                        <td><?php echo $cwWinPct; ?>%</td>
                        <td class="<?php echo $cwNetClass; ?>"><?php echo number_format($cwNet, 2); ?></td>
                        <td class="<?php echo $cwAvg >= 0 ? 'week-net-positive' : 'week-net-negative'; ?>"><?php echo number_format($cwAvg, 2); ?></td>
                    </tr>
                <?php
                foreach ($weeklyStats as $weekKey => $week):
                    $count = count($week['orders']);
                    $net = $week['net'];
                    $wins = $week['wins'];
                    $losses = $week['losses'];
                    $winPct = $count > 0 ? round($wins / $count * 100, 1) : 0;
                    $avg = $count > 0 ? $net / $count : 0;
                    $netClass = $net >= 0 ? 'week-net-positive' : 'week-net-negative';
                    $totalAllNet += $net;
                    $totalAllOrders += $count;
                    $totalAllWins += $wins;
                    $totalAllLosses += $losses;
                ?>
                    <tr>
                        <td><?php echo htmlspecialchars($week['label']); ?></td>
                        <td><?php echo $count; ?></td>
                        <td style="color: #28a745;"><?php echo $wins; ?></td>
                        <td style="color: #dc3545;"><?php echo $losses; ?></td>
                        <td><?php echo $winPct; ?>%</td>
                        <td class="<?php echo $netClass; ?>"><?php echo number_format($net, 2); ?></td>
                        <td class="<?php echo $avg >= 0 ? 'week-net-positive' : 'week-net-negative'; ?>"><?php echo number_format($avg, 2); ?></td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
                <tfoot>
                    <tr style="font-weight: bold; background: #f1f3f5;">
                        <td>SUMA</td>
                        <td><?php echo $totalAllOrders; ?></td>
                        <td style="color: #28a745;"><?php echo $totalAllWins; ?></td>
                        <td style="color: #dc3545;"><?php echo $totalAllLosses; ?></td>
                        <td><?php echo $totalAllOrders > 0 ? round($totalAllWins / $totalAllOrders * 100, 1) : 0; ?>%</td>
                        <td class="<?php echo $totalAllNet >= 0 ? 'week-net-positive' : 'week-net-negative'; ?>"><?php echo number_format($totalAllNet, 2); ?></td>
                        <td class="<?php echo $totalAllOrders > 0 && $totalAllNet / $totalAllOrders >= 0 ? 'week-net-positive' : 'week-net-negative'; ?>"><?php echo $totalAllOrders > 0 ? number_format($totalAllNet / $totalAllOrders, 2) : '0.00'; ?></td>
                    </tr>
                </tfoot>
            </table>

            <h3 style="margin-top: 0;">Logowania tygodniowe</h3>
            <table class="stats-table" style="margin-bottom: 24px;">
                <thead>
                    <tr>
                        <th>Tydzień</th>
                        <th>P</th>
                        <th>R</th>
                        <th>Logowania razem</th>
                    </tr>
                </thead>
                <tbody>
                <?php
                $loginWeekKeys = array_unique(array_merge([$currentWeekKey], array_keys($weeklyStats), array_keys($loginCountsByWeek)));
                rsort($loginWeekKeys);
                $loginTotalP = 0;
                $loginTotalR = 0;
                $loginTotalAll = 0;
                $renderedLoginRows = 0;

                foreach ($loginWeekKeys as $weekKey):
                    $weekMon = DateTime::createFromFormat('Y-m-d H:i:s', $weekKey . ' 00:00:00');
                    if (!$weekMon) {
                        continue;
                    }
                    $weekSun = clone $weekMon;
                    $weekSun->modify('+6 days');
                    $weekLabel = $weekMon->format('d.m') . ' – ' . $weekSun->format('d.m.Y');

                    $weekLoginP = intval($loginCountsByWeek[$weekKey]['users']['P'] ?? 0);
                    $weekLoginR = intval($loginCountsByWeek[$weekKey]['users']['R'] ?? 0);
                    $weekLoginTotal = intval($loginCountsByWeek[$weekKey]['total'] ?? 0);

                    if ($weekLoginTotal === 0) {
                        continue;
                    }

                    $loginTotalP += $weekLoginP;
                    $loginTotalR += $weekLoginR;
                    $loginTotalAll += $weekLoginTotal;
                    $renderedLoginRows++;

                    $rowStyle = ($weekKey === $currentWeekKey) ? ' style="background: #fffbe6; font-style: italic;"' : '';
                    $labelStyle = ($weekKey === $currentWeekKey) ? ' style="color: #856404;"' : '';
                ?>
                    <tr<?php echo $rowStyle; ?>>
                        <td<?php echo $labelStyle; ?>><?php echo htmlspecialchars($weekLabel); ?></td>
                        <td><?php echo $weekLoginP; ?></td>
                        <td><?php echo $weekLoginR; ?></td>
                        <td><?php echo $weekLoginTotal; ?></td>
                    </tr>
                <?php endforeach; ?>
                <?php if ($renderedLoginRows === 0): ?>
                    <tr>
                        <td colspan="4" style="text-align: center; color: #6c757d;">Brak logowań do wyświetlenia.</td>
                    </tr>
                <?php endif; ?>
                </tbody>
                <?php if ($renderedLoginRows > 0): ?>
                <tfoot>
                    <tr style="font-weight: bold; background: #f1f3f5;">
                        <td>SUMA</td>
                        <td><?php echo $loginTotalP; ?></td>
                        <td><?php echo $loginTotalR; ?></td>
                        <td><?php echo $loginTotalAll; ?></td>
                    </tr>
                </tfoot>
                <?php endif; ?>
            </table>

            <h3 style="margin-top: 0;">Dane tygodniowe</h3>
            <?php foreach ($weeklyStats as $weekKey => $week):
                $count = count($week['orders']);
                $net = $week['net'];
                $wins = $week['wins'];
                $losses = $week['losses'];
                $winPct = $count > 0 ? round($wins / $count * 100, 1) : 0;
                $netClass = $net >= 0 ? 'week-net-positive' : 'week-net-negative';

                // Sort orders by Close Time
                usort($week['orders'], function($a, $b) {
                    return strcmp($a['Close Time'] ?? '', $b['Close Time'] ?? '');
                });
            ?>
            <div class="week-section">
                <div class="week-header" onclick="toggleWeek(this)">
                    <span><strong><?php echo htmlspecialchars($week['label']); ?></strong> &nbsp; <?php echo $count; ?> orderów &nbsp; W:<?php echo $wins; ?> L:<?php echo $losses; ?> (<?php echo $winPct; ?>%)</span>
                    <span class="<?php echo $netClass; ?>"><?php echo number_format($net, 2); ?> ▾</span>
                </div>
                <div class="week-body">
                    <table class="orders-detail-table">
                        <thead>
                            <tr>
                                <th>Ticket</th>
                                <th>Type</th>
                                <th>Symbol</th>
                                <th>Lots</th>
                                <th>Open Time</th>
                                <th>Close Time</th>
                                <th>Open</th>
                                <th>Close</th>
                                <th>SL</th>
                                <th>TP</th>
                                <th>Profit</th>
                                <th>Comm</th>
                                <th>Net</th>
                            </tr>
                        </thead>
                        <tbody>
                        <?php foreach ($week['orders'] as $order):
                            $orderNet = floatval($order['Result (Net)'] ?? 0);
                            $rowClass = $orderNet >= 0 ? 'win' : 'loss';
                        ?>
                            <tr class="<?php echo $rowClass; ?>">
                                <td><?php echo htmlspecialchars($order['Ticket'] ?? ''); ?></td>
                                <td><?php echo htmlspecialchars($order['Type'] ?? ''); ?></td>
                                <td><?php echo htmlspecialchars($order['Symbol'] ?? ''); ?></td>
                                <td><?php echo htmlspecialchars($order['Lots'] ?? ''); ?></td>
                                <td><?php echo htmlspecialchars($order['Open Time'] ?? ''); ?></td>
                                <td><?php echo htmlspecialchars($order['Close Time'] ?? ''); ?></td>
                                <td><?php echo htmlspecialchars($order['Open Price'] ?? ''); ?></td>
                                <td><?php echo htmlspecialchars($order['Close Price'] ?? ''); ?></td>
                                <td><?php echo htmlspecialchars($order['Stop Loss'] ?? ''); ?></td>
                                <td><?php echo htmlspecialchars($order['Take Profit'] ?? ''); ?></td>
                                <td style="<?php echo floatval($order['Profit'] ?? 0) >= 0 ? 'color:#28a745' : 'color:#dc3545'; ?>"><?php echo number_format(floatval($order['Profit'] ?? 0), 2); ?></td>
                                <td><?php echo number_format(floatval($order['Commission'] ?? 0), 2); ?></td>
                                <td class="<?php echo $orderNet >= 0 ? 'week-net-positive' : 'week-net-negative'; ?>"><?php echo number_format($orderNet, 2); ?></td>
                            </tr>
                        <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
            </div>
            <?php endforeach; ?>
        <?php endif; ?>

    </div>

    <script>
        function refreshProfits() {
            Promise.all([
                fetch('stats.php?ajax=total_net_profit').then(r => r.json()),
                fetch('stats.php?ajax=account_profit').then(r => r.json())
            ])
            .then(([total, account]) => {
                document.getElementById('total-net-profit-display').innerHTML =
                    total.formatted + '<br/>' + account.formatted;
                document.title = '<?php echo APP_TITLE; ?>: ' + (account.value !== null ? account.value : 'N/A');
            })
            .catch(error => console.error('Error refreshing profits:', error));
        }

        function toggleWeek(header) {
            const body = header.nextElementSibling;
            const arrow = header.querySelector('span:last-child');
            body.classList.toggle('open');
            const net = arrow.textContent.replace('▾', '').replace('▴', '').trim();
            arrow.textContent = body.classList.contains('open') ? net + ' ▴' : net + ' ▾';
        }

        setInterval(refreshProfits, 1000);
    </script>
</body>
</html>
