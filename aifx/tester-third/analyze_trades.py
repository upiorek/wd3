import os
import time
import sys
from pathlib import Path
from io import StringIO

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

def process_mod_file(file_path):
    """Process a _mod file and add distance to TP/SL for each candle."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    if len(lines) < 2:
        return None, False, 0
    
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
        print(f"No signal found in {file_path.name}")
        return None, False, 0
    
    # Get entry price (open price of next candle after signal)
    if signal_line_idx + 1 >= len(lines):
        print(f"No candles after signal in {file_path.name}")
        return None, False, 0
    
    entry_candle = lines[signal_line_idx + 1].strip().split(';')
    if len(entry_candle) < 2:
        return None, False, 0
    
    try:
        entry_price = float(entry_candle[1])
    except ValueError:
        return None, False, 0
    
    tp_target = 200
    sl_target = -50
    be_trigger = 100  # Move SL to BE when TP distance reaches this
    sl_moved_to_be = False
    sl_be_moved_idx = None  # Track which candle SL moved to BE
    be_hit = False
    be_hit_idx = None
    result = None
    result_idx = None
    final_dist_sl = 0
    final_dist_tp = 0
    last_close_price = 0
    bad_luck = False  # Flag for when multiple outcomes could happen in same candle
    signal_idx = signal_line_idx + 1  # Index of the entry candle
    
    # Process all candles after entry and add distance information
    for i in range(signal_line_idx + 1, len(lines)):
        parts = lines[i].strip().split(';')
        if len(parts) < 4:
            continue
        
        try:
            high = float(parts[2])
            low = float(parts[3])
            close = float(parts[4].split()[0]) if len(parts) > 4 else float(parts[3])
            
            # Track last close price
            last_close_price = close
            
            if signal == 'BUY':
                # For BUY: TP is above entry, SL is below
                dist_tp = high - entry_price
                dist_sl = low - entry_price                
                
                # Check if we should move SL to BE
                if not sl_moved_to_be and dist_tp >= be_trigger:
                    sl_moved_to_be = True
                    sl_be_moved_idx = i  # Track which candle this happened on
                    sl_target = 0  # Move SL to break-even
                
                # Check if TP or SL/BE hit on this candle
                if result is None:
                    tp_hit = dist_tp >= tp_target
                    sl_hit = dist_sl <= sl_target
                    
                    # Check if both TP and SL could be hit in same candle (BAD LUCK scenario)
                    if tp_hit and sl_hit:
                        bad_luck = True
                        # Prefer worst scenario - SL is always worse than BE
                        result = 'SL'
                        result_idx = i
                        # Use SL target value instead of actual low if low is worse
                        final_dist_sl = max(dist_sl, sl_target)
                        final_dist_tp = dist_tp
                    elif tp_hit:
                        result = 'TP'
                        result_idx = i
                        final_dist_tp = dist_tp
                        final_dist_sl = dist_sl
                    elif sl_hit:
                        if sl_moved_to_be and not be_hit:
                            # BE was hit - this is the final result
                            be_hit = True
                            result = 'BE'
                            result_idx = i
                            be_hit_idx = i
                            # Use SL target value instead of actual low if low is worse
                            final_dist_sl = max(dist_sl, sl_target)
                            final_dist_tp = dist_tp
                        else:
                            # Original SL was hit
                            result = 'SL'
                            result_idx = i
                            # Use SL target value instead of actual low if low is worse
                            final_dist_sl = max(dist_sl, sl_target)
                            final_dist_tp = dist_tp
            
            elif signal == 'SELL':
                # For SELL: TP is below entry, SL is above
                dist_tp = entry_price - low
                dist_sl = entry_price - high
                                
                # Check if we should move SL to BE
                if not sl_moved_to_be and dist_tp >= be_trigger:
                    sl_moved_to_be = True
                    sl_be_moved_idx = i  # Track which candle this happened on
                    sl_target = 0  # Move SL to break-even
                
                # Check if TP or SL/BE hit on this candle
                if result is None:
                    tp_hit = dist_tp >= tp_target
                    sl_hit = dist_sl <= sl_target
                    
                    # Check if both TP and SL could be hit in same candle (BAD LUCK scenario)
                    if tp_hit and sl_hit:
                        bad_luck = True
                        # Prefer worst scenario - SL is always worse than BE
                        result = 'SL'
                        result_idx = i
                        # Use SL target value instead of actual high if high is worse
                        final_dist_sl = max(dist_sl, sl_target)
                        final_dist_tp = dist_tp
                    elif tp_hit:
                        result = 'TP'
                        result_idx = i
                        final_dist_tp = dist_tp
                        final_dist_sl = dist_sl
                    elif sl_hit:
                        if sl_moved_to_be and not be_hit:
                            # BE was hit - this is the final result
                            be_hit = True
                            result = 'BE'
                            result_idx = i
                            be_hit_idx = i
                            # Use SL target value instead of actual high if high is worse
                            final_dist_sl = max(dist_sl, sl_target)
                            final_dist_tp = dist_tp
                        else:
                            # Original SL was hit
                            result = 'SL'
                            result_idx = i
                            # Use SL target value instead of actual high if high is worse
                            final_dist_sl = max(dist_sl, sl_target)
                            final_dist_tp = dist_tp
            
            # Add distance info to the line
            line_content = lines[i].rstrip()
            # Remove any previously added data (in case of re-running)
            if ' gain' in line_content or ' loss' in line_content:
                # Get base line without any added data
                base_line = ';'.join(line_content.split(';')[:5])
            else:
                base_line = line_content
            
            # Calculate current gain/loss for this candle
            current_gain_loss = dist_tp if dist_tp > 0 else dist_sl
            gain_loss_label = "gain" if current_gain_loss > 0 else "loss"
            
            if i == result_idx:
                # Add final result marker with gain/loss
                lines[i] = f"{base_line} {gain_loss_label} {(current_gain_loss):.2f} {result}\n"
            elif result is None:
                # Check if this is the candle where SL moved to BE
                if sl_be_moved_idx is not None and i == sl_be_moved_idx:
                    lines[i] = f"{base_line} {gain_loss_label} {(current_gain_loss):.2f} SL->BE\n"
                else:
                    lines[i] = f"{base_line} {gain_loss_label} {(current_gain_loss):.2f}\n"
            # After final result, don't add anything
        
        except (ValueError, IndexError):
            continue
    
    # Determine final result and calculate actual gain/loss
    if result == 'TP':
        final_result = 'TP'
        gain_loss = final_dist_tp  # Actual distance to TP when hit
    elif result == 'SL':
        final_result = 'SL'
        gain_loss = final_dist_sl  # Actual distance to SL when hit (negative)
    elif result == 'BE':
        final_result = 'BE'
        gain_loss = final_dist_sl  # Actual distance when BE was hit (should be ~0)
    elif be_hit:
        final_result = 'BE'
        gain_loss = final_dist_sl  # Actual distance when BE was hit (should be ~0)
    else:
        # Calculate result based on last close price for trades that didn't hit TP/SL/BE
        if signal == 'BUY':
            close_gain_loss = last_close_price - entry_price
        else:  # SELL
            close_gain_loss = entry_price - last_close_price
        
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
    
    if gain_loss > 0:
        result_text = f"GAIN +{gain_loss:.2f}"
    elif gain_loss < 0:
        result_text = f"LOSS {gain_loss:.2f}"
    else:
        result_text = f"BREAK EVEN {gain_loss:.2f}"
    
    # Don't print individual file results anymore, just return the data
    return final_result, bad_luck, gain_loss  # Return the result, bad_luck flag, and gain/loss for statistics

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
    
    # Redirect all print statements to a string buffer
    output_buffer = StringIO()
    original_stdout = sys.stdout
    sys.stdout = output_buffer

    if revert:
        for mod_file in mod_files:
            revert_mod_file(mod_file)
            time.sleep(0.01)
    else:
        # Track statistics
        results = {'TP': 0, 'SL': 0, 'BE': 0, 'Profiting': 0, 'Losing': 0, 'None': 0}
        files_by_category = {'TP': [], 'SL': [], 'BE': [], 'Profiting': [], 'Losing': [], 'None': []}
        bad_luck_count = 0
        total_gain_loss = 0
        
        processed_count = 0
        for mod_file in mod_files:
            result, is_bad_luck, gain_loss = process_mod_file(mod_file)
            processed_count += 1
            
            if result:
                results[result] += 1
                files_by_category[result].append((str(mod_file), gain_loss))
                total_gain_loss += gain_loss
            else:
                results['None'] += 1
                files_by_category['None'].append((str(mod_file), 0))
            
            if is_bad_luck:
                bad_luck_count += 1
            
            time.sleep(0.01)
        
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
        for filepath, gain_loss in sorted(files_by_category['TP'], key=lambda x: x[1], reverse=True):
            print(f"  - {filepath}: {gain_loss:+.2f}")
        
        print(f"Profiting (open):  {results['Profiting']:3d} trades")
        for filepath, gain_loss in sorted(files_by_category['Profiting'], key=lambda x: x[1], reverse=True):
            print(f"  - {filepath}: {gain_loss:+.2f}")
            
        print(f"BE (Break Even):   {results['BE']:3d} trades")
        for filepath, gain_loss in sorted(files_by_category['BE'], key=lambda x: x[1], reverse=True):
            print(f"  - {filepath}: {gain_loss:+.2f}")      

        print(f"Losing (open):     {results['Losing']:3d} trades")
        for filepath, gain_loss in sorted(files_by_category['Losing'], key=lambda x: x[1]):
            print(f"  - {filepath}: {gain_loss:+.2f}")
            
        print(f"SL (Stop Loss):    {results['SL']:3d} trades")
        for filepath, gain_loss in sorted(files_by_category['SL'], key=lambda x: x[1]):
            print(f"  - {filepath}: {gain_loss:+.2f}")
        
        if results['None'] > 0:
            print(f"No Result:         {results['None']:3d} trades")
            for filepath, gain_loss in sorted(files_by_category['None'], key=lambda x: x[0]):
                print(f"  - {filepath}")
                
        print(f"{'-'*50}")
        print(f"Bad Luck Trades:   {bad_luck_count:3d} trades")
        print(f"{'='*50}")
        total_closed = results['TP'] + results['BE'] + results['SL']
        if total_closed > 0:
            wins = results['TP'] + results['Profiting']
            losses = results['SL'] + results['Losing']
            win_rate = (wins / total_trades) * 100
            loss_rate = (losses / total_trades) * 100
            print(f"Win Rate: {win_rate:.1f}% ({wins}/{total_trades}) [TP + Profiting]")
            print(f"Loss Rate: {loss_rate:.1f}% ({losses}/{total_trades}) [SL + Losing]")
        print(f"Total P/L: {total_gain_loss:+.2f} points")
        print(f"{'='*50}")
    
    print(f"\n{'Revert' if revert else 'Analysis'} complete!")
    
    # Restore stdout and write to log file
    sys.stdout = original_stdout
    log_content = output_buffer.getvalue()
    output_buffer.close()
    
    # Write to analyze.log
    log_file = Path(__file__).parent / "analyze.log"
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(log_content)
    
    # Print the log file to screen
    print(log_content, end='')

if __name__ == "__main__":
    main()
