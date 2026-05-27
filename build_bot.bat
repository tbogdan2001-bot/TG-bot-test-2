@echo off
title Telegram Bot EXE Compiler
chcp 65001 > nul
echo ===================================================
echo   СТАРТ СБОРКИ TELEGRAM-БОТА В .EXE ФАЙЛ
echo ===================================================
echo.

echo [1/4] Установка PyInstaller и зависимостей...
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
echo.

echo [2/4] Компиляция проекта в один .exe файл...
pyinstaller --onefile --console --name="telegram_funnel_bot" ^
  --hidden-import="aiogram" ^
  --hidden-import="aiogram.dispatcher" ^
  --hidden-import="aiogram.filters" ^
  --hidden-import="aiogram.fsm.storage.memory" ^
  --hidden-import="aiogram.types" ^
  --hidden-import="aiosqlite" ^
  --hidden-import="apscheduler" ^
  --hidden-import="apscheduler.schedulers.asyncio" ^
  --hidden-import="apscheduler.triggers.cron" ^
  --hidden-import="apscheduler.triggers.interval" ^
  --hidden-import="apscheduler.triggers.date" ^
  --hidden-import="telethon" ^
  --hidden-import="telethon.crypto" ^
  --hidden-import="telethon.extensions" ^
  --hidden-import="google.generativeai" ^
  --hidden-import="google.protobuf" ^
  --hidden-import="google.protobuf.descriptor" ^
  --hidden-import="google.protobuf.message" ^
  --hidden-import="google.protobuf.pyext._message" ^
  main.py

echo.
echo [3/4] Копирование конфигурационного файла .env в папку сборки...
if exist .env (
    copy .env dist\.env
    echo [УСПЕХ] Файл .env успешно скопирован в папку dist!
) else (
    echo [ПРЕДУПРЕЖДЕНИЕ] Файл .env не найден в корне. Пожалуйста, скопируйте его в папку dist вручную.
)
echo.

echo [4/4] Очистка временных файлов сборщика...
if exist build rmdir /s /q build
if exist telegram_funnel_bot.spec del /f /q telegram_funnel_bot.spec
echo [УСПЕХ] Временные папки очищены.
echo.

echo ===================================================
echo   СБОРКА УСПЕШНО ЗАВЕРШЕНА!
echo.
echo   1. Откройте появившуюся папку "dist"
echo   2. Запустите "telegram_funnel_bot.exe"
echo ===================================================
echo.
pause
