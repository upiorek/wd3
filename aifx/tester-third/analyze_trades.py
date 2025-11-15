import os
import time
import sys
from pathlib import Path

def revert_mod_file(file_path):
    """Remove TP/SL markers and distance data from a _mod file."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    modified = False
    for i, line in enumerate(lines):
        # Skip header line
        if i == 0:
            continue
            
        stripped = line.rstrip()
        
        # Check if line has any added data (distSL, distTP, TP, SL, or BE)
        if ' dist' in stripped or ' TP' in stripped or ' SL' in stripped or ' BE' in stripped:
            # Split by semicolon to get the base CSV data
            parts = stripped.split(';')
            if len(parts) >= 5:
                # Keep only first 5 parts (Time;Open;High;Low;Close) - no Volume column
                base_parts = parts[:5]
                
                # Check if this is the signal line (should have BUY/SELL at the end)
                if i == 1:
                    # Check the Close field for BUY/SELL signal
                    close_field = base_parts[4]
                    if ' BUY' in close_field or ' SELL' in close_field:
                        # Preserve the signal
                        lines[i] = ';'.join(base_parts) + '\n'
                    else:
                        # Signal might be in the extra data, extract it
                        if ' BUY' in stripped:
                            base_parts[4] = base_parts[4].split()[0]  # Clean the close price
                            lines[i] = ';'.join(base_parts) + ' BUY\n'
                        elif ' SELL' in stripped:
                            base_parts[4] = base_parts[4].split()[0]  # Clean the close price
                            lines[i] = ';'.join(base_parts) + ' SELL\n'
                        else:
                            lines[i] = ';'.join(base_parts) + '\n'
                else:
                    # For other lines, just keep the base CSV data
                    # Clean the Close field if it has extra data
                    close_field = base_parts[4].split()[0]  # Take only the number
                    base_parts[4] = close_field
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
        return None, False
    
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
        return None, False
    
    # Get entry price (open price of next candle after signal)
    if signal_line_idx + 1 >= len(lines):
        print(f"No candles after signal in {file_path.name}")
        return None, False
    
    entry_candle = lines[signal_line_idx + 1].strip().split(';')
    if len(entry_candle) < 2:
        return None, False
    
    try:
        entry_price = float(entry_candle[1])
    except ValueError:
        return None, False
    
    tp_target = 200
    sl_target = -50
    be_trigger = 100  # Move SL to BE when TP distance reaches this
    sl_moved_to_be = False
    be_hit = False
    be_hit_idx = None
    result = None
    result_idx = None
    final_dist_sl = 0
    final_dist_tp = 0
    last_dist_sl = 0
    last_dist_tp = 0
    last_close_price = 0
    bad_luck = False  # Flag for when multiple outcomes could happen in same candle
    
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
                
                # Track last distances
                last_dist_sl = dist_sl
                last_dist_tp = dist_tp
                
                # Check if we should move SL to BE
                if not sl_moved_to_be and dist_tp >= be_trigger:
                    sl_moved_to_be = True
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
                        final_dist_sl = dist_sl
                        final_dist_tp = dist_tp
                    elif tp_hit:
                        result = 'TP'
                        result_idx = i
                        final_dist_tp = dist_tp
                        final_dist_sl = dist_sl
                    elif sl_hit:
                        if sl_moved_to_be and not be_hit:
                            # BE was hit, mark it but continue analyzing
                            be_hit = True
                            be_hit_idx = i
                            final_dist_sl = dist_sl
                            final_dist_tp = dist_tp
                        else:
                            # Original SL was hit
                            result = 'SL'
                            result_idx = i
                            final_dist_sl = dist_sl
                            final_dist_tp = dist_tp
            
            elif signal == 'SELL':
                # For SELL: TP is below entry, SL is above
                dist_tp = entry_price - low
                dist_sl = entry_price - high
                
                # Track last distances
                last_dist_sl = dist_sl
                last_dist_tp = dist_tp
                
                # Check if we should move SL to BE
                if not sl_moved_to_be and dist_tp >= be_trigger:
                    sl_moved_to_be = True
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
                        final_dist_sl = dist_sl
                        final_dist_tp = dist_tp
                    elif tp_hit:
                        result = 'TP'
                        result_idx = i
                        final_dist_tp = dist_tp
                        final_dist_sl = dist_sl
                    elif sl_hit:
                        if sl_moved_to_be and not be_hit:
                            # BE was hit, mark it but continue analyzing
                            be_hit = True
                            be_hit_idx = i
                            final_dist_sl = dist_sl
                            final_dist_tp = dist_tp
                        else:
                            # Original SL was hit
                            result = 'SL'
                            result_idx = i
                            final_dist_sl = dist_sl
                            final_dist_tp = dist_tp
            
            # Add distance info to the line
            line_content = lines[i].rstrip()
            # Remove any previously added data (in case of re-running)
            if ' dist' in line_content:
                # Get base line without any added data
                base_line = ';'.join(line_content.split(';')[:5])
            else:
                base_line = line_content
            
            if i == result_idx:
                # Add final result marker with distance info
                lines[i] = f"{base_line} distSL={dist_sl:.2f} distTP={dist_tp:.2f} {result}\n"
            elif i == be_hit_idx:
                # Mark where BE was hit, but continue analyzing
                lines[i] = f"{base_line} distSL={dist_sl:.2f} distTP={dist_tp:.2f} BE\n"
            elif result is None and not be_hit:
                # Only add distance info before BE/SL/TP is hit
                be_marker = " BE" if sl_moved_to_be else ""
                lines[i] = f"{base_line} distSL={dist_sl:.2f} distTP={dist_tp:.2f}{be_marker}\n"
            elif be_hit and result is None:
                # After BE hit, continue tracking to see if TP would have been hit
                lines[i] = f"{base_line} distSL={dist_sl:.2f} distTP={dist_tp:.2f} (after BE)\n"
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
        final_result = None
        gain_loss = 0
    
    # Write back to file
    with open(file_path, 'w') as f:
        f.writelines(lines)
    
    if final_result:
        if gain_loss > 0:
            result_text = f"GAIN +{gain_loss:.2f}"
        elif gain_loss < 0:
            result_text = f"LOSS {gain_loss:.2f}"
        else:
            result_text = f"BREAK EVEN {gain_loss:.2f}"
        
        bad_luck_marker = " BAD LUCK" if bad_luck else ""
        print(f"Processed: {file_path.name} - {signal} -> {final_result} ({result_text}){bad_luck_marker}")
    else:
        # Calculate result based on last close price
        close_gain_loss = last_close_price - entry_price
        if close_gain_loss > 0:
            result_text = f"GAIN +{close_gain_loss:.2f}"
        elif close_gain_loss < 0:
            result_text = f"LOSS {close_gain_loss:.2f}"
        else:
            result_text = f"BREAK EVEN {close_gain_loss:.2f}"
        print(f"Processed: {file_path.name} - {signal} -> LAST: Close ({result_text})")
    
    return final_result, bad_luck  # Return the result and bad_luck flag for statistics

def main():
    revert = len(sys.argv) > 1 and sys.argv[1] == "--revert"
    
    # Check for candles in mt4_test_results first, then fall back to m15_candles
    test_results_dir = Path(__file__).parent / "mt4_test_results" / "m15_candles"
    original_dir = Path(__file__).parent / "m15_candles"
    
    if test_results_dir.exists():
        candles_dir = test_results_dir
        print(f"Using MT4 test results: {candles_dir}")
    elif original_dir.exists():
        candles_dir = original_dir
        print(f"Using original candles: {candles_dir}")
    else:
        print(f"Directory not found: {test_results_dir}")
        print(f"Directory not found: {original_dir}")
        return
    
    # Get all _mod.csv files
    mod_files = sorted(candles_dir.glob("*_mod.csv"))
    
    print(f"Found {len(mod_files)} _mod files to {'revert' if revert else 'analyze'}\n")
    
    if revert:
        for mod_file in mod_files:
            revert_mod_file(mod_file)
            time.sleep(0.01)
    else:
        # Track statistics
        results = {'TP': 0, 'SL': 0, 'BE': 0, 'None': 0}
        bad_luck_count = 0
        
        for mod_file in mod_files:
            result, is_bad_luck = process_mod_file(mod_file)
            if result:
                results[result] += 1
            else:
                results['None'] += 1
            
            if is_bad_luck:
                bad_luck_count += 1
            
            time.sleep(0.01)
        
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
        print(f"BE (Break Even):   {results['BE']:3d} trades")
        print(f"SL (Stop Loss):    {results['SL']:3d} trades")
        print(f"No Result:         {results['None']:3d} trades")
        print(f"{'-'*50}")
        print(f"Bad Luck Trades:   {bad_luck_count:3d} trades")
        print(f"{'='*50}")
        total_closed = results['TP'] + results['BE'] + results['SL']
        if total_closed > 0:
            win_rate = (results['TP'] / total_closed) * 100
            print(f"Win Rate: {win_rate:.1f}% ({results['TP']}/{total_closed})")
            print(f"{'='*50}")
    
    print(f"\n{'Revert' if revert else 'Analysis'} complete!")

if __name__ == "__main__":
    main()
