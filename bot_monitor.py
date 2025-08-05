import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import MetaTrader5 as mt5

class BotMonitor:
    def __init__(self, bot_instance=None):
        self.bot = bot_instance
        self.last_check = datetime.now()
        self.alerts_sent = {}
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - MONITOR - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('BotMonitor')
    
    def check_bot_health(self) -> Dict:
        """Check overall bot health"""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'mt5_connected': self.check_mt5_connection(),
            'account_accessible': self.check_account_access(),
            'positions_count': self.get_positions_count(),
            'daily_pnl': self.get_daily_pnl(),
            'drawdown_status': self.check_drawdown_levels(),
            'trading_rules_compliance': self.check_rules_compliance()
        }
        
        return health_status
    
    def check_mt5_connection(self) -> bool:
        """Check MT5 connection status"""
        try:
            account_info = mt5.account_info()
            return account_info is not None
        except:
            return False
    
    def check_account_access(self) -> bool:
        """Check if account is accessible and not disabled"""
        try:
            account_info = mt5.account_info()
            if account_info is None:
                return False
            return account_info.trade_allowed
        except:
            return False
    
    def get_positions_count(self) -> int:
        """Get current number of open positions"""
        try:
            positions = mt5.positions_get()
            return len(positions) if positions else 0
        except:
            return 0
    
    def get_daily_pnl(self) -> float:
        """Get today's P&L"""
        try:
            # Get today's deals
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            deals = mt5.history_deals_get(today, datetime.now())
            
            if deals is None:
                return 0.0
                
            daily_pnl = sum(deal.profit for deal in deals if deal.magic == 234000)
            return daily_pnl
        except:
            return 0.0
    
    def check_drawdown_levels(self) -> Dict:
        """Check current drawdown against limits"""
        try:
            account_info = mt5.account_info()
            if account_info is None:
                return {"status": "error"}
            
            if self.bot:
                equity = account_info.equity
                balance = account_info.balance
                
                # Calculate various drawdowns
                max_dd_percent = (self.bot.initial_balance - equity) / self.bot.initial_balance * 100
                daily_dd_percent = (self.bot.daily_start_balance - equity) / self.bot.daily_start_balance * 100
                
                return {
                    "status": "ok",
                    "max_drawdown_percent": max_dd_percent,
                    "daily_drawdown_percent": daily_dd_percent,
                    "max_dd_limit": self.bot.max_drawdown * 100,
                    "daily_dd_limit": self.bot.daily_drawdown * 100
                }
            
            return {"status": "no_bot_reference"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def check_rules_compliance(self) -> Dict:
        """Check compliance with FundedFriday rules"""
        if not self.bot:
            return {"status": "no_bot_reference"}
        
        try:
            compliance = {
                "trading_days": len(self.bot.trading_days),
                "min_trading_days": self.bot.min_trading_days,
                "profitable_days": self.bot.profitable_days,
                "min_profitable_days": self.bot.min_profitable_days,
                "total_trades": self.bot.total_trades,
                "profit_target_percent": (self.bot.current_equity - self.bot.initial_balance) / self.bot.initial_balance * 100,
                "required_profit_percent": self.bot.profit_target * 100
            }
            
            return compliance
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def generate_daily_report(self) -> str:
        """Generate daily performance report"""
        health = self.check_bot_health()
        
        report = f"""
=== FundedFriday Bot Daily Report ===
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔗 Connection Status: {'✅ Connected' if health['mt5_connected'] else '❌ Disconnected'}
📊 Account Status: {'✅ Active' if health['account_accessible'] else '❌ Restricted'}
📈 Open Positions: {health['positions_count']}
💰 Daily P&L: ${health['daily_pnl']:.2f}

📋 Rules Compliance:
- Trading Days: {health['trading_rules_compliance'].get('trading_days', 0)}/{health['trading_rules_compliance'].get('min_trading_days', 7)}
- Profitable Days: {health['trading_rules_compliance'].get('profitable_days', 0)}/{health['trading_rules_compliance'].get('min_profitable_days', 7)}
- Total Trades: {health['trading_rules_compliance'].get('total_trades', 0)}
- Profit Progress: {health['trading_rules_compliance'].get('profit_target_percent', 0):.2f}%/{health['trading_rules_compliance'].get('required_profit_percent', 10):.1f}%

⚠️ Risk Status:
- Max Drawdown: {health['drawdown_status'].get('max_drawdown_percent', 0):.2f}%/{health['drawdown_status'].get('max_dd_limit', 6):.1f}%
- Daily Drawdown: {health['drawdown_status'].get('daily_drawdown_percent', 0):.2f}%/{health['drawdown_status'].get('daily_dd_limit', 3):.1f}%

================================
        """
        
        return report.strip()
    
    def save_performance_data(self):
        """Save performance data to file"""
        try:
            health = self.check_bot_health()
            
            # Load existing data
            performance_file = 'data/performance_history.json'
            if os.path.exists(performance_file):
                with open(performance_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []
            
            # Add current data
            history.append(health)
            
            # Keep only last 30 days
            cutoff_date = datetime.now() - timedelta(days=30)
            history = [
                record for record in history 
                if datetime.fromisoformat(record['timestamp']) > cutoff_date
            ]
            
            # Save updated data
            os.makedirs('data', exist_ok=True)
            with open(performance_file, 'w') as f:
                json.dump(history, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Error saving performance data: {e}")