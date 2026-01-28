"""
📱 SIGNAL FORMATTER - Generates professional Telegram messages
Customizable templates, emojis, markdown support
"""

from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import json


@dataclass
class FormattedSignal:
    """Formatted signal ready to send"""
    telegram_message: str       # Formatted message for Telegram
    plain_text: str             # Plain text version
    webhook_payload: Dict       # Payload for TradingView webhook
    json_data: Dict             # Complete JSON data


class SignalFormatter:
    """
    Trading signal formatter
    
    Generates professional Telegram messages with:
    - Emojis and formatting
    - RR and distance calculations
    - Customizable templates
    """
    
    # Default templates
    TEMPLATES = {
        "standard": """
🚀 *{direction_emoji} {direction} {asset}*
━━━━━━━━━━━━━━━━━━━━
⏱️ Timeframe: `{timeframe}`
💵 Entry: `{entry}`

🎯 *Targets:*
├─ TP1: `{tp1}` ({tp1_dist})
├─ TP2: `{tp2}` ({tp2_dist})
└─ TP3: `{tp3}` ({tp3_dist})

🛡️ Stop Loss: `{sl}` ({sl_dist})
📊 Risk/Reward: `1:{rr_ratio}`

⏰ {timestamp}
{signature}
""",
        
        "compact": """
{direction_emoji} *{direction} {asset}* | {timeframe}
Entry: `{entry}`
TP: `{tp1}` → `{tp2}` → `{tp3}`
SL: `{sl}` | R:R `1:{rr_ratio}`
""",
        
        "premium": """
╔═══════════════════════════════════╗
║  {direction_emoji} *SIGNAL {direction}* {direction_emoji}
╠═══════════════════════════════════╣
║  📈 *{asset}* | ⏱ *{timeframe}*
╠═══════════════════════════════════╣
║  💰 Entry Zone
║  └─ `{entry}`
╠═══════════════════════════════════╣
║  🎯 Take Profits
║  ├─ TP1: `{tp1}` ➜ +{tp1_dist}
║  ├─ TP2: `{tp2}` ➜ +{tp2_dist}
║  └─ TP3: `{tp3}` ➜ +{tp3_dist}
╠═══════════════════════════════════╣
║  🛡️ Stop Loss
║  └─ `{sl}` ➜ -{sl_dist}
╠═══════════════════════════════════╣
║  📊 R:R Ratio: *1:{rr_ratio}*
╚═══════════════════════════════════╝

⏰ _{timestamp}_
{signature}
""",
        
        "minimal": """{direction_emoji} {asset} {timeframe}
E: {entry} | TP: {tp1}/{tp2}/{tp3} | SL: {sl}""",
    }
    
    def __init__(self, 
                 template: str = "standard",
                 signature: str = "🤖 Oracle Trading Bot"):
        """
        Args:
            template: Template name or custom template
            signature: Signature at the bottom of message
        """
        if template in self.TEMPLATES:
            self.template = self.TEMPLATES[template]
        else:
            self.template = template
        
        self.signature = signature
    
    def format(self, levels, asset_rules: Optional[Dict] = None) -> FormattedSignal:
        """
        Format TradingLevels into complete signal
        
        Args:
            levels: TradingLevels object
            asset_rules: Optional rules for the asset
            
        Returns:
            FormattedSignal with all versions
        """
        # Emoji based on direction
        direction_emoji = "🟢" if levels.direction == "LONG" else "🔴"
        
        # Price formatting
        entry_str = self._format_number(levels.entry, levels.asset)
        tp1_str = self._format_number(levels.tp1, levels.asset)
        tp2_str = self._format_number(levels.tp2, levels.asset)
        tp3_str = self._format_number(levels.tp3, levels.asset)
        sl_str = self._format_number(levels.sl, levels.asset)
        
        # Distance formatting
        unit_symbol = self._get_unit_symbol(levels.unit)
        tp1_dist = f"+{levels.tp1_distance}{unit_symbol}"
        tp2_dist = f"+{levels.tp2_distance}{unit_symbol}"
        tp3_dist = f"+{levels.tp3_distance}{unit_symbol}"
        sl_dist = f"-{levels.sl_distance}{unit_symbol}"
        
        # Timestamp
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Remplissage du template
        telegram_message = self.template.format(
            direction=levels.direction,
            direction_emoji=direction_emoji,
            asset=levels.asset,
            timeframe=levels.timeframe,
            entry=entry_str,
            tp1=tp1_str,
            tp2=tp2_str,
            tp3=tp3_str,
            sl=sl_str,
            tp1_dist=tp1_dist,
            tp2_dist=tp2_dist,
            tp3_dist=tp3_dist,
            sl_dist=sl_dist,
            rr_ratio=levels.rr_ratio,
            timestamp=timestamp,
            signature=self.signature
        ).strip()
        
        # Version texte simple (sans markdown)
        plain_text = telegram_message.replace('*', '').replace('`', '').replace('_', '')
        
        # Payload webhook pour TradingView
        webhook_payload = self._create_webhook_payload(levels)
        
        # JSON complet
        json_data = {
            "signal": levels.to_dict(),
            "formatted": {
                "telegram": telegram_message,
                "plain": plain_text
            },
            "meta": {
                "timestamp": timestamp,
                "template": "custom" if self.template not in self.TEMPLATES.values() else "standard"
            }
        }
        
        return FormattedSignal(
            telegram_message=telegram_message,
            plain_text=plain_text,
            webhook_payload=webhook_payload,
            json_data=json_data
        )
    
    def _format_number(self, value: float, asset: str) -> str:
        """Format a number according to asset"""
        # Decimals adapted to asset
        if asset in ["EURUSD", "GBPUSD", "AUDUSD", "USDCAD", "USDCHF"]:
            return f"{value:.5f}"
        elif asset in ["USDJPY"]:
            return f"{value:.3f}"
        elif asset in ["US30", "NAS100", "SPX500"]:
            return f"{value:.1f}"
        elif asset in ["BTCUSD", "ETHUSDT", "XAUUSD"]:
            return f"{value:.2f}"
        else:
            return f"{value:.2f}"
    
    def _get_unit_symbol(self, unit: str) -> str:
        """Return the unit symbol"""
        symbols = {
            "%": "%",
            "pips": " pips",
            "points": " pts"
        }
        return symbols.get(unit, "%")
    
    def _create_webhook_payload(self, levels) -> Dict:
        """Create payload for TradingView/Bot webhook"""
        return {
            "action": levels.direction.lower(),
            "symbol": levels.asset,
            "timeframe": levels.timeframe,
            "price": levels.entry,
            "targets": {
                "tp1": levels.tp1,
                "tp2": levels.tp2,
                "tp3": levels.tp3
            },
            "stoploss": levels.sl,
            "risk_reward": levels.rr_ratio,
            "timestamp": datetime.now().isoformat()
        }
    
    @classmethod
    def available_templates(cls) -> list:
        """List available templates"""
        return list(cls.TEMPLATES.keys())


# === Tests ===
if __name__ == "__main__":
    from calculator import LevelCalculator, TradingLevels
    
    calc = LevelCalculator()
    
    # Test with different templates
    levels = calc.calculate("LONG", "BTCUSD", "M5", 65000)
    
    print("=" * 60)
    print("📱 SIGNAL FORMATTER TEST")
    print("=" * 60)
    
    for template_name in SignalFormatter.available_templates():
        formatter = SignalFormatter(template=template_name)
        result = formatter.format(levels)
        
        print(f"\n{'='*60}")
        print(f"📋 Template: {template_name.upper()}")
        print("=" * 60)
        print(result.telegram_message)
    
    # Test webhook payload
    print("\n" + "=" * 60)
    print("🔗 WEBHOOK PAYLOAD")
    print("=" * 60)
    formatter = SignalFormatter()
    result = formatter.format(levels)
    print(json.dumps(result.webhook_payload, indent=2))
