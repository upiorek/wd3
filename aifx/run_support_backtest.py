import pandas as pd
import sys
import os
import shutil
import json
import logging
from support_breakout_strategy import SupportBreakoutStrategy
from backtest_engine import BacktestEngine

def load_data(filepath):
    """Wczytuje dane z pliku CSV/TSV"""
    df = pd.read_csv(filepath, sep='\t')
    df['DateTime'] = pd.to_datetime(df['<DATE>'] + ' ' + df['<TIME>'])
    df = df.rename(columns={
        '<OPEN>': 'Open',
        '<HIGH>': 'High',
        '<LOW>': 'Low',
        '<CLOSE>': 'Close',
        '<TICKVOL>': 'Volume'
    })
    return df[['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()

def print_stats(results, mode_name):
    """Wyświetla statystyki"""
    stats = results['stats']
    
    print("\n" + "="*60)
    print(f"WYNIKI - SUPPORT BREAKOUT ({mode_name})")
    print("="*60)
    
    print(f"\n📊 STATYSTYKI:")
    print(f"  Total Trades: {stats['total_trades']}")
    
    if stats['total_trades'] > 0:
        print(f"  Wins: {stats['wins']} | Losses: {stats['losses']}")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
    
    print(f"\n💰 PIPSY:")
    print(f"  Total: {stats['total_pips']:.2f}")
    print(f"  Avg Win: {stats['avg_win_pips']:.2f} | Avg Loss: {stats['avg_loss_pips']:.2f}")
    
    print(f"\n💵 P&L:")
    print(f"  Total: ${stats['total_pnl']:.2f}")
    print(f"  Return: {stats['return_pct']:.2f}%")
    print(f"  Max DD: {stats['max_drawdown_pct']:.2f}%")
    
    # Analiza psychologiczna
    if stats['total_trades'] > 0:
        print(f"\n🧠 ANALIZA:")
        
        # Consecutive losses (psychologiczny test)
        trades_df = pd.DataFrame(results['trades'])
        trades_df['is_loss'] = trades_df['result'] == 'SL'
        
        max_consecutive_losses = 0
        current_streak = 0
        for is_loss in trades_df['is_loss']:
            if is_loss:
                current_streak += 1
                max_consecutive_losses = max(max_consecutive_losses, current_streak)
            else:
                current_streak = 0
        
        print(f"  Max consecutive losses: {max_consecutive_losses}")
        if max_consecutive_losses >= 5:
            print(f"    ⚠️ Seria {max_consecutive_losses} strat testuje dyscyplinę")
        
        # False breakouts (wróciło pod support)
        print(f"\n  Detailed trades analysis needed for false breakout %")
    
    print("\n" + "="*60)

def print_sample_trades(results, n=5):
    """Pokazuje przykładowe transakcje"""
    trades = results['trades']
    
    if not trades:
        print("\nBrak transakcji")
        return
    
    print(f"\n📋 Pierwsze {min(n, len(trades))} transakcji:")
    print("-" * 100)
    
    for i, trade in enumerate(trades[:n]):
        result_icon = "✓" if trade['result'] == 'TP' else "✗"
        print(f"{result_icon} {trade['time']} | Entry: {trade['entry_price']:.2f} | "
              f"Exit: {trade['exit_price']:.2f} | Pips: {trade['pips']:6.2f} | "
              f"P&L: ${trade['pnl']:7.2f}")
    
    if len(trades) > n:
        print(f"... i {len(trades) - n} więcej")
    print("-" * 100)

def main():
    data_file = 'FUS100.15.csv'
    charts_dir = 'support_charts'
    
    # Domyślne opcje
    default_options = {
        'start_date': None,
        'end_date': None,
        'lookback_days': 5,
        'risk_pips': 20,
        'reward_ratio': 2.5,
        'retest_mode': False,
        'initial_capital': 10000,
        'risk_per_trade_pct': 2.0,
        'min_slope': 0.1,
        'show_volume': True,
        'generate_charts': True
    }
    
    # Parametry z linii komend
    if len(sys.argv) > 1 and sys.argv[1].endswith('.json'):
        # Format: python run_support_backtest.py config.json
        config_file = sys.argv[1]
        
        print(f"Wczytuję konfigurację z {config_file}...")
        with open(config_file, 'r') as f:
            options = json.load(f)
        # Merge z defaults
        options = {**default_options, **options}
        
        start_date = options['start_date']
        end_date = options['end_date']
        
        if not start_date or not end_date:
            print("Błąd: start_date i end_date muszą być w pliku JSON")
            return
            
    elif len(sys.argv) > 3 and sys.argv[3].endswith('.json'):
        # Format: python run_support_backtest.py start_date end_date config.json
        start_date = sys.argv[1]
        end_date = sys.argv[2]
        config_file = sys.argv[3]
        
        print(f"Wczytuję konfigurację z {config_file}...")
        with open(config_file, 'r') as f:
            options = json.load(f)
        # Merge z defaults (daty z linii komend mają priorytet)
        options = {**default_options, **options}
        options['start_date'] = start_date
        options['end_date'] = end_date
        
    elif len(sys.argv) > 2:
        # Format: python run_support_backtest.py start_date end_date
        start_date = sys.argv[1]
        end_date = sys.argv[2]
        options = default_options
    else:
        # Domyślnie ostatnie 10 dni
        end_date = '2025-11-07'  # ostatni dzień w danych
        start_date = '2025-10-28'  # 10 dni wstecz
        options = default_options
    
    print(f"Support Breakout Backtest: {start_date} do {end_date}")
    print(f"Lookback: {options['lookback_days']} dni, R:R {options['reward_ratio']}, Risk: {options['risk_pips']} pips, Min slope: {options['min_slope']}")
    
    # Wyczyść folder z wykresami
    if os.path.exists(charts_dir):
        try:
            shutil.rmtree(charts_dir)
        except PermissionError:
            # Folder otwarty - usuń tylko pliki wewnątrz
            for file in os.listdir(charts_dir):
                try:
                    os.remove(os.path.join(charts_dir, file))
                except:
                    pass
    os.makedirs(charts_dir, exist_ok=True)
    
    # Load data
    print(f"\nWczytuję dane...")
    df = load_data(data_file)
    print(f"Załadowano {len(df)} świeczek")
    
    # Strategia - immediate breakout
    strategy = SupportBreakoutStrategy(
        lookback_days=options['lookback_days'],
        risk_pips=options['risk_pips'],
        reward_ratio=options['reward_ratio'],
        retest_mode=options['retest_mode']
    )

    # Get module-level logger (handler is configured inside BacktestEngine or Strategy)
    logger = logging.getLogger('aifx_debug')
    
    engine = BacktestEngine(
        initial_capital=options['initial_capital'],
        risk_per_trade_pct=options['risk_per_trade_pct']
    )
    
    # Uruchom backtest
    print("\nUruchamiam backtest...")
    print(f"Dane przed calculate_indicators: {len(df)} świeczek")
    print(f"Zakres dat w pliku: {df['DateTime'].min()} - {df['DateTime'].max()}")
    results = engine.run(df, strategy, start_date, end_date)
    
    # Wyniki
    print_stats(results, "IMMEDIATE")
    print_sample_trades(results, n=10)
    
    # Generuj wykresy dla każdego dnia w zakresie (opcjonalnie)
    if options['generate_charts']:
        print(f"\n📊 Generuję wykresy...")
        print(f"Daily support data entries: {len(strategy.daily_support_data)}")
        if strategy.daily_support_data:
            # Write dates list to debug log instead of printing to console
            logger.debug(f"Daty z support data: {[str(d['date']) for d in strategy.daily_support_data]}")
        
        # Użyj PEŁNEGO df (nie filtrowanego) dla poprawnego obliczenia dni handlowych
        df_full = load_data(data_file)
        
        # Pobierz unikalne daty z daily_support_data (dni dla których mamy support)
        support_dates = [info['date'] for info in strategy.daily_support_data]
        
        print(f"Zakres backtestingu: {start_date} - {end_date}")
        print(f"Dni z obliczonym support: {len(support_dates)}")
        
        charts_generated = 0
        
        for date in support_dates:
            filename = strategy.plot_daily_chart(df_full, date, output_dir=charts_dir, show_volume=options['show_volume'])
            if filename:
                charts_generated += 1
                print(f"  ✓ {filename}")
        
        print(f"\n✓ Wygenerowano {charts_generated} wykresów w folderze {charts_dir}/")
    else:
        print(f"\n⊘ Generowanie wykresów wyłączone (generate_charts: false)")
    
    # Zapisz CSV z transakcjami
    if results['trades']:
        trades_df = pd.DataFrame(results['trades'])
        
        # CSV w folderze z wykresami (w katalogu roboczym)
        charts_csv = f'{charts_dir}/summary_{start_date}_to_{end_date}.csv'
        trades_df.to_csv(charts_csv, index=False)
        print(f"💾 Zapisano: {charts_csv}")

if __name__ == '__main__':
    main()
