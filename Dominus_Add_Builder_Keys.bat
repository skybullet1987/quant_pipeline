@echo off
title Dominus - Add Polymarket Builder Keys
ssh -t kraken-finland "/home/skybullet1987/quant_pipeline/venv/bin/python3 /home/skybullet1987/quant_pipeline/scripts/set_builder_keys.py"
echo.
pause
