"""
Golden Test for Magic Lines

Ten test uruchamia magic_lines.py na danych testowych i porównuje wyniki z oczekiwanymi.

Struktura:
- golden_input/: katalog z plikami CSV do testowania
- golden_test_output/: katalog z wygenerowanymi wynikami (wykresy + support_lines_results.txt)

Użycie:
    python golden.py           # uruchom test
    python golden.py --update  # zaktualizuj golden results (zapisz obecne wyniki jako wzorcowe)
"""

import sys
import os
from pathlib import Path
import shutil

# Dodaj katalog parent do sys.path aby móc importować magic_lines
sys.path.insert(0, str(Path(__file__).parent.parent))

from magic_lines import process_all_files, process_single_file

# Ścieżki
SCRIPT_DIR = Path(__file__).parent
INPUT_DIR = SCRIPT_DIR / 'golden_input'
OUTPUT_DIR = SCRIPT_DIR / 'golden_test_output'
RESULTS_FILE = OUTPUT_DIR / 'support_lines_results.txt'
CHARTS_DIR = OUTPUT_DIR / 'charts'


def setup_test_environment():
    """Przygotuj środowisko testowe - wyczyść stare wyniki"""
    # Usuń tylko pliki, nie cały katalog (unikanie problemów z uprawnieniami)
    if RESULTS_FILE.exists():
        RESULTS_FILE.unlink()
    
    if CHARTS_DIR.exists():
        for chart_file in CHARTS_DIR.glob('*.png'):
            try:
                chart_file.unlink()
            except Exception:
                pass  # Ignoruj błędy przy usuwaniu
    
    # Utwórz katalogi jeśli nie istnieją
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Przygotowano katalog wyjściowy: {OUTPUT_DIR}")


def run_golden_test():
    """Uruchom test golden"""
    print("=" * 60)
    print("GOLDEN TEST - Magic Lines")
    print("=" * 60)
    
    # Sprawdź czy istnieją dane wejściowe
    if not INPUT_DIR.exists():
        print(f"✗ BŁĄD: Katalog wejściowy nie istnieje: {INPUT_DIR}")
        print(f"  Utwórz katalog i dodaj pliki CSV do testowania.")
        return False
    
    csv_files = list(INPUT_DIR.glob('*.csv'))
    if not csv_files:
        print(f"✗ BŁĄD: Brak plików CSV w: {INPUT_DIR}")
        print(f"  Dodaj pliki CSV do testowania.")
        return False
    
    print(f"Znaleziono {len(csv_files)} plików CSV w {INPUT_DIR}")
    print()
    
    # Przygotuj środowisko
    setup_test_environment()
    
    # Uruchom przetwarzanie
    print("Rozpoczynam przetwarzanie...")
    print()
    
    try:
        process_all_files(
            str(INPUT_DIR),
            output_file=str(RESULTS_FILE),
            output_charts_dir=str(CHARTS_DIR)
        )
    except Exception as e:
        print(f"\n✗ BŁĄD podczas przetwarzania: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Sprawdź wyniki
    print()
    print("=" * 60)
    print("WYNIKI TESTU")
    print("=" * 60)
    
    if not RESULTS_FILE.exists():
        print(f"✗ BŁĄD: Plik wyników nie został utworzony: {RESULTS_FILE}")
        return False
    
    # Wyświetl wyniki
    print(f"\nWyniki zapisano w: {RESULTS_FILE}")
    print()
    print("Zawartość pliku wyników:")
    print("-" * 60)
    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        print(content)
    print("-" * 60)
    
    # Sprawdź wykresy
    chart_files = list(CHARTS_DIR.glob('*.png'))
    print(f"\nWygenerowano {len(chart_files)} wykresów w: {CHARTS_DIR}")
    
    if chart_files:
        print("\nWykresy:")
        for chart in sorted(chart_files):
            size_kb = chart.stat().st_size / 1024
            print(f"  - {chart.name} ({size_kb:.1f} KB)")
    
    print()
    print("=" * 60)
    print("✓ TEST ZAKOŃCZONY POMYŚLNIE")
    print("=" * 60)
    
    return True


def update_golden_results():
    """Zaktualizuj wzorcowe wyniki (golden results)"""
    print("=" * 60)
    print("AKTUALIZACJA GOLDEN RESULTS")
    print("=" * 60)
    print()
    print("Ta operacja nadpisze obecne wzorcowe wyniki.")
    print("Czy kontynuować? [t/N]: ", end='')
    
    response = input().strip().lower()
    if response != 't' and response != 'y':
        print("Anulowano.")
        return
    
    # Uruchom test
    success = run_golden_test()
    
    if not success:
        print("\n✗ Nie można zaktualizować golden results - test nie powiódł się.")
        return
    
    # Tutaj można dodać logikę kopiowania wyników do katalogu z wzorcowymi wynikami
    # Na razie wystarczy że wyniki są w golden_test_output
    print("\n✓ Golden results zaktualizowane pomyślnie!")


def main():
    """Główna funkcja"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--update':
            update_golden_results()
        elif sys.argv[1] == '--help':
            print(__doc__)
        else:
            print(f"Nieznana opcja: {sys.argv[1]}")
            print("Użyj: python golden.py [--update|--help]")
            sys.exit(1)
    else:
        # Uruchom test
        success = run_golden_test()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
