@echo off
echo ========================================
echo UNTOUCHED WICK TRACKER
echo ========================================
echo.
echo YOUR EDGE: Small wicks 20-40 min back
echo Exact tip-to-tip touches that fade
echo.
echo Processing BTC-USDT-SWAP...
python untouch_wick.py --instId BTC-USDT-SWAP
echo.
echo Processing ETH-USDT-SWAP...
python untouch_wick.py --instId ETH-USDT-SWAP
echo.
echo ========================================
echo WICK TRACKING COMPLETE
echo ========================================
echo.
echo Check wicks_active.json for current untouched wicks
echo Check wicks_events.jsonl for full audit trail
echo.
pause
