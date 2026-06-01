@echo off
:: ============================================================
:: RealtorPal Bot — Windows Auto-Restart Script
:: Double-click this file to start the bot.
:: It will automatically restart if it crashes.
:: Close this window to stop the bot.
:: ============================================================

title RealtorPal Bot - @RealtorpalBot
color 0A

:LOOP
echo.
echo ============================================================
echo  RealtorPal Bot starting...
echo  Window: Keep this window open to keep the bot running.
echo  Stop:   Close this window or press Ctrl+C
echo ============================================================
echo.

cd /d "%~dp0"
python run_bot_simple.py

echo.
echo [!] Bot stopped. Restarting in 5 seconds...
echo     (Close this window to stop permanently)
echo.
timeout /t 5 /nobreak >nul
goto LOOP
