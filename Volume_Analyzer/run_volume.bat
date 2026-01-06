@echo off
echo ========================================
echo VOLUME ANALYZER
echo ========================================
echo.
echo Adversarial Volume Intelligence:
echo - Volume tiers (T1-T4)
echo - Whale filtering (trades over $100k)
echo - Absorption detection (wall defense)
echo - Divergence detection (exhaustion)
echo.
echo Processing BTC-USDT-SWAP...
python volume_analyzer.py --instId BTC-USDT-SWAP
echo.
echo Processing ETH-USDT-SWAP...
python volume_analyzer.py --instId ETH-USDT-SWAP
echo.
echo ========================================
echo VOLUME ANALYSIS COMPLETE
echo ========================================
echo.
echo Output: Vault\derived\volume\okx\perps\{INSTID}\volume_1m.jsonl
echo State: Vault\state\volume\okx\perps\{INSTID}.state.json
echo.
pause
