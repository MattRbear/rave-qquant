@echo off
echo ========================================
echo CVD Calculator - JSONL Mode
echo ========================================
echo.
echo Processing BTC-USDT...
python "C:\Users\M.R Bear\Documents\RaveQuant\CVD\run_cvd_from_jsonl.py" --symbol BTC-USDT
echo.
echo Processing ETH-USDT...
python "C:\Users\M.R Bear\Documents\RaveQuant\CVD\run_cvd_from_jsonl.py" --symbol ETH-USDT
echo.
echo ========================================
echo CVD Processing Complete
echo ========================================
pause
