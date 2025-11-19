"""
Data classes i konfiguracja dla Support Breakout Strategy.

Refactoring: Configuration Object + Data Classes
- StrategyConfig: wszystkie parametry strategii w jednym miejscu
- Point: reprezentacja punktu na wykresie
- HierarchicalLine: linia hierarchiczna (S2, S3, R2, R3)
- SupportLine: główna linia support/resistance z hierarchią
- TradeSignal: sygnał wejścia w trade
"""

from dataclasses import dataclass, field
from typing import List, Optional, Literal
from datetime import datetime, date


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class StrategyConfig:
    """
    Konfiguracja strategii Support Breakout.
    
    Użycie:
        config = StrategyConfig(lookback_days=3, risk_pips=30)
        strategy = SupportBreakoutStrategy(config)
    """
    # Lookback window
    lookback_days: int = 5
    
    # Risk management
    risk_pips: int = 50
    reward_ratio: int = 3
    
    # Breakout mode
    retest_mode: bool = False
    retest_tolerance: int = 30
    
    # Line detection
    min_slope: float = 0.1
    allow_descending: bool = True
    
    # Hierarchical levels
    hierarchical_levels_below: int = 4
    hierarchical_levels_above: int = 4
    hierarchical_tolerance: int = 30
    
    # Visualization
    show_legend: bool = True
    chart_dpi: int = 150
    
    # Trading rules
    close_at_eod: bool = False
    
    # Constants
    CANDLES_PER_DAY_M15: int = 96
    EXTREMA_ORDER: int = 5
    DEFAULT_TOLERANCE_PIPS: int = 30
    
    @property
    def lookback_candles(self) -> int:
        """Liczba świeczek w oknie lookback."""
        return self.lookback_days * self.CANDLES_PER_DAY_M15
    
    @property
    def reward_pips(self) -> int:
        """Docelowy zysk w pipsach."""
        return self.risk_pips * self.reward_ratio


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Point:
    """
    Punkt na wykresie (minima, maxima, impulse).
    """
    index: int  # Pozycja w DataFrame (offset od lookback_start)
    price: float  # Cena (Low dla support, High dla resistance)
    type: Literal['impulse', 'minimum', 'maximum', 'fallback'] = 'minimum'
    
    def __hash__(self):
        return hash((self.index, self.price))


@dataclass
class HierarchicalLine:
    """
    Linia hierarchiczna (S2, S3, R2, R3).
    Równoległa do głównej linii, przesunięta pionowo.
    """
    level: int  # 2, 3, 4... (S1/R1 to główna linia)
    slope: float
    intercept: float
    offset: float  # Przesunięcie względem głównej linii (w pipsach)
    touches: int  # Ile punktów dotyka tej linii
    score: float  # Jakość dopasowania
    direction: Literal['support', 'resistance']  # Poniżej (S) czy powyżej (R)
    
    def price_at(self, index: int) -> float:
        """Cena linii w danym indeksie."""
        return self.slope * index + self.intercept


@dataclass
class SupportLine:
    """
    Główna linia support/resistance z hierarchią.
    
    Zawiera:
    - Parametry głównej linii (slope, intercept)
    - Punkty użyte do dopasowania
    - Hierarchiczne linie równoległe (S2, S3, R2, R3)
    - Metadane (data, lookback range, impulsy)
    """
    # Identyfikacja
    date: date
    type: Literal['ascending', 'descending']
    
    # Główna linia (S1 lub R1)
    slope: float
    intercept: float
    score: float
    
    # Punkty dopasowania
    support_points: List[Point]
    all_minima: List[Point]
    local_maxima: List[Point]
    impulses: List[Point]
    
    # Hierarchiczne linie równoległe
    hierarchical_supports: List[HierarchicalLine] = field(default_factory=list)
    hierarchical_resistances: List[HierarchicalLine] = field(default_factory=list)
    
    # Metadane lookback window
    lookback_start_dt: datetime = None
    lookback_end_dt: datetime = None
    day_start_idx: int = 0
    
    def price_at(self, index: int) -> float:
        """Cena głównej linii w danym indeksie."""
        return self.slope * index + self.intercept
    
    def is_ascending(self) -> bool:
        """Czy linia wznosząca (LONG)."""
        return self.type == 'ascending'
    
    def is_descending(self) -> bool:
        """Czy linia opadająca (SHORT)."""
        return self.type == 'descending'


@dataclass
class TradeSignal:
    """
    Sygnał wejścia w trade (breakout).
    """
    direction: Literal['LONG', 'SHORT']
    entry_price: float
    stop_loss: float
    take_profit: float
    support_line: SupportLine
    candle_idx: int
    candle_time: datetime
    
    @property
    def risk_pips(self) -> float:
        """Ryzyko w pipsach."""
        return abs(self.entry_price - self.stop_loss)
    
    @property
    def reward_pips(self) -> float:
        """Potencjalny zysk w pipsach."""
        return abs(self.take_profit - self.entry_price)
