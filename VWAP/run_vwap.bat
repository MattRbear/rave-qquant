@echo off
echo ========================================
echo VWAP Calculator - Rolling 1h + 4h
echo ========================================
echo.
echo Processing BTC-USDT-SWAP...
python vwap_calculator.py --instId BTC-USDT-SWAP
echo.
echo Processing ETH-USDT-SWAP...
python vwap_calculator.py --instId ETH-USDT-SWAP
echo.
echo ========================================
echo VWAP Processing Complete
echo ========================================
pause
