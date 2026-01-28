"""
💰 LEVEL CALCULATOR - Calculates TP1/TP2/TP3/SL according to rules
Handles: percentages, pips, points, live prices
"""

import json
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass

@dataclass
class TradingLevels:
    """Structure of calculated levels"""
    direction: str
    asset: str
    timeframe: str
    entry: float
    tp1: float
    tp2: float
    tp3: float
    sl: float
    tp1_distance: float  # Distance in % or unit
    tp2_distance: float
    tp3_distance: float
    sl_distance: float
    unit: str  # '%', 'pips', 'points'
    rr_ratio: float  # Risk/Reward ratio average
    
    def to_dict(self) -> Dict:
        return {
            "direction": self.direction,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "entry": self.entry,
            "tp1": self.tp1,
            "tp2": self.tp2,
            "tp3": self.tp3,
            "sl": self.sl,
            "tp1_distance": self.tp1_distance,
            "tp2_distance": self.tp2_distance,
            "tp3_distance": self.tp3_distance,
            "sl_distance": self.sl_distance,
            "unit": self.unit,
            "rr_ratio": self.rr_ratio
        }


class LevelCalculator:
    """
    TP/SL Level Calculator
    
    Uses rules from config/rules.json to calculate
    exact levels based on asset, timeframe, and entry price
    """
    
    # Pip conversion for FOREX
    PIP_VALUES = {
        "EURUSD": 0.0001,
        "GBPUSD": 0.0001,
        "USDJPY": 0.01,
        "AUDUSD": 0.0001,
        "USDCAD": 0.0001,
        "USDCHF": 0.0001,
    }
    
    # Points for indices
    POINT_VALUES = {
        "US30": 1.0,
        "NAS100": 1.0,
        "SPX500": 0.1,
    }
    
    def __init__(self, config_path: str = "config/rules.json"):
        self.config = self._load_config(config_path)
    
    def _load_config(self, path: str) -> Dict:
        """Load configuration"""
        config_file = Path(path)
        if not config_file.exists():
            config_file = Path(__file__).parent.parent / "config" / "rules.json"
        
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def calculate(self, 
                  direction: str, 
                  asset: str, 
                  timeframe: str, 
                  entry_price: float) -> TradingLevels:
        """
        Calculate all TP/SL levels
        
        Args:
            direction: LONG or SHORT
            asset: Normalized asset (BTCUSD, XAUUSD, etc.)
            timeframe: Normalized TF (M1, M5, etc.)
            entry_price: Entry price
            
        Returns:
            TradingLevels with all calculated levels
        """
        rules = self.config["assets"][asset][timeframe]
        unit = rules.get("unit", "%")
        
        # Distances from rules
        tp1_dist = rules["tp1"]
        tp2_dist = rules["tp2"]
        tp3_dist = rules["tp3"]
        sl_dist = rules["sl"]
        
        # Calculate levels based on unit type
        if unit == "pips":
            pip_value = self.PIP_VALUES.get(asset, 0.0001)
            tp1, tp2, tp3, sl = self._calc_pips(
                direction, entry_price, pip_value,
                tp1_dist, tp2_dist, tp3_dist, sl_dist
            )
        elif unit == "points":
            point_value = self.POINT_VALUES.get(asset, 1.0)
            tp1, tp2, tp3, sl = self._calc_points(
                direction, entry_price, point_value,
                tp1_dist, tp2_dist, tp3_dist, sl_dist
            )
        else:  # Percentage (default)
            tp1, tp2, tp3, sl = self._calc_percentage(
                direction, entry_price,
                tp1_dist, tp2_dist, tp3_dist, sl_dist
            )
        
        # Calculate average Risk/Reward
        avg_tp = (tp1_dist + tp2_dist + tp3_dist) / 3
        rr_ratio = round(avg_tp / sl_dist, 2) if sl_dist > 0 else 0
        
        return TradingLevels(
            direction=direction,
            asset=asset,
            timeframe=timeframe,
            entry=entry_price,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            sl=sl,
            tp1_distance=tp1_dist,
            tp2_distance=tp2_dist,
            tp3_distance=tp3_dist,
            sl_distance=sl_dist,
            unit=unit,
            rr_ratio=rr_ratio
        )
    
    def _calc_percentage(self, direction: str, entry: float,
                         tp1_pct: float, tp2_pct: float, 
                         tp3_pct: float, sl_pct: float):
        """Calculate based on percentage"""
        if direction == "LONG":
            tp1 = entry * (1 + tp1_pct / 100)
            tp2 = entry * (1 + tp2_pct / 100)
            tp3 = entry * (1 + tp3_pct / 100)
            sl = entry * (1 - sl_pct / 100)
        else:  # SHORT
            tp1 = entry * (1 - tp1_pct / 100)
            tp2 = entry * (1 - tp2_pct / 100)
            tp3 = entry * (1 - tp3_pct / 100)
            sl = entry * (1 + sl_pct / 100)
        
        return tp1, tp2, tp3, sl
    
    def _calc_pips(self, direction: str, entry: float, pip_value: float,
                   tp1_pips: float, tp2_pips: float, 
                   tp3_pips: float, sl_pips: float):
        """Calculate based on pips (FOREX)"""
        if direction == "LONG":
            tp1 = entry + (tp1_pips * pip_value)
            tp2 = entry + (tp2_pips * pip_value)
            tp3 = entry + (tp3_pips * pip_value)
            sl = entry - (sl_pips * pip_value)
        else:  # SHORT
            tp1 = entry - (tp1_pips * pip_value)
            tp2 = entry - (tp2_pips * pip_value)
            tp3 = entry - (tp3_pips * pip_value)
            sl = entry + (sl_pips * pip_value)
        
        return tp1, tp2, tp3, sl
    
    def _calc_points(self, direction: str, entry: float, point_value: float,
                     tp1_pts: float, tp2_pts: float,
                     tp3_pts: float, sl_pts: float):
        """Calculate based on points (Indices)"""
        if direction == "LONG":
            tp1 = entry + (tp1_pts * point_value)
            tp2 = entry + (tp2_pts * point_value)
            tp3 = entry + (tp3_pts * point_value)
            sl = entry - (sl_pts * point_value)
        else:  # SHORT
            tp1 = entry - (tp1_pts * point_value)
            tp2 = entry - (tp2_pts * point_value)
            tp3 = entry - (tp3_pts * point_value)
            sl = entry + (sl_pts * point_value)
        
        return tp1, tp2, tp3, sl
    
    def format_price(self, price: float, asset: str) -> str:
        """Format a price according to asset"""
        # Decimals per asset
        decimals = {
            "BTCUSD": 2,
            "ETHUSDT": 2,
            "XAUUSD": 2,
            "EURUSD": 5,
            "GBPUSD": 5,
            "USDJPY": 3,
            "US30": 1,
            "NAS100": 1,
        }
        dec = decimals.get(asset, 2)
        return f"{price:.{dec}f}"


# === Tests ===
if __name__ == "__main__":
    calc = LevelCalculator()
    
    test_cases = [
        ("LONG", "BTCUSD", "M5", 65000),
        ("SHORT", "XAUUSD", "M1", 2350),
        ("LONG", "ETHUSDT", "H1", 2450),
        ("SHORT", "EURUSD", "M15", 1.0850),
        ("LONG", "US30", "H1", 39500),
    ]
    
    print("=" * 70)
    print("💰 LEVEL CALCULATOR TEST")
    print("=" * 70)
    
    for direction, asset, tf, entry in test_cases:
        levels = calc.calculate(direction, asset, tf, entry)
        
        print(f"\n📊 {direction} {asset} {tf} @ {entry}")
        print(f"   TP1: {calc.format_price(levels.tp1, asset)} ({levels.tp1_distance}{levels.unit})")
        print(f"   TP2: {calc.format_price(levels.tp2, asset)} ({levels.tp2_distance}{levels.unit})")
        print(f"   TP3: {calc.format_price(levels.tp3, asset)} ({levels.tp3_distance}{levels.unit})")
        print(f"   SL:  {calc.format_price(levels.sl, asset)} ({levels.sl_distance}{levels.unit})")
        print(f"   R:R: 1:{levels.rr_ratio}")
