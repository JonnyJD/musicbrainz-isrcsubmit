@echo off
for /f "tokens=2 delims=:." %%x in ('chcp') do set cp=%%x
chcp 65001>NUL & cmd /c "isrcDigitalSubmit.py %*" & chcp %cp%>NUL
echo.
pause
