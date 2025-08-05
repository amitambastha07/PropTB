import os
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class TradingConfig:
    # MT5 Connection Settings
    MT5_LOGIN: int = int(os.getenv('MT5_LOGIN', '0'))
    MT5_PASSWORD: str = os.getenv('MT5_PASSWORD', '')
    MT5_SERVER: str = os.getenv('MT5_SERVER', '')
    
    # Account Settings
    ACCOUNT_BALANCE: float = float(os.getenv('ACCOUNT_BALANCE', '10000'))
    CHALLENGE_TYPE: str = os.getenv('CHALLENGE_TYPE', 'ONE_STEP')  # ONE_STEP or TWO_STEP
    
    # Risk Management
    BASE_RISK_PER_TRADE: float = 0.012  # 1.2%
    MAX_RISK_PER_TRADE: float = 0.02    # 2%
    MAX_CONCURRENT_TRADES: int = 4
    MAX_TRADES_PER_SYMBOL: int = 2
    
    # Trading Settings
    PRIMARY_SYMBOLS: List[str] = None
    BACKUP_SYMBOLS: List[str] = None
    TRADING_HOURS: Dict[str, str] = None
    
    def __post_init__(self):
        if self.PRIMARY_SYMBOLS is None:
            self.PRIMARY_SYMBOLS = ['XAUUSD', 'XAGUSD']
        if self.BACKUP_SYMBOLS is None:
            self.BACKUP_SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY']
        if self.TRADING_HOURS is None:
            self.TRADING_HOURS = {
                'start': '01:00',  # UTC
                'end': '22:00',    # UTC
                'friday_close': '21:00'  # Close all trades by Friday 21:00 UTC
            }