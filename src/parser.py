"""
🎯 MESSAGE PARSER - Transforms "LONG BTCUSD M5" into structured signal
Supports: aliases, multiple formats, complete validation
"""

import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ParsedSignal:
    """Structure of a parsed signal"""
    direction: str          # LONG or SHORT
    asset: str              # Normalized asset (e.g., BTCUSD)
    timeframe: str          # Normalized TF (e.g., M5)
    original_message: str   # Original message
    timestamp: datetime     # When parsed
    entry_price: Optional[float] = None  # Entry price (optional)
    
    def to_dict(self) -> Dict:
        return {
            "direction": self.direction,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "original_message": self.original_message,
            "timestamp": self.timestamp.isoformat(),
            "entry_price": self.entry_price
        }

class MessageParser:
    """
    Smart parser for trading messages
    Supported formats:
    - LONG BTCUSD M5
    - BUY GOLD 5M
    - SHORT ETH M1 @2450.50
    - 🟢 BTC 15
    """
    
    def __init__(self, config_path: str = "config/rules.json"):
        self.config = self._load_config(config_path)
        self._build_lookup_tables()
    
    def _load_config(self, path: str) -> Dict:
        """Load rules configuration"""
        config_file = Path(path)
        if not config_file.exists():
            # Search in parent folder if needed
            config_file = Path(__file__).parent.parent / "config" / "rules.json"
        
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def _build_lookup_tables(self):
        """Build lookup tables for fast parsing"""
        # Direction table
        self.direction_lookup = {}
        for direction, aliases in self.config["directions"].items():
            for alias in aliases:
                self.direction_lookup[alias.upper()] = direction
        
        # Asset table
        self.asset_lookup = {}
        for asset, data in self.config["assets"].items():
            self.asset_lookup[asset.upper()] = asset
            if "aliases" in data:
                for alias in data["aliases"]:
                    self.asset_lookup[alias.upper()] = asset
        
        # Timeframe table
        self.tf_lookup = {}
        for alias, tf in self.config["timeframes"]["aliases"].items():
            self.tf_lookup[alias.upper()] = tf
    
    def parse(self, message: str) -> Tuple[Optional[ParsedSignal], Optional[str]]:
        """
        Parse a message and return (signal, error)
        
        Args:
            message: Raw message to parse
            
        Returns:
            (ParsedSignal, None) if success
            (None, error_message) if failure
        """
        original = message
        message = message.strip().upper()
        
        # Extract components
        direction = self._extract_direction(message)
        if not direction:
            return None, "❌ Direction not found. Use: LONG/SHORT/BUY/SELL"
        
        asset = self._extract_asset(message)
        if not asset:
            return None, f"❌ Asset not recognized. Available: {', '.join(self.config['assets'].keys())}"
        
        timeframe = self._extract_timeframe(message)
        if not timeframe:
            return None, "❌ Timeframe not found. Use: M1/M5/M15/H1/H4"
        
        # Check if TF exists for this asset
        if timeframe not in self.config["assets"][asset]:
            available_tfs = [k for k in self.config["assets"][asset].keys() if k != "aliases"]
            return None, f"❌ TF {timeframe} not configured for {asset}. Available: {', '.join(available_tfs)}"
        
        # Optional entry price extraction
        entry_price = self._extract_price(message)
        
        signal = ParsedSignal(
            direction=direction,
            asset=asset,
            timeframe=timeframe,
            original_message=original,
            timestamp=datetime.now(),
            entry_price=entry_price
        )
        
        return signal, None
    
    def _extract_direction(self, message: str) -> Optional[str]:
        """Extract direction (LONG/SHORT)"""
        words = message.split()
        
        # Search in first tokens
        for word in words[:3]:
            clean = re.sub(r'[^\w🟢🔴]', '', word)
            if clean in self.direction_lookup:
                return self.direction_lookup[clean]
        
        return None
    
    def _extract_asset(self, message: str) -> Optional[str]:
        """Extract asset from message"""
        words = message.replace('@', ' ').split()
        
        # Search for match in words
        for word in words:
            clean = re.sub(r'[^\w]', '', word)
            if clean in self.asset_lookup:
                return self.asset_lookup[clean]
        
        # Try to find asset in complete message
        for alias in sorted(self.asset_lookup.keys(), key=len, reverse=True):
            if alias in message:
                return self.asset_lookup[alias]
        
        return None
    
    def _extract_timeframe(self, message: str) -> Optional[str]:
        """Extract timeframe"""
        # Pattern for timeframe: M1, M5, 5M, 15, H1, 4H, D1, etc.
        # Supports: M1, M5, M15, H1, H4, D1, 5M, 15M, 1H, 4H, 5, 15, etc.
        tf_pattern = r'\b([MHD]\d+|\d+[MHD]|\d+MIN?|\d+)\b'
        matches = re.findall(tf_pattern, message, re.IGNORECASE)
        
        for match in matches:
            upper_match = match.upper()
            if upper_match in self.tf_lookup:
                return self.tf_lookup[upper_match]
        
        # Also search for direct timeframes in words
        words = message.split()
        for word in words:
            clean = re.sub(r'[^\w]', '', word).upper()
            if clean in self.tf_lookup:
                return self.tf_lookup[clean]
        
        return None
    
    def _extract_price(self, message: str) -> Optional[float]:
        """Extract optional price (@2450.50)"""
        price_pattern = r'@\s*([\d.,]+)'
        match = re.search(price_pattern, message)
        if match:
            try:
                price_str = match.group(1).replace(',', '')
                return float(price_str)
            except ValueError:
                pass
        return None


# === Quick tests ===
if __name__ == "__main__":
    parser = MessageParser()
    
    test_messages = [
        "LONG BTCUSD M5",
        "SHORT GOLD M1",
        "BUY ETH 15M",
        "sell nasdaq h1",
        "🟢 BTC M5 @65000",
        "short xau 5",
        "LONG DOW H4",
        "invalid message",
        "LONG UNKNOWN M5",
    ]
    
    print("=" * 60)
    print("🧪 PARSER TEST")
    print("=" * 60)
    
    for msg in test_messages:
        signal, error = parser.parse(msg)
        if signal:
            print(f"✅ '{msg}'")
            print(f"   → {signal.direction} {signal.asset} {signal.timeframe}")
            if signal.entry_price:
                print(f"   → Entry: {signal.entry_price}")
        else:
            print(f"❌ '{msg}' → {error}")
        print()
