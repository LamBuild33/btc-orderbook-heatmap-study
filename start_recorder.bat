@echo off
title BTC heatmap recorder
call "%USERPROFILE%\anaconda3\Scripts\activate.bat" "%USERPROFILE%\anaconda3"
cd /d "%USERPROFILE%\btc-heatmap"
python coinbase_book_recorder.py
pause
