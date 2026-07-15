@echo off
echo ============================================
echo  Building Offline Radio Builder.exe
echo ============================================

pip install -r requirements.txt
pip install pyinstaller

pyinstaller OfflineRadioBuilder.spec --noconfirm

echo.
echo ============================================
echo  Done. EXE is at: dist\OfflineRadioBuilder.exe
echo ============================================
pause
