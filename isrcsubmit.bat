@echo off
setlocal
echo.
for /f "tokens=2 delims=:." %%x in ('chcp') do set cp=%%x
chcp 65001 >nul
python "%~dp0isrcsubmit.py" %*
chcp %cp% >nul
echo %cmdcmdline%|findstr /c:"%~nx0" >nul
if %errorlevel% equ 0 echo.&pause
