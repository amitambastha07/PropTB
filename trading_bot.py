import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import logging
import json
import os
from typing import Dict, List, Tuple, Optional
import threading
import schedule

class FundedFridayTradingBot:
    def __init__(self, account_balance: float = 10000, challenge_type: str = "ONE_STEP", config=None):
        """
        FundedFriday Trading Bot for XAU/XAG pairs
        Designed for AWS EC2 Windows environment with MT5
        """
        self.account_balance = account_balance
        self.initial_balance = account_balance
        self.challenge_type = challenge_type
        self.current_equity = account_balance
        self.all_time_high_equity = account_balance
        self.daily_high_equity = account_balance
        self.daily_start_balance = account_balance
        
        # Load configuration
        if config is None:
            # Default config if none provided
            from config import TradingConfig
            config = TradingConfig()
        
        # Apply risk management settings from config
        self.base_risk_per_trade = config.BASE_RISK_PER_TRADE
        self.max_risk_per_trade = config.MAX_RISK_PER_TRADE
        self.max_concurrent_trades = config.MAX_CONCURRENT_TRADES
        self.max_trades_per_symbol = config.MAX_TRADES_PER_SYMBOL
        
        # Primary trading symbols (as requested)
        self.primary_symbols = config.PRIMARY_SYMBOLS
        # Backup symbols for diversification
        self.backup_symbols = config.BACKUP_SYMBOLS
        
        # Trading statistics
        self.total_trades = 0
        self.profitable_days = 0
        self.trading_days = set()
        self.last_trade_date = None
        self.daily_profit = 0
        self.total_profit = 0
        self.consecutive_losses = 0
        
        # Set challenge-specific rules
        self._set_challenge_rules()
        
        # Initialize logging
        self._setup_logging()
        
        # Trading state
        self.active_positions = {}
        self.daily_trades_count = {}
        self.trade_history = []
        self.is_trading_enabled = True
        
        # Technical indicators settings
        self.timeframes = [mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1, mt5.TIMEFRAME_H4]
        
    def _set_challenge_rules(self):
        """Set rules based on challenge type"""
        if self.challenge_type == "ONE_STEP":
            self.profit_target = 0.10  # 10%
            self.max_drawdown = 0.06   # 6%
            self.daily_drawdown = 0.03 # 3%
            self.trailing_daily_drawdown = 0.04  # 4%
            self.trailing_drawdown = 0.08        # 8%
            self.min_trading_days = 7
            self.min_profitable_days = 7
        else:  # TWO_STEP
            self.profit_target = 0.08  # 8% for Phase 1
            self.max_drawdown = 0.08   # 8%
            self.daily_drawdown = 0.05 # 5%
            self.trailing_daily_drawdown = 0.07  # 7%
            self.trailing_drawdown = 0.10        # 10%
            self.min_trading_days = 7
            self.min_profitable_days = 7
    
    def _setup_logging(self):
        """Setup comprehensive logging"""
        log_dir = "trading_logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = f"{log_dir}/trading_bot_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def initialize_mt5(self, login: int, password: str, server: str):
        """Initialize MT5 connection"""
        if not mt5.initialize():
            self.logger.error("MT5 initialization failed")
            return False
            
        if not mt5.login(login, password, server):
            self.logger.error(f"Failed to login to account {login}")
            return False
            
        self.logger.info(f"Successfully connected to MT5 account {login}")
        return True
    
    def check_account_status(self) -> Dict:
        """Check current account status and risk levels"""
        account_info = mt5.account_info()
        if account_info is None:
            return {"status": "error", "message": "Cannot get account info"}
            
        self.current_equity = account_info.equity
        self.account_balance = account_info.balance
        
        # Update all-time high
        if self.current_equity > self.all_time_high_equity:
            self.all_time_high_equity = self.current_equity
            
        # Calculate drawdowns
        max_dd_amount = self.initial_balance * self.max_drawdown
        current_dd = self.initial_balance - self.current_equity
        
        trailing_dd_amount = self.all_time_high_equity * self.trailing_drawdown
        current_trailing_dd = self.all_time_high_equity - self.current_equity
        
        daily_dd_amount = self.daily_start_balance * self.daily_drawdown
        current_daily_dd = self.daily_start_balance - self.current_equity
        
        trailing_daily_dd_amount = self.daily_high_equity * self.trailing_daily_drawdown
        current_trailing_daily_dd = self.daily_high_equity - self.current_equity
        
        # Check for breaches
        breaches = []
        if current_dd >= max_dd_amount:
            breaches.append("Maximum Drawdown")
        if current_trailing_dd >= trailing_dd_amount:
            breaches.append("Trailing Drawdown")
        if current_daily_dd >= daily_dd_amount:
            breaches.append("Daily Drawdown")
        if current_trailing_daily_dd >= trailing_daily_dd_amount:
            breaches.append("Trailing Daily Drawdown")
            
        profit_percentage = (self.current_equity - self.initial_balance) / self.initial_balance
        
        status = {
            "equity": self.current_equity,
            "balance": self.account_balance,
            "profit_percentage": profit_percentage * 100,
            "target_reached": profit_percentage >= self.profit_target,
            "breaches": breaches,
            "trading_days": len(self.trading_days),
            "profitable_days": self.profitable_days,
            "total_trades": self.total_trades,
            "can_trade": len(breaches) == 0 and self.is_trading_enabled
        }
        
        return status
    
    def get_market_analysis(self, symbol: str, timeframe) -> Dict:
        """Advanced market analysis for XAU/XAG"""
        try:
            # Get recent price data
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)
            if rates is None or len(rates) < 50:
                return {"signal": "HOLD", "strength": 0}
                
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Calculate technical indicators
            close_prices = df['close'].values
            high_prices = df['high'].values
            low_prices = df['low'].values
            volume = df['tick_volume'].values
            
            # Moving averages
            ema_20 = pd.Series(close_prices).ewm(span=20).mean().iloc[-1]
            ema_50 = pd.Series(close_prices).ewm(span=50).mean().iloc[-1]
            sma_100 = pd.Series(close_prices).rolling(window=100).mean().iloc[-1]
            
            current_price = close_prices[-1]
            
            # RSI
            rsi = self._calculate_rsi(close_prices, 14)
            
            # MACD
            macd_line, macd_signal, macd_histogram = self._calculate_macd(close_prices)
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(close_prices, 20, 2)
            
            # Support and Resistance levels
            support_resistance = self._find_support_resistance(high_prices, low_prices, close_prices)
            
            # Market volatility (ATR)
            atr = self._calculate_atr(high_prices, low_prices, close_prices, 14)
            
            # Signal generation
            signals = []
            signal_strength = 0
            
            # Trend following signals
            if current_price > ema_20 > ema_50 > sma_100:
                signals.append("STRONG_UPTREND")
                signal_strength += 3
            elif current_price > ema_20 > ema_50:
                signals.append("UPTREND")
                signal_strength += 2
            elif current_price < ema_20 < ema_50 < sma_100:
                signals.append("STRONG_DOWNTREND")
                signal_strength -= 3
            elif current_price < ema_20 < ema_50:
                signals.append("DOWNTREND")
                signal_strength -= 2
                
            # RSI signals
            if rsi < 30:
                signals.append("RSI_OVERSOLD")
                signal_strength += 1
            elif rsi > 70:
                signals.append("RSI_OVERBOUGHT")
                signal_strength -= 1
                
            # MACD signals
            if macd_line > macd_signal and macd_histogram > 0:
                signals.append("MACD_BULLISH")
                signal_strength += 1
            elif macd_line < macd_signal and macd_histogram < 0:
                signals.append("MACD_BEARISH")
                signal_strength -= 1
                
            # Bollinger Band signals
            if current_price < bb_lower:
                signals.append("BB_OVERSOLD")
                signal_strength += 1
            elif current_price > bb_upper:
                signals.append("BB_OVERBOUGHT")
                signal_strength -= 1
                
            # Determine final signal
            if signal_strength >= 3:
                final_signal = "BUY"
            elif signal_strength <= -3:
                final_signal = "SELL"
            else:
                final_signal = "HOLD"
                
            return {
                "signal": final_signal,
                "strength": abs(signal_strength),
                "current_price": current_price,
                "atr": atr,
                "rsi": rsi,
                "support_resistance": support_resistance,
                "signals": signals
            }
            
        except Exception as e:
            self.logger.error(f"Error in market analysis for {symbol}: {e}")
            return {"signal": "HOLD", "strength": 0}
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
        if avg_loss == 0:
            return 100
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """Calculate MACD"""
        prices_series = pd.Series(prices)
        ema_fast = prices_series.ewm(span=fast).mean()
        ema_slow = prices_series.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal).mean()
        macd_histogram = macd_line - macd_signal
        
        return macd_line.iloc[-1], macd_signal.iloc[-1], macd_histogram.iloc[-1]
    
    def _calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        prices_series = pd.Series(prices)
        sma = prices_series.rolling(window=period).mean()
        std = prices_series.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band.iloc[-1], sma.iloc[-1], lower_band.iloc[-1]
    
    def _calculate_atr(self, high, low, close, period=14):
        """Calculate Average True Range"""
        high_low = high - low
        high_close = np.abs(high - np.roll(close, 1))
        low_close = np.abs(low - np.roll(close, 1))
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = np.mean(true_range[-period:])
        
        return atr
    
    def _find_support_resistance(self, high, low, close, lookback=20):
        """Find support and resistance levels"""
        recent_highs = high[-lookback:]
        recent_lows = low[-lookback:]
        
        resistance = np.max(recent_highs)
        support = np.min(recent_lows)
        
        return {"support": support, "resistance": resistance}
    
    def calculate_position_size(self, symbol: str, entry_price: float, stop_loss: float) -> float:
        """Calculate optimal position size based on risk management"""
        try:
            # Get symbol info
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return 0.0
                
            # Calculate risk amount
            risk_amount = self.current_equity * self.base_risk_per_trade
            
            # Adjust risk based on consecutive losses
            if self.consecutive_losses >= 3:
                risk_amount *= 0.5  # Reduce risk after losses
            elif self.consecutive_losses == 0 and self.total_trades > 10:
                risk_amount *= 1.2  # Increase slightly after wins
                
            # Calculate pip value and position size
            pip_size = symbol_info.point * 10 if 'JPY' in symbol else symbol_info.point
            risk_in_pips = abs(entry_price - stop_loss) / pip_size
            
            if risk_in_pips == 0:
                return 0.0
                
            # For gold/silver, adjust calculation
            if symbol == 'XAUUSD':
                # Gold: 1 lot = 100 oz, $1 per pip per lot
                position_size = risk_amount / risk_in_pips
                position_size = max(0.01, min(position_size, 5.0))  # Min 0.01, Max 5 lots
            elif symbol == 'XAGUSD':
                # Silver: 1 lot = 5000 oz, $5 per pip per lot
                position_size = risk_amount / (risk_in_pips * 5)
                position_size = max(0.01, min(position_size, 10.0))  # Min 0.01, Max 10 lots
            else:
                # Standard forex calculation
                contract_size = symbol_info.trade_contract_size
                pip_value = (pip_size / entry_price) * contract_size
                position_size = risk_amount / (risk_in_pips * pip_value)
                position_size = max(0.01, min(position_size, 2.0))
                
            # Round to valid lot size
            min_lot = symbol_info.volume_min
            lot_step = symbol_info.volume_step
            position_size = round(position_size / lot_step) * lot_step
            position_size = max(min_lot, position_size)
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.01  # Default minimum size
    
    def place_trade(self, symbol: str, trade_type: str, analysis: Dict) -> bool:
        """Place a trade with proper risk management"""
        try:
            # Check if we can trade
            if not self.check_trading_conditions(symbol):
                return False
                
            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return False
                
            entry_price = tick.ask if trade_type == "BUY" else tick.bid
            atr = analysis.get('atr', 0.001)
            
            # Calculate stop loss and take profit
            if trade_type == "BUY":
                stop_loss = entry_price - (atr * 2)
                take_profit = entry_price + (atr * 3)
            else:
                stop_loss = entry_price + (atr * 2)
                take_profit = entry_price - (atr * 3)
                
            # Calculate position size
            position_size = self.calculate_position_size(symbol, entry_price, stop_loss)
            if position_size == 0:
                return False
                
            # Prepare trade request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": position_size,
                "type": mt5.ORDER_TYPE_BUY if trade_type == "BUY" else mt5.ORDER_TYPE_SELL,
                "price": entry_price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": 20,
                "magic": 234000,
                "comment": f"FundedFriday_Bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Execute trade
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Trade failed: {result.retcode} - {result.comment}")
                return False
                
            # Record trade
            self.total_trades += 1
            today = datetime.now().strftime('%Y-%m-%d')
            self.trading_days.add(today)
            
            self.active_positions[result.order] = {
                "symbol": symbol,
                "type": trade_type,
                "volume": position_size,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "time": datetime.now(),
                "analysis": analysis
            }
            
            self.logger.info(f"Trade placed: {trade_type} {position_size} {symbol} at {entry_price}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error placing trade: {e}")
            return False
    
    def check_trading_conditions(self, symbol: str) -> bool:
        """Check if we can place a trade"""
        # Check account status
        status = self.check_account_status()
        if not status["can_trade"]:
            return False
            
        # Check weekend restriction
        now = datetime.now()
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
            
        # Check if too many trades on this symbol
        symbol_trades = sum(1 for pos in self.active_positions.values() if pos["symbol"] == symbol)
        if symbol_trades >= self.max_trades_per_symbol:
            return False
            
        # Check total concurrent trades
        if len(self.active_positions) >= self.max_concurrent_trades:
            return False
            
        return True
    
    def manage_positions(self):
        """Monitor and manage open positions"""
        try:
            positions = mt5.positions_get()
            if positions is None:
                return
                
            current_time = datetime.now()
            
            for position in positions:
                if position.magic != 234000:  # Only manage our trades
                    continue
                    
                # Check if position should be closed early
                if self._should_close_position(position, current_time):
                    self.close_position(position.ticket)
                    
        except Exception as e:
            self.logger.error(f"Error managing positions: {e}")
    
    def _should_close_position(self, position, current_time) -> bool:
        """Determine if position should be closed early"""
        # Close before weekend (Friday 23:00 UTC)
        if current_time.weekday() == 4 and current_time.hour >= 23:
            return True
            
        # Close if holding too long (risk management)
        position_time = datetime.fromtimestamp(position.time)
        if current_time - position_time > timedelta(hours=24):
            return True
            
        # Close if significant profit (take partial profits)
        if position.profit > (self.current_equity * 0.02):  # 2% profit
            return True
            
        return False
    
    def close_position(self, ticket: int) -> bool:
        """Close a specific position"""
        try:
            position = mt5.positions_get(ticket=ticket)
            if position is None or len(position) == 0:
                return False
                
            pos = position[0]
            
            # Prepare close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "position": ticket,
                "deviation": 20,
                "magic": 234000,
                "comment": "Close by bot",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                # Update statistics
                if pos.profit > 0:
                    self.consecutive_losses = 0
                else:
                    self.consecutive_losses += 1
                    
                self.daily_profit += pos.profit
                self.total_profit += pos.profit
                
                # Remove from active positions
                if ticket in self.active_positions:
                    del self.active_positions[ticket]
                    
                self.logger.info(f"Position closed: {pos.symbol} P&L: {pos.profit:.2f}")
                return True
            else:
                self.logger.error(f"Failed to close position {ticket}: {result.comment}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error closing position {ticket}: {e}")
            return False
    
    def daily_reset(self):
        """Reset daily statistics"""
        # Check if we had a profitable day
        if self.daily_profit >= (self.current_equity * 0.001):  # At least 0.1% profit
            self.profitable_days += 1
            
        self.daily_profit = 0
        self.daily_start_balance = self.current_equity
        self.daily_high_equity = self.current_equity
        
        self.logger.info(f"Daily reset - Profitable days: {self.profitable_days}/{len(self.trading_days)}")
    
    def run_trading_cycle(self):
        """Main trading logic cycle"""
        try:
            # Check account status
            status = self.check_account_status()
            
            if not status["can_trade"]:
                self.logger.warning("Trading disabled due to risk management")
                return
                
            # Manage existing positions
            self.manage_positions()
            
            # Look for new trading opportunities
            for symbol in self.primary_symbols:
                if not self.check_trading_conditions(symbol):
                    continue
                    
                # Multi-timeframe analysis
                signals = {}
                for tf in self.timeframes:
                    analysis = self.get_market_analysis(symbol, tf)
                    signals[tf] = analysis
                    
                # Combine signals (higher timeframes have more weight)
                final_signal = self._combine_signals(signals)
                
                if final_signal["signal"] in ["BUY", "SELL"] and final_signal["strength"] >= 4:
                    self.place_trade(symbol, final_signal["signal"], final_signal)
                    time.sleep(2)  # Brief pause between trades
                    
        except Exception as e:
            self.logger.error(f"Error in trading cycle: {e}")
    
    def _combine_signals(self, signals: Dict) -> Dict:
        """Combine multi-timeframe signals"""
        signal_scores = {"BUY": 0, "SELL": 0, "HOLD": 0}
        weights = {mt5.TIMEFRAME_H4: 3, mt5.TIMEFRAME_H1: 2, mt5.TIMEFRAME_M15: 1}
        
        total_strength = 0
        
        for tf, analysis in signals.items():
            weight = weights.get(tf, 1)
            signal = analysis.get("signal", "HOLD")
            strength = analysis.get("strength", 0)
            
            signal_scores[signal] += strength * weight
            total_strength += strength * weight
            
        # Determine final signal
        final_signal = max(signal_scores, key=signal_scores.get)
        final_strength = signal_scores[final_signal]
        
        return {
            "signal": final_signal,
            "strength": final_strength,
            "analysis": signals
        }
    
    def save_state(self):
        """Save bot state to file"""
        state = {
            "account_balance": self.account_balance,
            "current_equity": self.current_equity,
            "all_time_high_equity": self.all_time_high_equity,
            "total_trades": self.total_trades,
            "profitable_days": self.profitable_days,
            "trading_days": list(self.trading_days),
            "total_profit": self.total_profit,
            "consecutive_losses": self.consecutive_losses
        }
        
        with open("bot_state.json", "w") as f:
            json.dump(state, f, indent=2)
    
    def load_state(self):
        """Load bot state from file"""
        try:
            if os.path.exists("bot_state.json"):
                with open("bot_state.json", "r") as f:
                    state = json.load(f)
                    
                self.account_balance = state.get("account_balance", self.account_balance)
                self.current_equity = state.get("current_equity", self.current_equity)
                self.all_time_high_equity = state.get("all_time_high_equity", self.all_time_high_equity)
                self.total_trades = state.get("total_trades", 0)
                self.profitable_days = state.get("profitable_days", 0)
                self.trading_days = set(state.get("trading_days", []))
                self.total_profit = state.get("total_profit", 0)
                self.consecutive_losses = state.get("consecutive_losses", 0)
                
                self.logger.info("Bot state loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading bot state: {e}")
    
    def start_bot(self, login: int, password: str, server: str):
        """Start the trading bot"""
        if not self.initialize_mt5(login, password, server):
            return False
            
        self.load_state()
        
        # Schedule daily reset
        schedule.every().day.at("00:01").do(self.daily_reset)
        
        self.logger.info("FundedFriday Trading Bot started successfully")
        
        # Main bot loop
        while self.is_trading_enabled:
            try:
                # Run scheduled tasks
                schedule.run_pending()
                
                # Trading cycle every 15 minutes
                current_time = datetime.now()
                if current_time.minute % 15 == 0 and current_time.second < 30:
                    self.run_trading_cycle()
                    
                # Save state every hour
                if current_time.minute == 0 and current_time.second < 30:
                    self.save_state()
                    
                # Check account status every 5 minutes
                if current_time.minute % 5 == 0 and current_time.second < 30:
                    status = self.check_account_status()
                    
                    # Stop if target reached or major breach
                    if status["target_reached"]:
                        self.logger.info("PROFIT TARGET REACHED! Challenge passed!")
                        self.is_trading_enabled = False
                        break
                        
                    if status["breaches"]:
                        self.logger.error(f"ACCOUNT BREACHED: {status['breaches']}")
                        self.is_trading_enabled = False
                        break
                
                time.sleep(30)  # Sleep for 30 seconds
                
            except KeyboardInterrupt:
                self.logger.info("Bot stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
        
        # Cleanup
        self.save_state()
        mt5.shutdown()
        self.logger.info("Trading bot shut down")

# Usage example and configuration
if __name__ == "__main__":
    # Configuration - REPLACE WITH YOUR ACTUAL MT5 CREDENTIALS
    MT5_LOGIN = 12345678  # Your MT5 account number
    MT5_PASSWORD = "your_password"  # Your MT5 password
    MT5_SERVER = "YourBroker-Server"  # Your broker's server name
    
    ACCOUNT_BALANCE = 10000  # Your challenge account balance
    CHALLENGE_TYPE = "ONE_STEP"  # or "TWO_STEP"
    
    # Create and start the bot
    bot = FundedFridayTradingBot(ACCOUNT_BALANCE, CHALLENGE_TYPE)
    
    print("=== FundedFriday XAU/XAG Trading Bot ===")
    print(f"Account Balance: ${ACCOUNT_BALANCE:,}")
    print(f"Challenge Type: {CHALLENGE_TYPE}")
    print(f"Target Symbols: {bot.primary_symbols}")
    print("=====================================")
    
    # Start the bot
    bot.start_bot(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)