import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import datetime

def generate_chart(csv_file, start_date, end_date, output_file='chart.png'):
    """
    Generuje wykres świecowy Nasdaq 100 dla podanego zakresu dat.
    
    Parametry:
    csv_file: ścieżka do pliku CSV z danymi
    start_date: data początkowa (format: 'YYYY-MM-DD' lub 'YYYY-MM-DD HH:MM')
    end_date: data końcowa (format: 'YYYY-MM-DD' lub 'YYYY-MM-DD HH:MM')
    output_file: nazwa pliku wyjściowego (domyślnie 'chart.png')
    """
    
    # Wczytaj dane
    print(f"Wczytuję dane z {csv_file}...")
    df = pd.read_csv(csv_file, 
                     sep='\t',  # Separator to tabulator
                     skiprows=1,  # Pomiń nagłówek
                     names=['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'TickVol', 'Vol', 'Spread'])
    
    # Użyj tylko potrzebnych kolumn
    df = df[['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'TickVol']]
    df.rename(columns={'TickVol': 'Volume'}, inplace=True)
    
    # Połącz Date i Time w Datetime
    df['Datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
    df = df.set_index('Datetime')
    df = df.drop(['Date', 'Time'], axis=1)
    
    # Posortuj indeks
    df = df.sort_index()
    
    print(f"Załadowano {len(df)} świeczek")
    print(f"Zakres danych: {df.index.min()} do {df.index.max()}")
    
    # Filtruj dane według zakresu
    df_filtered = df.loc[start_date:end_date]
    
    if len(df_filtered) == 0:
        print(f"UWAGA: Brak danych dla zakresu {start_date} - {end_date}")
        return
    
    print(f"Wybrany zakres: {len(df_filtered)} świeczek ({df_filtered.index.min()} - {df_filtered.index.max()})")
    
    # Konfiguracja wykresu
    mc = mpf.make_marketcolors(up='g', down='r', edge='inherit', wick='inherit', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True)
    
    # Generuj wykres
    print(f"Generuję wykres...")
    mpf.plot(df_filtered, 
             type='candle', 
             style=s,
             title=f'Nasdaq 100 (M15) - {start_date} do {end_date}',
             ylabel='Cena',
             volume=True,
             ylabel_lower='Wolumen',
             figsize=(16, 9),
             warn_too_much_data=10000,  # Wyłącz ostrzeżenie dla dużej ilości danych
             savefig=output_file)
    
    print(f"✓ Wykres zapisany jako: {output_file}")
    
    # Statystyki zakresu
    print(f"\n--- Statystyki ---")
    print(f"Open pierwszej świeczki: {df_filtered['Open'].iloc[0]:.2f}")
    print(f"Close ostatniej świeczki: {df_filtered['Close'].iloc[-1]:.2f}")
    print(f"High zakresu: {df_filtered['High'].max():.2f}")
    print(f"Low zakresu: {df_filtered['Low'].min():.2f}")
    print(f"Zmiana: {df_filtered['Close'].iloc[-1] - df_filtered['Open'].iloc[0]:.2f} punktów")
    print(f"Zmiana %: {((df_filtered['Close'].iloc[-1] / df_filtered['Open'].iloc[0]) - 1) * 100:.2f}%")


if __name__ == "__main__":
    # Wygeneruj wykres dla 3-7 października 2025 (pełny tydzień z kontekstem)
    generate_chart('FUS100.15.csv', 
                   start_date='2025-10-03', 
                   end_date='2025-10-07',
                   output_file='nasdaq_oct_3-7_2025.png')
