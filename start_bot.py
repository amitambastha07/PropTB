import os
import sys
from dotenv import load_dotenv
from config import TradingConfig
from bot_monitor import BotMonitor

def main():
    # Load environment variables
    load_dotenv()
    
    # Load configuration
    config = TradingConfig()
    
    # Validate configuration
    if not config.MT5_LOGIN or not config.MT5_PASSWORD or not config.MT5_SERVER:
        print("❌ Error: MT5 credentials not configured!")
        print("Please edit the .env file with your MT5 login details.")
        return
    
    print("🚀 Starting FundedFriday XAU/XAG Trading Bot...")
    print(f"📊 Account: {config.MT5_LOGIN}")
    print(f"🎯 Challenge: {config.CHALLENGE_TYPE}")
    print(f"💰 Balance: ${config.ACCOUNT_BALANCE:,}")
    print(f"📈 Symbols: {config.PRIMARY_SYMBOLS}")
    
    try:
        # Import and create bot instance
        from trading_bot import FundedFridayTradingBot
        
        bot = FundedFridayTradingBot(
            account_balance=config.ACCOUNT_BALANCE,
            challenge_type=config.CHALLENGE_TYPE
        )
        
        # Create monitor
        monitor = BotMonitor(bot)
        
        # Start the bot
        bot.start_bot(
            login=config.MT5_LOGIN,
            password=config.MT5_PASSWORD,
            server=config.MT5_SERVER
        )
        
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()