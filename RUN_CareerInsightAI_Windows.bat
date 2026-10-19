@echo off
setlocal
cd /d "%~dp0"
echo Starting CareerInsight AI...
echo Local development cookies are configured for HTTP.
echo Keep this window open while using the app.
cd frontend
npm run dev
pause
