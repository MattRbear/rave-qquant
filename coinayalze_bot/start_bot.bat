@echo off
echo ========================================
echo COINALYZE BOT - LAUNCHER
echo ========================================
echo.

echo Installing dependencies...
pip install -r requirements.txt
echo.

echo ========================================
echo Starting Coinalyze Bot
echo ========================================
echo Mode: Continuous (1min interval)
echo Symbols: BTC, ETH
echo Data: OI, Liquidations, Funding, Bull/Bear
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

python coinalyze_bot.py

pause
