#!/usr/bin/env python3
"""
Convert CSV format from:
  2023.09.20;12:00;15405.87;15405.87;15397.63;15402.90;887
To:
  2026.01.02 21:30;25430.50;25438.98;25391.24;25392.48
"""

import os
import sys

def convert_csv_format(input_file, output_file=None):
    """Convert CSV from comma-separated to semicolon-separated format."""
    
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
                # Parse: YYYY.MM.DD;HH:MM;open;high;low;close;volume
                parts = None
                if ';' in line:
                    parts = line.split(';')
                elif ',' in line:
                    parts = line.split(',')
                
                if len(parts) < 6:
                    print(f"Warning: Line {line_num} has insufficient columns, skipping")
                    print(f"Line content: {line}")
                    print(f"len(parts): {len(parts)} parts: {parts}")
                    exit(1)
                
                date = parts[0]           # "YYYY.MM.DD"
                time = parts[1]           # "HH:MM"
                open_price = parts[2]
                high_price = parts[3]
                low_price = parts[4]
                close_price = parts[5]
                # volume = parts[6] if len(parts) > 6 else None  # Ignored
                
                # Create new format: YYYY.MM.DD HH:MM;open;high;low;close
                new_line = f"{date} {time};{open_price};{high_price};{low_price};{close_price}\n"
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
