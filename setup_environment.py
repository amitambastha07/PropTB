import os
import subprocess
import sys

def install_requirements():
    """Install required packages"""
    requirements = [
        'MetaTrader5==5.0.45',
        'pandas==2.0.3',
        'numpy==1.24.3',
        'schedule==1.2.0',
        'python-dotenv==1.0.0'
    ]
    
    for package in requirements:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✓ Installed {package}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {package}: {e}")

def create_directories():
    """Create necessary directories"""
    directories = [
        'trading_logs',
        'data',
        'backups'
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created directory: {directory}")

def create_env_file():
    """Create .env file template"""
    env_content = """# MT5 Connection Settings
MT5_LOGIN=your_account_number
MT5_PASSWORD=your_password
MT5_SERVER=your_broker_server

# Account Settings  
ACCOUNT_BALANCE=10000
CHALLENGE_TYPE=ONE_STEP

# Notification Settings (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✓ Created .env file template")
        print("⚠️  Please edit .env file with your actual MT5 credentials")

if __name__ == "__main__":
    print("Setting up FundedFriday Trading Bot environment...")
    install_requirements()
    create_directories() 
    create_env_file()
    print("Setup complete!")