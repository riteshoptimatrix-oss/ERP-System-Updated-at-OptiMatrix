@echo off
echo ===================================================
echo Starting Local MongoDB for Opti Matrix ERP...
echo ===================================================

net start MongoDB >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Windows MongoDB Service started successfully!
    pause
    exit /b 0
)

echo Windows MongoDB Service requires Administrator privileges or is already running.
echo Starting MongoDB directly using local user directory...
if not exist "%USERPROFILE%\mongodata" mkdir "%USERPROFILE%\mongodata"
echo MongoDB running on mongodb://127.0.0.1:27017 (Data path: %USERPROFILE%\mongodata)
echo Keep this terminal window open while working!
echo.
"C:\Program Files\MongoDB\Server\8.0\bin\mongod.exe" --dbpath "%USERPROFILE%\mongodata" --wiredTigerCollectionBlockCompressor zstd --wiredTigerJournalCompressor zstd
