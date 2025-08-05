FundedFriday XAU/XAG Trading Bot
Overview
This trading bot is designed to pass FundedFriday prop firm challenges by trading XAU (Gold) and XAG (Silver) using advanced risk management and multi-timeframe analysis. Optimized for 24/7 operation on an AWS EC2 Windows instance, it ensures compliance with FundedFriday rules while targeting consistent performance.
Key Features

Prop Firm Compliant: Adheres to FundedFriday challenge rules
XAU/XAG Focus: Specialized for precious metals trading
Risk Management: Dynamic lot sizing, drawdown protection
Multi-Timeframe Analysis: Combines M15, H1, and H4 signals
AWS EC2 Optimized: Reliable cloud deployment
Monitoring: Real-time logging and performance tracking

Prerequisites

AWS Windows EC2 instance (t3.medium or larger recommended)
MetaTrader 5 (MT5) installed and configured
Python 3.8+ installed
FundedFriday challenge account credentials

Installation
Step 1: Upload Files to EC2

Connect to your AWS Windows EC2 instance via RDP.
Create a directory: C:\TradingBot\.
Upload the following files:
trading_bot.py (main bot file)
config.py
bot_monitor.py
setup_environment.py
start_bot.py
install_service.py



Step 2: Set Up Environment
Open Command Prompt as Administrator and run:
cd C:\TradingBot
python setup_environment.py

This installs required Python packages, creates directories, and generates a .env file.
Step 3: Configure Settings
Edit C:\TradingBot\.env with your MT5 credentials and account details:
# MT5 Connection Settings
MT5_LOGIN=12345678
MT5_PASSWORD=YourPassword123
MT5_SERVER=YourBroker-Server

# Account Settings
ACCOUNT_BALANCE=10000
CHALLENGE_TYPE=ONE_STEP

Step 4: Test the Bot
Run a test to verify connectivity:
python start_bot.py

Press Ctrl+C to stop after confirming successful connection.
Step 5: Set Up as Windows Service
For 24/7 operation, configure the bot as a Windows service:
python install_service.py

This creates run_bot.bat and trading_bot_task.xml.
Step 6: Configure Auto-Start

Open Task Scheduler (search in Start menu).
Click Import Task... and select trading_bot_task.xml.
Configure user credentials and enable the task.

Configuration
Risk Management
Edit config.py to adjust risk settings:
BASE_RISK_PER_TRADE = 0.012    # 1.2% per trade
MAX_RISK_PER_TRADE = 0.02      # 2% maximum
MAX_CONCURRENT_TRADES = 4      # Maximum open positions
MAX_TRADES_PER_SYMBOL = 2      # Per XAU/XAG

Trading Hours (UTC)
TRADING_HOURS = {
    'start': '01:00',           # Start trading
    'end': '22:00',             # Stop new trades
    'friday_close': '21:00'     # Close all Friday trades
}

Monitoring

Logs: trading_logs/trading_bot_YYYYMMDD.log
Performance: data/performance_history.json
State: bot_state.json
Reports: Daily P&L, drawdown, and compliance summaries

Trading Strategy

Multi-Timeframe: H4 (trend), H1 (entry), M15 (timing)
Indicators: RSI, MACD, Bollinger Bands, EMAs
Market Structure: Support/resistance identification
Volatility: ATR-based position sizing
XAU/XAG Focus: Optimized for Asian/London sessions, news avoidance

Risk Management

FundedFriday Compliance: Real-time drawdown monitoring, auto-stop
Position Management: ATR-based SL/TP, max 24-hour trades
Correlation: Limits over-exposure across XAU/XAG

Troubleshooting
Common Issues

Bot Won't Start:python -c "import MetaTrader5 as mt5; print(mt5.initialize())"


No Trades: Check .env credentials, drawdown limits, market hours, logs.
High Drawdown: Review position sizes; bot auto-reduces risk.

Error Codes



Error
Solution



MT5 Login Failed
Verify .env credentials


Invalid Symbol
Confirm XAU/XAG availability


Insufficient Margin
Reduce position sizes


Market Closed
Wait for market open


Support
For issues, provide:

Latest trading_logs/ file
bot_state.json
MT5 account screenshot

Important Notes

Test on a demo account first.
Only trade with risk capital.
Verify broker supports XAU/XAG.
All times are UTC.
Monitor FundedFriday rule updates.
Regularly check account status.

Expected Performance

Success Rate: 65-75% profitable trades
Risk-Reward: 1:1.5 average
Monthly Target: 8-12% (varies by challenge)
Drawdown: <5% typical
Challenge Timeline:
ONE_STEP: 2-4 weeks
TWO_STEP: 3-6 weeks



Disclaimer
Trading involves significant risk. This bot is a tool to assist with systematic trading but does not guarantee profits. Always trade responsibly.