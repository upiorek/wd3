"""
Skrypt do przetwarzania wszystkich plików CSV z katalogu m15_candles
"""

import os
import subprocess
from pathlib import Path

# Ścieżka do katalogu z plikami CSV
csv_dir = Path("tester-third/mt4_test_results/m15_candles")
output_file = "support_lines_results.txt"

# Znajdź wszystkie pliki CSV
csv_files = sorted(csv_dir.glob("*.csv"))
total = len(csv_files)

print(f"Znaleziono {total} plików CSV")
print(f"Rozpoczynam przetwarzanie...\n")

# Otwórz plik wyjściowy
with open(output_file, 'w', encoding='utf-8') as f:
    for i, csv_file in enumerate(csv_files, 1):
        print(f"[{i}/{total}] Przetwarzam: {csv_file.name}")
        
        # Uruchom skrypt dla każdego pliku
        result = subprocess.run(
            ['python', 'calculate_support_lines_min.py', str(csv_file)],
            capture_output=True,
            text=True
        )
        
        # Zapisz wynik
        output = result.stdout.strip() if result.stdout else result.stderr.strip()
        f.write(f"{csv_file.name}: {output}\n")

print(f"\n✓ Gotowe! Wyniki zapisano w: {output_file}")
print(f"Przetworzono {total} plików")
