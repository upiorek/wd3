#!/usr/bin/env python3
"""
Convert CSV format from:
  2024.11.18 15:15;20579.36;20586.14;20555.08;20557.86
To:
  2024.11.18,15:15,20579.36,20586.14,20555.08,20557.86,0
"""

import os
import sys

def convert_csv_format(input_file, output_file=None):
    """Convert CSV from semicolon-separated to comma-separated format."""
    
    if output_file is None:
        output_file = input_file.replace('.csv', '_converted.csv')
        if output_file == input_file:
            output_file = input_file + '_converted'
    
    print(f"Reading {input_file}...")
    
    converted_count = 0
    
    with open(input_file, 'r') as inf, open(output_file, 'w') as outf:
        for line_num, line in enumerate(inf, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                # Parse: YYYY.MM.DD HH:MM;open;high;low;close
                parts = line.split(';')
                
                if len(parts) < 5:
                    print(f"Warning: Line {line_num} has insufficient columns, skipping")
                    continue
                
                datetime_part = parts[0]  # "YYYY.MM.DD HH:MM"
                open_price = parts[1]
                high_price = parts[2]
                low_price = parts[3]
                close_price = parts[4]
                
                # Split date and time
                date_time_split = datetime_part.split(' ')
                if len(date_time_split) != 2:
                    print(f"Warning: Line {line_num} has invalid date/time format, skipping")
                    continue
                
                date = date_time_split[0]
                time = date_time_split[1]
                
                # Create new format: YYYY.MM.DD,HH:MM,open,high,low,close,volume (volume=0)
                new_line = f"{date},{time},{open_price},{high_price},{low_price},{close_price},0\n"
                outf.write(new_line)
                
                converted_count += 1
                
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
                continue
    
    print(f"Converted {converted_count} lines")
    print(f"Output written to: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 convert_csv_format.py <input_file> [output_file]")
        print("Example: python3 convert_csv_format.py US100.f15.csv_data")
        exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        exit(1)
    
    convert_csv_format(input_file, output_file)
    print("\nDone!")
