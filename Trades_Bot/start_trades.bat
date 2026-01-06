@echo off
echo ========================================
echo OKX Trades Exporter - PERPS ONLY
echo ========================================
echo.
echo Instruments: BTC-USDT-SWAP, ETH-USDT-SWAP
echo Output: Vault\raw\okx\trades_perps\
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

python trades_exporter.py

pause
