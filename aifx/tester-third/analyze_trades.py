import os
import time
import sys
from pathlib import Path

def revert_mod_file(file_path):
    """Remove all annotations, keeping only candles and BUY/SELL signal."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    modified = False
    for i, line in enumerate(lines):
        # Skip header line
        if i == 0:
            continue
            
        stripped = line.rstrip()
        
        # Split by semicolon to get the base CSV data
        parts = stripped.split(';')
        if len(parts) >= 5:
            # Keep only first 5 parts (Time;Open;High;Low;Close)
            base_parts = parts[:5]
            
            # Clean the Close field and check for BUY/SELL
            close_field = base_parts[4]
            
            # Check if line has BUY or SELL signal
            if ' BUY' in stripped:
                # Extract just the close price
                close_price = close_field.split()[0]
                base_parts[4] = close_price
                lines[i] = ';'.join(base_parts) + ' BUY\n'
                modified = True
            elif ' SELL' in stripped:
                # Extract just the close price
                close_price = close_field.split()[0]
                base_parts[4] = close_price
                lines[i] = ';'.join(base_parts) + ' SELL\n'
                modified = True
            elif ' ' in close_field or 'gain' in stripped or 'loss' in stripped:
                # Line has annotations but no signal - remove all annotations
                close_price = close_field.split()[0]
                base_parts[4] = close_price
                lines[i] = ';'.join(base_parts) + '\n'
                modified = True
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        print(f"Reverted: {file_path.name}")
    else:
        print(f"No changes: {file_path.name}")

def calculate_distances(signal, entry_price, open_price, high, low):
    """Calculate TP and SL distances from entry price.
    
    Returns: (dist_tp, dist_sl, dist_tp_open, dist_sl_open)
    """
    if signal == 'BUY':
        # For BUY: TP is above entry, SL is below
        dist_tp = high - entry_price
        dist_sl = low - entry_price
        dist_tp_open = open_price - entry_price
        dist_sl_open = open_price - entry_price
    else:  # SELL
        # For SELL: TP is below entry, SL is above
        dist_tp = entry_price - low
        dist_sl = entry_price - high
        dist_tp_open = entry_price - open_price
        dist_sl_open = entry_price - open_price
    
    return dist_tp, dist_sl, dist_tp_open, dist_sl_open

def check_targets_hit(signal, entry_price, open_price, high, low, tp_target, sl_target, sl_target_at_open):
    """Check if TP or SL targets are hit.
    
    Args:
        sl_target: Current SL target (may be 0 if BE was triggered)
        sl_target_at_open: The SL target at the start of the candle (before any BE move this candle)
    
    Returns: (tp_hit, sl_hit, tp_at_open, sl_at_open)
    """
    dist_tp, dist_sl, _, _ = calculate_distances(signal, entry_price, open_price, high, low)
    
    tp_hit = dist_tp >= tp_target
    sl_hit = dist_sl <= sl_target  # Use current sl_target for hit detection
    
    if signal == 'BUY':
        tp_at_open = (open_price >= entry_price + tp_target)
        sl_at_open = (open_price <= entry_price + sl_target_at_open)
    else:  # SELL
        tp_at_open = (open_price <= entry_price - tp_target)
        sl_at_open = (open_price >= entry_price - sl_target_at_open)
    
    return tp_hit, sl_hit, tp_at_open, sl_at_open

def determine_result(tp_hit, sl_hit, tp_at_open, sl_at_open, sl_moved_to_be, be_hit, 
                      sl_be_moved_idx, i, dist_tp, dist_sl, dist_tp_open, dist_sl_open):
    """Determine the result of the trade based on which targets were hit.
    
    Returns: (result, result_at_open, be_hit_updated, be_hit_idx, final_dist_tp, final_dist_sl, bad_luck)
    """
    bad_luck = False
    result = None
    result_at_open = False
    be_hit_updated = be_hit
    be_hit_idx = None
    final_dist_tp = 0
    final_dist_sl = 0
    
    # Check if both TP and SL could be hit in same candle (BAD LUCK scenario)
    if tp_hit and sl_hit:
        bad_luck = True
        # Prefer worst scenario - if BE was triggered, it's BE, otherwise it's SL
        if sl_moved_to_be:
            result = 'BE'  # Break-even was hit (neutral outcome)
        else:
            result = 'SL'  # Original SL was hit (loss outcome)
        result_at_open = sl_at_open
        # Store actual distances (may include slippage)
        final_dist_sl = dist_sl
        final_dist_tp = dist_tp
    elif tp_hit:
        result = 'TP'
        result_at_open = tp_at_open
        # Store actual distance: if at open, use open distance (slippage); else use high/low distance
        final_dist_tp = dist_tp_open if tp_at_open else dist_tp
        final_dist_sl = dist_sl
    elif sl_hit:
        if sl_moved_to_be and not be_hit:
            # BE was hit - this is the final result
            be_hit_updated = True
            result = 'BE'
            # Only mark "(at open)" if BE was set on a previous candle
            result_at_open = sl_at_open and (sl_be_moved_idx < i)
            be_hit_idx = i
            # Store actual distances (may include slippage)
            final_dist_sl = dist_sl
            final_dist_tp = dist_tp
        else:
            # Original SL was hit
            result = 'SL'
            result_at_open = sl_at_open
            # Store actual distance: if at open, use open distance (slippage); else use low/high distance
            final_dist_sl = dist_sl_open if sl_at_open else dist_sl
            final_dist_tp = dist_tp
    
    return result, result_at_open, be_hit_updated, be_hit_idx, final_dist_tp, final_dist_sl, bad_luck

def clean_base_line(line_content):
    """Extract base OHLC data from a line, removing any annotations.
    
    Returns: base_line (string with only Time;Open;High;Low;Close)
    """
    if ' gain' in line_content or ' loss' in line_content:
        parts = line_content.split(';')
        if len(parts) >= 5:
            close_field = parts[4].split()[0]  # Take only the price part
            return ';'.join(parts[:4] + [close_field])
        else:
            return ';'.join(parts)
    return line_content

def calculate_current_gain_loss(signal, entry_price, close, i, result_idx, result, result_at_open, 
                                 final_dist_tp, final_dist_sl, tp_target, sl_target):
    """Calculate the gain/loss to display for the current candle.
    
    Returns: current_gain_loss (float)
    """
    if i == result_idx:
        # For result candle, show the actual final result distance
        if result == 'TP':
            # If hit at open (slippage/gap), show actual distance; otherwise cap at target
            current_gain_loss = final_dist_tp if result_at_open else min(final_dist_tp, tp_target)
        elif result == 'SL':
            # If hit at open (slippage/gap), show actual distance; otherwise cap at target
            current_gain_loss = final_dist_sl if result_at_open else max(final_dist_sl, sl_target)
        elif result == 'BE':
            current_gain_loss = 0.0
        else:
            # Fallback to close-based calculation
            if signal == 'BUY':
                current_gain_loss = close - entry_price
            else:  # SELL
                current_gain_loss = entry_price - close
    else:
        # For non-result candles, show close-based gain/loss
        if signal == 'BUY':
            current_gain_loss = close - entry_price
        else:  # SELL
            current_gain_loss = entry_price - close
    
    return current_gain_loss

def annotate_line(base_line, current_gain_loss, i, result_idx, result, result_at_open, bad_luck,
                  sl_be_moved_idx):
    """Annotate a line with gain/loss and result markers.
    
    Returns: annotated line string
    """
    gain_loss_label = "gain" if current_gain_loss > 0 else "loss"
    
    # Add "(at open)" suffix if result hit at open price
    open_suffix = " (at open)" if (i == result_idx and result_at_open) else ""
    
    # Add "(bad luck)" suffix if bad luck scenario
    bad_luck_suffix = " (bad luck)" if (i == result_idx and bad_luck) else ""
    
    if i == result_idx:
        # Add final result marker with gain/loss
        # If BE was hit in the same candle where SL->BE happened, show both
        if result == 'BE' and sl_be_moved_idx == i:
            return f"{base_line} {gain_loss_label} {abs(current_gain_loss):.2f} SL->BE {result}{open_suffix}{bad_luck_suffix}\n"
        else:
            return f"{base_line} {gain_loss_label} {abs(current_gain_loss):.2f} {result}{open_suffix}{bad_luck_suffix}\n"
    elif result is None:
        # Check if this is the candle where SL moved to BE
        if sl_be_moved_idx is not None and i == sl_be_moved_idx:
            return f"{base_line} {gain_loss_label} {abs(current_gain_loss):.2f} SL->BE\n"
        else:
            return f"{base_line} {gain_loss_label} {abs(current_gain_loss):.2f}\n"
    # After final result, return None to indicate no annotation
    return None

def process_mod_file(file_path):
    """Process a _mod file and add distance to TP/SL for each candle."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    if len(lines) < 2:
        return None, False, 0, 1
    
    # Find the line with BUY or SELL
    signal_line_idx = None
    signal = None
    
    for i, line in enumerate(lines):
        if line.strip().endswith(' BUY'):
            signal_line_idx = i
            signal = 'BUY'
            break
        elif line.strip().endswith(' SELL'):
            signal_line_idx = i
            signal = 'SELL'
            break
    
    if signal_line_idx is None or signal is None:
        # print(f"No signal found in {file_path.name}")
        return None, False, 0, 1
    
    # Get entry price (open price of next candle after signal)
    if signal_line_idx + 1 >= len(lines):
        print(f"No candles after signal in {file_path.name}")
        return None, False, 0, 1
    
    entry_candle = lines[signal_line_idx + 1].strip().split(';')
    if len(entry_candle) < 2:
        return None, False, 0, 1
    
    try:
        entry_price = float(entry_candle[1])
    except ValueError:
        return None, False, 0, 1
    
    tp_target = 200
    sl_target = -50
    be_trigger = 100  # Move SL to BE when TP distance reaches this
    sl_moved_to_be = False
    sl_be_moved_idx = None  # Track which candle SL moved to BE
    be_hit = False
    be_hit_idx = None
    result = None
    result_idx = None
    result_at_open = False  # Track if result hit at open price
    final_dist_sl = 0
    final_dist_tp = 0
    last_close_price = 0
    bad_luck = False  # Flag for when multiple outcomes could happen in same candle
    
    # Process all candles starting from entry candle
    # Entry happens at open of signal_idx, and TP/SL could be hit during that same candle
    for i in range(signal_line_idx + 1, len(lines)):
        parts = lines[i].strip().split(';')
        if len(parts) < 4:
            continue
        
        try:
            open_price = float(parts[1])
            high = float(parts[2])
            low = float(parts[3])
            close = float(parts[4].split()[0]) if len(parts) > 4 else float(parts[3])
            
            # Track last close price
            last_close_price = close
            
            # Calculate distances for this candle
            dist_tp, dist_sl, dist_tp_open, dist_sl_open = calculate_distances(
                signal, entry_price, open_price, high, low
            )
            
            # Store sl_target at start of candle for at_open checks
            sl_target_at_open = sl_target
            
            # Check if TP or SL/BE hit on this candle
            if result is None:
                # Check if we should move SL to BE
                if not sl_moved_to_be and dist_tp >= be_trigger:
                    sl_moved_to_be = True
                    sl_be_moved_idx = i  # Track which candle this happened on
                    sl_target = 0  # Move SL to break-even

                tp_hit, sl_hit, tp_at_open, sl_at_open = check_targets_hit(
                    signal, entry_price, open_price, high, low, tp_target, sl_target, sl_target_at_open
                )
                
                # Determine result based on what was hit
                result, result_at_open, be_hit, be_hit_idx_temp, final_dist_tp, final_dist_sl, bad_luck = determine_result(
                    tp_hit, sl_hit, tp_at_open, sl_at_open, sl_moved_to_be, be_hit,
                    sl_be_moved_idx, i, dist_tp, dist_sl, dist_tp_open, dist_sl_open
                )
                if result is not None:
                    result_idx = i
                    if be_hit_idx_temp is not None:
                        be_hit_idx = be_hit_idx_temp
            
            # Add distance info to the line
            base_line = clean_base_line(lines[i].rstrip())
            
            # Calculate current gain/loss for this candle
            current_gain_loss = calculate_current_gain_loss(
                signal, entry_price, close, i, result_idx, result, result_at_open,
                final_dist_tp, final_dist_sl, tp_target, sl_target
            )
            
            # Annotate the line
            annotated_line = annotate_line(
                base_line, current_gain_loss, i, result_idx, result, result_at_open, 
                bad_luck, sl_be_moved_idx
            )
            
            if annotated_line is not None:
                lines[i] = annotated_line
        
        except (ValueError, IndexError):
            continue
    
    # Determine final result and calculate actual gain/loss
    # If result hit at open (slippage), use actual distance; otherwise cap at target
    if result == 'TP':
        final_result = 'TP'
        gain_loss = final_dist_tp if result_at_open else min(final_dist_tp, tp_target)
    elif result == 'SL':
        final_result = 'SL'
        gain_loss = final_dist_sl if result_at_open else max(final_dist_sl, sl_target)
    elif result == 'BE' or be_hit:
        final_result = 'BE'
        gain_loss = 0.0  # Break-even is always 0
    else:
        # Calculate result based on last close price for trades that didn't hit TP/SL/BE
        close_gain_loss = last_close_price - entry_price if signal == 'BUY' else entry_price - last_close_price
        
        if close_gain_loss > 0:
            final_result = 'Profiting'
        elif close_gain_loss < 0:
            final_result = 'Losing'
        else:
            final_result = None
        gain_loss = close_gain_loss
    
    # Write back to file
    with open(file_path, 'w') as f:
        f.writelines(lines)
    
    # Entry line number for clickable links (signal_line_idx + 2 because: 0-indexed array + 1 for entry + 1 for file lines)
    entry_line_num = signal_line_idx + 2
    
    return final_result, bad_luck, gain_loss, entry_line_num

def main():    
    revert = len(sys.argv) > 1 and sys.argv[1] == "--revert"
    
    # Check for folder argument (candles or orders)
    folder_type = "candles"  # default
    if len(sys.argv) > 1 and sys.argv[1] in ["orders", "candles"]:
        folder_type = sys.argv[1]
    elif len(sys.argv) > 2 and sys.argv[2] in ["orders", "candles"]:
        folder_type = sys.argv[2]
    
    # Determine folder based on type
    if folder_type == "orders":
        test_results_dir = Path(__file__).parent / "mt4_test_results" / "m15_orders"
        original_dir = Path(__file__).parent / "m15_orders"
        file_pattern = "*.csv"  # orders don't have _mod suffix
    else:
        test_results_dir = Path(__file__).parent / "mt4_test_results" / "m15_candles"
        original_dir = Path(__file__).parent / "m15_candles"
        file_pattern = "*_mod.csv" if not revert else "*_mod.csv"
    
    if test_results_dir.exists():
        candles_dir = test_results_dir
        print(f"Using MT4 test results: {candles_dir}")
    elif original_dir.exists():
        candles_dir = original_dir
        print(f"Using original {folder_type}: {candles_dir}")
    else:
        print(f"Directory not found: {test_results_dir}")
        print(f"Directory not found: {original_dir}")
        return
    
    # Get all matching files
    if folder_type == "orders":
        mod_files = sorted(candles_dir.glob(file_pattern))
    else:
        mod_files = sorted(candles_dir.glob(file_pattern))
    
    print(f"Found {len(mod_files)} {folder_type} files to {'revert' if revert else 'analyze'}\n")

    if revert:
        for mod_file in mod_files:
            revert_mod_file(mod_file)
    else:
        # Track statistics
        results = {'TP': 0, 'SL': 0, 'BE': 0, 'Profiting': 0, 'Losing': 0, 'None': 0}
        files_by_category = {'TP': [], 'SL': [], 'BE': [], 'Profiting': [], 'Losing': [], 'None': []}
        bad_luck_count = 0
        bad_luck_files = []  # Track files with bad luck
        total_gain_loss = 0
        
        processed_count = 0
        for mod_file in mod_files:
            result, is_bad_luck, gain_loss, entry_line_num = process_mod_file(mod_file)
            processed_count += 1
            
            if result:
                results[result] += 1
                files_by_category[result].append((str(mod_file), gain_loss, entry_line_num))
                total_gain_loss += gain_loss
            else:
                results['None'] += 1
                files_by_category['None'].append((str(mod_file), 0, entry_line_num))
            
            if is_bad_luck:
                bad_luck_count += 1
                bad_luck_files.append((str(mod_file), result, gain_loss, entry_line_num))
        
        print(f"Processed {processed_count}/{len(mod_files)} files... Done!")
        
        # Print summary
        print(f"\n{'='*50}")
        print("SUMMARY:")
        print(f"{'='*50}")
        print(f"TP Target:  +200 points")
        print(f"SL Target:   -50 points")
        print(f"BE Trigger: +100 points (moves SL to 0)")
        print(f"{'-'*50}")
        total_trades = len(mod_files)
        print(f"Total Trades:      {total_trades:3d}")
        print(f"{'-'*50}")
        
        print(f"TP (Take Profit):  {results['TP']:3d} trades")
        for filepath, gain_loss, line_num in sorted(files_by_category['TP'], key=lambda x: x[1], reverse=True):
            print(f"  - {filepath}:{line_num}: {gain_loss:+.2f}")
        
        print(f"Profiting (open):  {results['Profiting']:3d} trades")
        for filepath, gain_loss, line_num in sorted(files_by_category['Profiting'], key=lambda x: x[1], reverse=True):
            print(f"  - {filepath}:{line_num}: {gain_loss:+.2f}")
            
        print(f"BE (Break Even):   {results['BE']:3d} trades")
        for filepath, gain_loss, line_num in sorted(files_by_category['BE'], key=lambda x: x[1], reverse=True):
            print(f"  - {filepath}:{line_num}: {gain_loss:+.2f}")      

        print(f"Losing (open):     {results['Losing']:3d} trades")
        for filepath, gain_loss, line_num in sorted(files_by_category['Losing'], key=lambda x: x[1]):
            print(f"  - {filepath}:{line_num}: {gain_loss:+.2f}")
            
        print(f"SL (Stop Loss):    {results['SL']:3d} trades")
        for filepath, gain_loss, line_num in sorted(files_by_category['SL'], key=lambda x: x[1]):
            print(f"  - {filepath}:{line_num}: {gain_loss:+.2f}")        
                
        print(f"{'-'*50}")
        print(f"Bad Luck Trades:   {bad_luck_count:3d} trades")
        if bad_luck_files:
            for filepath, result, gain_loss, line_num in sorted(bad_luck_files, key=lambda x: x[0]):
                print(f"  - {filepath}:{line_num}: {result} {gain_loss:+.2f}")
                
        print(f"{'-'*50}")
        if results['None'] > 0:
            print(f"No Result:         {results['None']:3d} trades")
            # for filepath, gain_loss, line_num in sorted(files_by_category['None'], key=lambda x: x[0]):
            #    print(f"  - {filepath}:{line_num}:")
            
        print(f"{'='*50}")
        total_closed = results['TP'] + results['BE'] + results['SL']
        if total_closed > 0:
            wins = results['TP'] + results['Profiting']
            losses = results['SL'] + results['Losing']
            be_count = results['BE']
            win_rate = (wins / total_trades) * 100
            loss_rate = (losses / total_trades) * 100
            be_rate = (be_count / total_trades) * 100
            print(f"Win Rate: {win_rate:.1f}% ({wins}/{total_trades}) [TP + Profiting]")
            print(f"Loss Rate: {loss_rate:.1f}% ({losses}/{total_trades}) [SL + Losing]")
            print(f"BE Rate: {be_rate:.1f}% ({be_count}/{total_trades}) [Break Even]")
        print(f"Total P/L: {total_gain_loss:+.2f} points")
        print(f"{'='*50}")
    
    print(f"\n{'Revert' if revert else 'Analysis'} complete!")

if __name__ == "__main__":
    main()
