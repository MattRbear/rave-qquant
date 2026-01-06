@echo off
echo ========================================
echo L2 LIQUIDITY BUCKETIZER
echo ========================================
echo.
echo Young Walls + Imbalance Detection
echo Anti-Noise Filters Active:
echo - 30s persistence minimum
echo - 1h stale reset
echo - $100k significant deltas
echo - Asset-specific thresholds
echo.
echo Processing BTC-USDT-SWAP...
python l2_bucketizer.py --instId BTC-USDT-SWAP --since 240m
echo.
echo Processing ETH-USDT-SWAP...
python l2_bucketizer.py --instId ETH-USDT-SWAP --since 240m
echo.
echo ========================================
echo BUCKET CALCULATION COMPLETE
echo ========================================
echo.
echo Output: Vault\derived\liquidity_buckets\okx\perps\{INSTID}\{DATE}.jsonl
echo State: Vault\state\liquidity_buckets\okx\perps\{INSTID}.state.json
echo.
pause
