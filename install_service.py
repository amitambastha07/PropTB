import os
import sys

def create_service_script():
    """Create Windows service batch file"""
    
    service_script = f"""@echo off
cd /d "{os.getcwd()}"
python start_bot.py
pause
"""
    
    with open('run_bot.bat', 'w') as f:
        f.write(service_script)
    
    print("✅ Created run_bot.bat")
    print("You can now run the bot by double-clicking run_bot.bat")

def create_task_scheduler_xml():
    """Create Task Scheduler XML for Windows"""
    
    xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>2024-01-01T00:00:00</Date>
    <Author>FundedFriday Bot</Author>
    <Description>Automated trading bot for FundedFriday challenge</Description>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT5M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions>
    <Exec>
      <Command>python</Command>
      <Arguments>start_bot.py</Arguments>
      <WorkingDirectory>{os.getcwd()}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""
    
    with open('trading_bot_task.xml', 'w') as f:
        f.write(xml_content)
    
    print("✅ Created trading_bot_task.xml")
    print("Import this file in Windows Task Scheduler to run bot automatically")

if __name__ == "__main__":
    create_service_script()
    create_task_scheduler_xml()