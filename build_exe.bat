@echo off
REM Build "QR Code Studio.exe" from qr_app.py (put this file in the same folder as qr_app.py)
cd /d "%~dp0"

where py >nul 2>nul && (set PY=py) || (set PY=python)

echo [1/2] Installing libraries...
%PY% -m pip install --upgrade customtkinter "qrcode[pil]" pillow pyinstaller
if errorlevel 1 goto :fail

echo [2/2] Building .exe ...
%PY% -m PyInstaller --noconfirm --onefile --windowed --name "QR Code Studio" --collect-data customtkinter qr_app.py
if errorlevel 1 goto :fail

echo.
echo Done!  Your program is at:  dist\QR Code Studio.exe
explorer dist
pause
exit /b 0

:fail
echo.
echo Build failed - check the messages above.
pause
exit /b 1
