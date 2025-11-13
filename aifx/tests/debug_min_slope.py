import sys
import json

# Symuluj uruchomienie: python run_support_backtest.py config_example.json
sys.argv = ['run_support_backtest.py', 'config_example.json']

# Default options (jak w run_support_backtest.py line 99)
default_options = {
    'min_slope': 0.1,
}

# Wczytaj config
config_file = sys.argv[1]
print(f"Wczytuję konfigurację z {config_file}...")
with open(config_file, 'r') as f:
    options = json.load(f)

print(f"PRZED merge - options['min_slope']: {options.get('min_slope', 'BRAK')}")
print(f"PRZED merge - default_options['min_slope']: {default_options['min_slope']}")

# Merge z defaults (jak w run_support_backtest.py line 126)
options = {**default_options, **options}

print(f"PO merge - options['min_slope']: {options['min_slope']}")

# Ten print to linia 161 w run_support_backtest.py
print(f"Lookback: {options.get('lookback_days', '?')} dni, Min slope: {options['min_slope']}")
