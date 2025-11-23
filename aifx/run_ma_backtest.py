import pandas as pd
import sys
from ma_cross_strategy import MACrossStrategy
from backtest_engine import BacktestEngine

def load_data(filepath):
    """Wczytuje dane z pliku CSV/TSV"""
    df = pd.read_csv(filepath, sep='\t')
    # Kolumny mają < > w nazwach
    df['DateTime'] = pd.to_datetime(df['<DATE>'] + ' ' + df['<TIME>'])
    df = df.rename(columns={
        '<OPEN>': 'Open',
        '<HIGH>': 'High',
        '<LOW>': 'Low',
        '<CLOSE>': 'Close',
        '<TICKVOL>': 'Volume'
    })
    return df[['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()

def print_stats(results):
    """
    Wyświetla statystyki backtestingu
    
    Psychologia: Prezentacja wyników wpływa na percepcję strategii.
    Te same dane można pokazać jako "40% win rate" (pesymistycznie) 
    lub "R:R 2.5 daje profit mimo 40% WR" (optymistycznie).
    """
    stats = results['stats']
    
    print("\n" + "="*60)
    print("WYNIKI BACKTESTINGU - MA CROSSING STRATEGY")
    print("="*60)
    
    print(f"\n📊 PODSTAWOWE STATYSTYKI:")
    print(f"  Total Trades: {stats['total_trades']}")
    print(f"  Wins: {stats['wins']} | Losses: {stats['losses']}")
    print(f"  Win Rate: {stats['win_rate']:.1f}%")
    
    print(f"\n💰 WYNIKI W PIPSACH:")
    print(f"  Total Pips: {stats['total_pips']:.2f}")
    print(f"  Avg Win: {stats['avg_win_pips']:.2f} pips")
    print(f"  Avg Loss: {stats['avg_loss_pips']:.2f} pips")
    
    print(f"\n💵 WYNIKI FINANSOWE:")
    print(f"  Initial Capital: ${stats.get('initial_capital', 10000):.2f}")
    print(f"  Final Capital: ${stats['final_capital']:.2f}")
    print(f"  Total P&L: ${stats['total_pnl']:.2f}")
    print(f"  Return: {stats['return_pct']:.2f}%")
    
    print(f"\n📉 RYZYKO:")
    print(f"  Max Drawdown: {stats['max_drawdown_pct']:.2f}%")
    
    if stats['avg_loss_pips'] != 0:
        profit_factor = abs(stats['avg_win_pips'] / stats['avg_loss_pips'])
        print(f"  Profit Factor (pips): {profit_factor:.2f}")
    
    # Psychologiczna interpretacja
    print(f"\n🧠 PSYCHOLOGIA WYNIKÓW:")
    if stats['win_rate'] < 50:
        print(f"  ⚠️  Win rate <50% - wymaga dyscypliny w trzymaniu TP")
        print(f"      (naturalna tendencja: cut winners, let losers run)")
    else:
        print(f"  ✓ Win rate >50% - psychologicznie łatwiejsza do tradowania")
    
    if stats['max_drawdown_pct'] < -10:
        dd_val = abs(stats['max_drawdown_pct'])
        print(f"  ⚠️  DD >{dd_val:.0f}% - test emocjonalnej wytrzymałości")
    else:
        print(f"  ✓ Umiarkowany DD - łatwiejszy do wytrzymania psychicznie")
    
    print("\n" + "="*60)

def print_trades(results, show_all=False):
    """Wyświetla listę transakcji"""
    trades = results['trades']
    
    print(f"\n📋 LISTA TRANSAKCJI (pokazuję {'wszystkie' if show_all else 'pierwsze 10'}):")
    print("-" * 120)
    
    for i, trade in enumerate(trades[:None if show_all else 10]):
        result_icon = "✓" if trade['result'] == 'TP' else "✗"
        direction_icon = "↑" if trade['direction'] == 'long' else "↓"
        
        print(f"{result_icon} #{i+1} | {trade['time']} | {direction_icon} {trade['direction'].upper():5s} | "
              f"Entry: {trade['entry_price']:8.2f} | Exit: {trade['exit_price']:8.2f} | "
              f"Pips: {trade['pips']:6.2f} | P&L: ${trade['pnl']:7.2f} | "
              f"Capital: ${trade['capital_after']:,.2f}")
    
    if not show_all and len(trades) > 10:
        print(f"... i {len(trades) - 10} więcej transakcji")
    
    print("-" * 120)

def main():
    # Parametry
    default_data_file = 'FUS100.15.csv'
    
    # Parsing argumentów (opcjonalnie)
    start_date = sys.argv[1] if len(sys.argv) > 1 else '2025-10-01'
    end_date = sys.argv[2] if len(sys.argv) > 2 else '2025-10-31'
    data_file = sys.argv[3] if len(sys.argv) > 3 else default_data_file
    
    print(f"Backtest: {start_date} do {end_date}")
    print(f"Data file: {data_file}")
    print("Strategia: MA Crossing (20/50) | R:R 2:5 | Risk: 20 pips")
    
    # Load data
    print(f"\nWczytuję dane z {data_file}...")
    df = load_data(data_file)
    print(f"Załadowano {len(df)} świeczek")
    
    # Inicjalizuj strategię i silnik
    strategy = MACrossStrategy(
        fast_period=20,
        slow_period=50,
        risk_pips=20,      # SL = 20 pips
        reward_ratio=2.5   # TP = 50 pips (20 * 2.5)
    )
    
    engine = BacktestEngine(
        initial_capital=10000,
        risk_per_trade_pct=2.0  # 2% kapitału na trade
    )
    
    # Uruchom backtest
    print("\nUruchamiam backtest...")
    results = engine.run(df, strategy, start_date, end_date)
    
    # Wyświetl wyniki
    print_stats(results)
    print_trades(results, show_all=False)
    
    # Zapisz szczegóły
    if results['trades']:
        trades_df = pd.DataFrame(results['trades'])
        output_file = f'backtest_results_{start_date}_to_{end_date}.csv'
        trades_df.to_csv(output_file, index=False)
        print(f"\n💾 Szczegóły transakcji zapisane w: {output_file}")

if __name__ == '__main__':
    main()
