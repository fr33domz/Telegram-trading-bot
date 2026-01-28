"""
🤖 TELEGRAM BOT - Point d'entrée principal
Reçoit les messages, orchestre le pipeline complet

Pipeline:
Message → Parser → Calculator → Formatter → Telegram + Webhook
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Telegram imports
try:
    from telegram import Update, Bot
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    # Mock classes pour éviter les erreurs
    Update = None
    Bot = None
    ContextTypes = type('ContextTypes', (), {'DEFAULT_TYPE': None})()
    print("⚠️ python-telegram-bot non installé. Mode simulation activé.")

# Imports locaux
from parser import MessageParser, ParsedSignal
from calculator import LevelCalculator, TradingLevels
from formatter import SignalFormatter, FormattedSignal

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class PriceProvider:
    """
    Fournisseur de prix en temps réel
    
    Utilise plusieurs sources:
    1. Prix fourni dans le message (@prix)
    2. API externe (Binance, etc.)
    3. Prix par défaut pour simulation
    """
    
    # Prix par défaut pour simulation/fallback
    DEFAULT_PRICES = {
        "BTCUSD": 65000,
        "ETHUSDT": 2450,
        "XAUUSD": 2350,
        "EURUSD": 1.0850,
        "GBPUSD": 1.2650,
        "USDJPY": 151.50,
        "US30": 39500,
        "NAS100": 17800,
    }
    
    @classmethod
    async def get_price(cls, asset: str, provided_price: Optional[float] = None) -> float:
        """
        Récupère le prix actuel
        
        Args:
            asset: L'actif
            provided_price: Prix fourni manuellement (prioritaire)
            
        Returns:
            Le prix à utiliser
        """
        if provided_price:
            return provided_price
        
        # TODO: Intégrer API Binance/autre pour prix live
        # async with aiohttp.ClientSession() as session:
        #     async with session.get(f"https://api.binance.com/...") as resp:
        #         data = await resp.json()
        #         return float(data['price'])
        
        return cls.DEFAULT_PRICES.get(asset, 0)


class TradingBot:
    """
    Bot principal de trading
    
    Orchestre le pipeline complet:
    1. Réception du message
    2. Parsing
    3. Récupération du prix
    4. Calcul des niveaux
    5. Formatage
    6. Envoi Telegram + Webhook
    """
    
    def __init__(self, 
                 token: Optional[str] = None,
                 channel_id: Optional[str] = None,
                 webhook_url: Optional[str] = None,
                 template: str = "premium"):
        """
        Args:
            token: Token du bot Telegram
            channel_id: ID du canal de destination des signaux
            webhook_url: URL webhook pour TradingView/bot externe
            template: Template de formatage
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.channel_id = channel_id or os.getenv("TELEGRAM_CHANNEL_ID")
        self.webhook_url = webhook_url or os.getenv("WEBHOOK_URL")
        
        # Composants du pipeline
        self.parser = MessageParser()
        self.calculator = LevelCalculator()
        self.formatter = SignalFormatter(template=template)
        
        # Statistiques
        self.stats = {
            "signals_sent": 0,
            "errors": 0,
            "last_signal": None
        }
    
    async def process_message(self, message: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Traite un message et génère le signal complet
        
        Args:
            message: Message brut (ex: "LONG BTCUSD M5")
            chat_id: ID du chat d'origine (pour réponse directe)
            
        Returns:
            Dict avec le résultat du traitement
        """
        result = {
            "success": False,
            "error": None,
            "signal": None,
            "formatted": None
        }
        
        # 1. Parsing
        signal, error = self.parser.parse(message)
        if error:
            result["error"] = error
            return result
        
        result["signal"] = signal.to_dict()
        
        # 2. Récupération du prix
        price = await PriceProvider.get_price(signal.asset, signal.entry_price)
        if price == 0:
            result["error"] = f"❌ Impossible de récupérer le prix pour {signal.asset}"
            return result
        
        # 3. Calcul des niveaux
        levels = self.calculator.calculate(
            signal.direction,
            signal.asset,
            signal.timeframe,
            price
        )
        
        # 4. Formatage
        formatted = self.formatter.format(levels)
        result["formatted"] = formatted.json_data
        
        # 5. Envoi
        result["success"] = True
        result["telegram_message"] = formatted.telegram_message
        result["webhook_payload"] = formatted.webhook_payload
        
        # Stats
        self.stats["signals_sent"] += 1
        self.stats["last_signal"] = datetime.now().isoformat()
        
        return result
    
    async def send_to_channel(self, message: str) -> bool:
        """Envoie un message au canal configuré"""
        if not TELEGRAM_AVAILABLE:
            logger.warning("Telegram non disponible - simulation")
            return True
        
        if not self.token or not self.channel_id:
            logger.warning("Token ou Channel ID non configuré")
            return False
        
        try:
            bot = Bot(token=self.token)
            await bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode="Markdown"
            )
            return True
        except Exception as e:
            logger.error(f"Erreur envoi Telegram: {e}")
            self.stats["errors"] += 1
            return False
    
    async def send_webhook(self, payload: Dict) -> bool:
        """Envoie le payload au webhook"""
        if not self.webhook_url:
            return True
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"Erreur webhook: {e}")
            return False
    
    # === Handlers Telegram ===
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler /start"""
        welcome = """
🤖 *Oracle Trading Bot*

Bienvenue! Envoyez un signal au format:
`LONG BTCUSD M5`
`SHORT GOLD M1`
`BUY ETH H1 @2450`

*Commandes:*
/help - Aide détaillée
/assets - Assets disponibles
/stats - Statistiques

🚀 Prêt à trader!
"""
        await update.message.reply_text(welcome, parse_mode="Markdown")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler /help"""
        help_text = """
📚 *Guide d'utilisation*

*Format de base:*
`[DIRECTION] [ASSET] [TIMEFRAME]`

*Directions:* LONG, SHORT, BUY, SELL
*Assets:* BTCUSD, GOLD, ETHUSDT, EURUSD...
*Timeframes:* M1, M5, M15, H1, H4

*Prix optionnel:*
`LONG BTCUSD M5 @65000`

*Exemples:*
• `LONG BTCUSD M5`
• `SHORT GOLD M1`
• `BUY ETH 15M @2450`
• `sell nasdaq h1`
"""
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def cmd_assets(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler /assets"""
        assets_list = list(self.parser.config["assets"].keys())
        text = "📊 *Assets disponibles:*\n\n"
        text += "\n".join([f"• `{a}`" for a in assets_list])
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler /stats"""
        text = f"""
📈 *Statistiques*

Signaux envoyés: {self.stats['signals_sent']}
Erreurs: {self.stats['errors']}
Dernier signal: {self.stats['last_signal'] or 'Aucun'}
"""
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler messages texte"""
        message = update.message.text
        chat_id = str(update.effective_chat.id)
        
        # Process
        result = await self.process_message(message, chat_id)
        
        if result["success"]:
            # Réponse à l'utilisateur
            await update.message.reply_text(
                result["telegram_message"],
                parse_mode="Markdown"
            )
            
            # Envoi au canal si configuré
            if self.channel_id and self.channel_id != chat_id:
                await self.send_to_channel(result["telegram_message"])
            
            # Webhook
            if self.webhook_url:
                await self.send_webhook(result["webhook_payload"])
        else:
            await update.message.reply_text(result["error"])
    
    def run(self):
        """Lance le bot en mode polling"""
        if not TELEGRAM_AVAILABLE:
            logger.error("python-telegram-bot requis: pip install python-telegram-bot")
            return
        
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN non défini")
            return
        
        app = Application.builder().token(self.token).build()
        
        # Handlers
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("assets", self.cmd_assets))
        app.add_handler(CommandHandler("stats", self.cmd_stats))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("🤖 Bot démarré!")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


# === Mode simulation (sans Telegram) ===
async def simulate():
    """Simule le bot sans connexion Telegram"""
    bot = TradingBot(template="premium")
    
    test_messages = [
        "LONG BTCUSD M5",
        "SHORT GOLD M1",
        "BUY ETH H1 @2450",
        "sell nasdaq 15m",
    ]
    
    print("=" * 70)
    print("🧪 SIMULATION DU BOT (sans Telegram)")
    print("=" * 70)
    
    for msg in test_messages:
        print(f"\n📨 Input: '{msg}'")
        print("-" * 50)
        
        result = await bot.process_message(msg)
        
        if result["success"]:
            print(result["telegram_message"])
            print("\n🔗 Webhook payload:")
            print(json.dumps(result["webhook_payload"], indent=2))
        else:
            print(f"❌ Erreur: {result['error']}")


if __name__ == "__main__":
    import sys
    
    if "--run" in sys.argv:
        # Mode production
        bot = TradingBot()
        bot.run()
    else:
        # Mode simulation
        asyncio.run(simulate())
