# 🚀 Oracle Trading Signal Bot

Complete trading signal generation system:
**Telegram → Parser → Calculator → Formatter → Telegram + Webhook**

## 📋 Architecture

```
TELEGRAM (text message)
    │ "LONG BTCUSD M5"
    ↓
TELEGRAM BOT (parser)
    │ Detects: direction, asset, timeframe
    ↓
CALCULATOR (TP/SL rules)
    │ Applies rules per asset+TF
    ↓
FORMATTER (templates)
    │ Generates professional message
    ↓
OUTPUTS
    ├→ TELEGRAM (formatted signal)
    ├→ WEBHOOK (for external bot)
    └→ GOOGLE SHEETS (logging)
```

## ✨ Features

- 🎯 **Smart Parser** - Understands multiple formats: `LONG BTC M5`, `buy gold 1m`, `🟢 ETH H1 @2450`
- 📊 **Flexible Rules** - TP/SL rules per asset AND timeframe (%, pips, points)
- 💬 **Pro Templates** - 4 message templates (standard, compact, premium, minimal)
- 🔗 **TradingView Ready** - Webhook server for alerts integration
- 📈 **Google Sheets** - Optional sync for rules and signal logging
- ⚡ **Semi-Automated** - Generates signals without auto-trading

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/telegram-trading-bot.git
cd telegram-trading-bot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your tokens
```

### 2. Telegram Setup

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Copy the token to `.env`
3. Create a channel and add the bot as admin
4. Get the channel ID (use [@userinfobot](https://t.me/userinfobot))

### 3. Run the Bot

```bash
# Simulation mode (without Telegram)
python src/bot.py

# Production mode
python src/bot.py --run
```

## 📱 Usage

### Message Format

```
LONG BTCUSD M5
SHORT GOLD M1
BUY ETH H1 @2450
sell nasdaq 15m
```

### Supported Formats

| Direction | Asset | Timeframe | Price (optional) |
|-----------|-------|-----------|------------------|
| LONG, BUY, L, 🟢 | BTCUSD, BTC, BITCOIN | M1, M5, M15, H1, H4 | @65000 |
| SHORT, SELL, S, 🔴 | XAUUSD, GOLD, XAU | 1, 5, 15, 1H, 4H | @2350.50 |

### Telegram Commands

- `/start` - Start the bot
- `/help` - Detailed help
- `/assets` - Available assets
- `/stats` - Statistics

## 🎯 Rules Configuration

### Option 1: JSON File (config/rules.json)

```json
{
  "assets": {
    "BTCUSD": {
      "aliases": ["BTC", "BITCOIN"],
      "M5": { "tp1": 1.0, "tp2": 2.0, "tp3": 3.5, "sl": 1.5 },
      "H1": { "tp1": 2.5, "tp2": 5.0, "tp3": 8.0, "sl": 3.0 }
    },
    "XAUUSD": {
      "aliases": ["GOLD", "XAU"],
      "M1": { "tp1": 0.3, "tp2": 0.6, "tp3": 1.0, "sl": 0.5 }
    },
    "EURUSD": {
      "M5": { "tp1": 10, "tp2": 20, "tp3": 30, "sl": 15, "unit": "pips" }
    },
    "US30": {
      "M5": { "tp1": 30, "tp2": 60, "tp3": 100, "sl": 50, "unit": "points" }
    }
  }
}
```

### Option 2: Google Sheets

Create a sheet with this format:

| Asset | TF | TP1 | TP2 | TP3 | SL | Unit |
|-------|-----|-----|-----|-----|-----|------|
| BTCUSD | M5 | 1.0 | 2.0 | 3.5 | 1.5 | % |
| XAUUSD | M1 | 0.3 | 0.6 | 1.0 | 0.5 | % |
| EURUSD | M5 | 10 | 20 | 30 | 15 | pips |
| US30 | M5 | 30 | 60 | 100 | 50 | points |

## 🔗 TradingView Integration

### 1. Start the Webhook Server

```bash
python src/webhook_server.py
```

### 2. Expose with ngrok (development)

```bash
ngrok http 5000
# Copy the URL https://xxx.ngrok.io
```

### 3. Configure TradingView Alert

**Webhook URL:** `https://xxx.ngrok.io/webhook`

**Message (JSON):**
```json
{
    "action": "{{strategy.order.action}}",
    "ticker": "{{ticker}}",
    "close": {{close}},
    "interval": "{{interval}}",
    "secret": "your-secret-key"
}
```

**With TP/SL from indicator:**
```json
{
    "action": "buy",
    "ticker": "{{ticker}}",
    "close": {{close}},
    "interval": "{{interval}}",
    "tp1": {{plot_0}},
    "tp2": {{plot_1}},
    "tp3": {{plot_2}},
    "sl": {{plot_3}},
    "secret": "your-secret-key"
}
```

## 📊 Signal Templates

### Standard
```
🟢 LONG BTCUSD
━━━━━━━━━━━━━━━━━━━━
⏱️ Timeframe: M5
💵 Entry: 65000.00

🎯 Targets:
├─ TP1: 65650.00 (+1%)
├─ TP2: 66300.00 (+2%)
└─ TP3: 67275.00 (+3.5%)

🛡️ Stop Loss: 64025.00 (-1.5%)
📊 Risk/Reward: 1:2.17
```

### Premium
```
╔═══════════════════════════════════╗
║  🟢 SIGNAL LONG 🟢
╠═══════════════════════════════════╣
║  📈 BTCUSD | ⏱ M5
║  💰 Entry: 65000.00
║  🎯 TP1: 65650.00 → +1%
║  🎯 TP2: 66300.00 → +2%
║  🎯 TP3: 67275.00 → +3.5%
║  🛡️ SL: 64025.00 → -1.5%
║  📊 R:R: 1:2.17
╚═══════════════════════════════════╝
```

### Compact
```
🟢 LONG BTCUSD | M5
Entry: 65000.00
TP: 65650 → 66300 → 67275
SL: 64025 | R:R 1:2.17
```

## 📁 Project Structure

```
telegram-trading-bot/
├── config/
│   └── rules.json          # TP/SL rules per asset
├── src/
│   ├── parser.py           # Message parser
│   ├── calculator.py       # Level calculator
│   ├── formatter.py        # Signal formatter
│   ├── bot.py              # Main Telegram bot
│   ├── webhook_server.py   # Flask webhook server
│   └── sheets_integration.py # Google Sheets sync
├── .env.example
├── requirements.txt
└── README.md
```

## ⚙️ Environment Variables

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=-100123456789

# Webhook Security
WEBHOOK_SECRET=your-secret-key
WEBHOOK_URL=https://your-server.com/webhook

# Google Sheets (optional)
GOOGLE_CREDENTIALS_PATH=./credentials.json
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id

# Server
PORT=5000
FLASK_DEBUG=false
```

## 🔒 Security

- Use a strong `WEBHOOK_SECRET`
- Never share your `BOT_TOKEN`
- Enable webhook signature validation
- Use HTTPS in production
- Validate all incoming data

## 🚀 Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "src/bot.py", "--run"]
```

```bash
docker build -t trading-bot .
docker run -d --env-file .env trading-bot
```

### Railway / Render / Heroku

1. Connect your repository
2. Set environment variables
3. Start command: `python src/bot.py --run`

### VPS (Ubuntu)

```bash
# Install
sudo apt update && sudo apt install python3-pip
pip install -r requirements.txt

# Run with systemd
sudo nano /etc/systemd/system/trading-bot.service
```

```ini
[Unit]
Description=Trading Signal Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/telegram-trading-bot
ExecStart=/usr/bin/python3 src/bot.py --run
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
```

## 📝 API Reference

### Parser

```python
from src.parser import MessageParser

parser = MessageParser()
signal, error = parser.parse("LONG BTCUSD M5")

if signal:
    print(signal.direction)  # "LONG"
    print(signal.asset)      # "BTCUSD"
    print(signal.timeframe)  # "M5"
```

### Calculator

```python
from src.calculator import LevelCalculator

calc = LevelCalculator()
levels = calc.calculate("LONG", "BTCUSD", "M5", 65000)

print(levels.tp1)  # 65650.0
print(levels.sl)   # 64025.0
print(levels.rr_ratio)  # 1.44
```

### Formatter

```python
from src.formatter import SignalFormatter

formatter = SignalFormatter(template="premium")
result = formatter.format(levels)

print(result.telegram_message)  # Formatted message
print(result.webhook_payload)   # JSON for webhook
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Flask](https://flask.palletsprojects.com/)
- [gspread](https://github.com/burnash/gspread)

---

Made with ❤️ by Oracle Trading
