@echo off
setlocal
echo.
for /f "tokens=2 delims=:." %%x in ('chcp') do set cp=%%x
chcp 65001 >NUL
python "%~dp0isrcsubmit.py" %*
chcp %cp% >NUL
