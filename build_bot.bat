@echo off
title Compiler
chcp 65001 > nul

echo ===================================================
echo   CTAPT CBOPKU TELEGRAM-BOTA B .EXE FAIL
echo ===================================================
echo.

REM Bypassing Rust build version check for Python 3.14 Compatibility
set PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

echo [1/4] Ustanovka PyInstaller i zavisimostey...
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller aiohttp
echo.

echo [2/4] Kompilyaciya proekta v odin .exe fail...
python -m PyInstaller --onefile --console --name="telegram_funnel_bot" --hidden-import="aiogram" --hidden-import="aiogram.dispatcher" --hidden-import="aiogram.filters" --hidden-import="aiogram.fsm.storage.memory" --hidden-import="aiogram.types" --hidden-import="aiosqlite" --hidden-import="aiohttp" --hidden-import="apscheduler" --hidden-import="apscheduler.schedulers.asyncio" --hidden-import="apscheduler.triggers.cron" --hidden-import="apscheduler.triggers.interval" --hidden-import="apscheduler.triggers.date" --hidden-import="telethon" --hidden-import="telethon.crypto" --hidden-import="telethon.extensions" --hidden-import="google.generativeai" --hidden-import="google.protobuf" --hidden-import="google.protobuf.descriptor" --hidden-import="google.protobuf.message" --add-data "postback.py;." main.py
echo.

echo [3/4] Kopirovanie .env v papku dist...
if exist .env (
    copy /y .env dist\.env
    echo [OK] .env skopirovan v dist!
) else (
    if exist .env.example (
        copy /y .env.example dist\.env
        echo [OK] .env.example skopirovan kak dist\.env!
    ) else (
        echo [!] .env ne naydeny v kornevoy papke proekta!
    )
)
echo.

echo [4/4] Ochistka vremennyx faylov...
if exist build rmdir /s /q build
if exist telegram_funnel_bot.spec del /f /q telegram_funnel_bot.spec
echo [OK] Vremennye papki ochisheny.
echo.

echo ===================================================
echo   SBORKA USPESHNO ZAVERSHENA!
echo.
echo   1. Otkroyte papku dist
echo   2. Zapustite telegram_funnel_bot.exe
echo ===================================================
echo.
pause
