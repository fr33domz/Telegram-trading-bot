"""
🔗 WEBHOOK SERVER - Reçoit alertes TradingView, envoie vers Telegram

Deux modes:
1. INCOMING: TradingView → Ce serveur → Telegram
2. OUTGOING: Telegram → Ce serveur → Bot externe

Architecture:
TradingView Alert → /webhook → Process → Telegram Channel
"""

import os
import json
import hmac
import hashlib
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
import asyncio

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️ Flask non installé. pip install flask flask-cors")

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class WebhookPayload:
    """Structure standardisée pour les webhooks"""
    action: str         # buy/sell/long/short
    symbol: str         # BTCUSD, XAUUSD, etc.
    price: float        # Prix d'entrée
    timeframe: str      # M1, M5, etc.
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    tp3: Optional[float] = None
    sl: Optional[float] = None
    comment: Optional[str] = None
    timestamp: Optional[str] = None
    secret: Optional[str] = None
    
    @classmethod
    def from_tradingview(cls, data: Dict) -> 'WebhookPayload':
        """Parse un payload TradingView"""
        return cls(
            action=data.get("action", data.get("strategy.order.action", "")),
            symbol=data.get("ticker", data.get("symbol", "")),
            price=float(data.get("close", data.get("price", 0))),
            timeframe=data.get("interval", data.get("timeframe", "M5")),
            tp1=float(data["tp1"]) if "tp1" in data else None,
            tp2=float(data["tp2"]) if "tp2" in data else None,
            tp3=float(data["tp3"]) if "tp3" in data else None,
            sl=float(data["sl"]) if "sl" in data else None,
            comment=data.get("comment", ""),
            timestamp=data.get("time", datetime.now().isoformat()),
            secret=data.get("secret", "")
        )


class TelegramSender:
    """Envoie des messages vers Telegram"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
    
    async def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Envoie un message async"""
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp requis pour envoi async")
            return False
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            async with session.post(
                f"{self.api_url}/sendMessage",
                json=payload
            ) as resp:
                return resp.status == 200
    
    def send_message_sync(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Envoie un message sync (pour Flask)"""
        import requests
        
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        resp = requests.post(
            f"{self.api_url}/sendMessage",
            json=payload
        )
        return resp.status_code == 200


def create_app():
    """Factory pour l'app Flask"""
    if not FLASK_AVAILABLE:
        raise ImportError("Flask requis: pip install flask flask-cors")
    
    app = Flask(__name__)
    CORS(app)
    
    # Configuration
    app.config.update(
        BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN"),
        CHAT_ID=os.getenv("TELEGRAM_CHANNEL_ID"),
        WEBHOOK_SECRET=os.getenv("WEBHOOK_SECRET", "your-secret-key"),
        DEBUG=os.getenv("FLASK_DEBUG", "false").lower() == "true"
    )
    
    # Telegram sender
    telegram = TelegramSender(
        app.config["BOT_TOKEN"],
        app.config["CHAT_ID"]
    ) if app.config["BOT_TOKEN"] else None
    
    # === Routes ===
    
    @app.route("/", methods=["GET"])
    def home():
        """Health check"""
        return jsonify({
            "status": "running",
            "service": "Oracle Trading Webhook Server",
            "timestamp": datetime.now().isoformat()
        })
    
    @app.route("/health", methods=["GET"])
    def health():
        """Health check détaillé"""
        return jsonify({
            "status": "healthy",
            "telegram_configured": app.config["BOT_TOKEN"] is not None,
            "channel_configured": app.config["CHAT_ID"] is not None
        })
    
    @app.route("/webhook", methods=["POST"])
    def webhook_tradingview():
        """
        Endpoint principal pour TradingView
        
        Format attendu:
        {
            "action": "buy",
            "ticker": "BTCUSD",
            "close": 65000,
            "interval": "5",
            "tp1": 65650,
            "tp2": 66300,
            "tp3": 68275,
            "sl": 64025,
            "secret": "your-secret"
        }
        """
        try:
            data = request.get_json(force=True)
            logger.info(f"Webhook reçu: {json.dumps(data)}")
            
            # Validation du secret
            if app.config["WEBHOOK_SECRET"]:
                if data.get("secret") != app.config["WEBHOOK_SECRET"]:
                    logger.warning("Secret invalide")
                    return jsonify({"error": "Invalid secret"}), 401
            
            # Parse le payload
            payload = WebhookPayload.from_tradingview(data)
            
            # Formater le message
            message = format_signal_message(payload)
            
            # Envoyer vers Telegram
            if telegram:
                success = telegram.send_message_sync(message)
                if success:
                    logger.info("Signal envoyé vers Telegram")
                else:
                    logger.error("Échec envoi Telegram")
            
            return jsonify({
                "status": "success",
                "signal": asdict(payload)
            })
            
        except Exception as e:
            logger.error(f"Erreur webhook: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/webhook/raw", methods=["POST"])
    def webhook_raw():
        """Endpoint pour recevoir du texte brut (comme le format de ton parser)"""
        try:
            # Support texte brut ou JSON
            if request.is_json:
                data = request.get_json()
                message = data.get("message", "")
            else:
                message = request.data.decode("utf-8")
            
            logger.info(f"Message brut reçu: {message}")
            
            # Importer et utiliser le parser
            from parser import MessageParser
            from calculator import LevelCalculator
            from formatter import SignalFormatter
            
            parser = MessageParser()
            calculator = LevelCalculator()
            formatter = SignalFormatter(template="premium")
            
            # Process
            signal, error = parser.parse(message)
            if error:
                return jsonify({"error": error}), 400
            
            # Simuler un prix si non fourni
            if not signal.entry_price:
                from bot import PriceProvider
                signal.entry_price = asyncio.run(
                    PriceProvider.get_price(signal.asset)
                )
            
            # Calculer
            levels = calculator.calculate(
                signal.direction,
                signal.asset,
                signal.timeframe,
                signal.entry_price
            )
            
            # Formater
            formatted = formatter.format(levels)
            
            # Envoyer
            if telegram:
                telegram.send_message_sync(formatted.telegram_message)
            
            return jsonify({
                "status": "success",
                "signal": formatted.json_data
            })
            
        except Exception as e:
            logger.error(f"Erreur: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/test", methods=["GET", "POST"])
    def test_signal():
        """Endpoint de test"""
        test_payload = {
            "action": "buy",
            "ticker": "BTCUSD",
            "close": 65000,
            "interval": "5",
            "tp1": 65650,
            "tp2": 66300,
            "tp3": 68275,
            "sl": 64025
        }
        
        payload = WebhookPayload.from_tradingview(test_payload)
        message = format_signal_message(payload)
        
        return jsonify({
            "test_payload": test_payload,
            "formatted_message": message
        })
    
    return app


def format_signal_message(payload: WebhookPayload) -> str:
    """Formate un payload en message Telegram"""
    direction = "LONG" if payload.action.lower() in ["buy", "long"] else "SHORT"
    emoji = "🟢" if direction == "LONG" else "🔴"
    
    message = f"""
{emoji} *{direction} {payload.symbol}*
━━━━━━━━━━━━━━━━━━━━
⏱️ Timeframe: `{payload.timeframe}`
💵 Entry: `{payload.price}`
"""
    
    if payload.tp1:
        message += f"""
🎯 *Targets:*
├─ TP1: `{payload.tp1}`
├─ TP2: `{payload.tp2}`
└─ TP3: `{payload.tp3}`
"""
    
    if payload.sl:
        message += f"""
🛡️ Stop Loss: `{payload.sl}`
"""
    
    if payload.comment:
        message += f"""
📝 {payload.comment}
"""
    
    message += f"""
⏰ {payload.timestamp}
🤖 _Oracle Trading Bot_
"""
    
    return message.strip()


# === TradingView Alert Template ===
TRADINGVIEW_ALERT_TEMPLATE = """
📋 TEMPLATE POUR ALERTE TRADINGVIEW

=== Configuration de l'alerte ===
Webhook URL: https://your-server.com/webhook

=== Message (JSON) ===
{
    "action": "{{strategy.order.action}}",
    "ticker": "{{ticker}}",
    "close": {{close}},
    "interval": "{{interval}}",
    "tp1": {{plot_0}},
    "tp2": {{plot_1}},
    "tp3": {{plot_2}},
    "sl": {{plot_3}},
    "time": "{{time}}",
    "secret": "your-secret-key",
    "comment": "Signal from Oracle"
}

=== Pour indicateur simple (sans strategy) ===
{
    "action": "buy",
    "ticker": "{{ticker}}",
    "close": {{close}},
    "interval": "{{interval}}",
    "secret": "your-secret-key"
}

=== Variables TradingView disponibles ===
{{ticker}} - Symbole (BTCUSD)
{{close}} - Prix de clôture
{{open}}, {{high}}, {{low}} - OHLC
{{volume}} - Volume
{{time}} - Timestamp
{{interval}} - Timeframe (5, 15, 60, etc.)
{{strategy.order.action}} - buy/sell (pour strategies)
{{plot_0}}, {{plot_1}}, etc. - Valeurs des plots de l'indicateur
"""


# === Démarrage ===
if __name__ == "__main__":
    if not FLASK_AVAILABLE:
        print("❌ Flask requis: pip install flask flask-cors")
        print(TRADINGVIEW_ALERT_TEMPLATE)
    else:
        print("=" * 60)
        print("🔗 ORACLE WEBHOOK SERVER")
        print("=" * 60)
        print(TRADINGVIEW_ALERT_TEMPLATE)
        print("=" * 60)
        
        app = create_app()
        port = int(os.getenv("PORT", 5000))
        
        print(f"\n🚀 Démarrage sur http://localhost:{port}")
        print(f"📡 Webhook URL: http://localhost:{port}/webhook")
        print(f"🧪 Test URL: http://localhost:{port}/test")
        
        app.run(host="0.0.0.0", port=port, debug=True)
