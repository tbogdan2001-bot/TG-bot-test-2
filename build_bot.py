# build_bot.py
# Python-based compiler script that bypasses command line length and character parsing limits of Windows cmd.exe.
# Installs dependencies, runs PyInstaller, copies configuration files, and cleans up.

import os
import sys
import shutil
import subprocess

def safe_input(prompt=""):
    if sys.stdin and sys.stdin.isatty():
        return input(prompt)
    print(prompt)
    return ""


def main():
    print("===================================================")
    print("   СТАРТ СБОРКИ TELEGRAM-БОТА В .EXE ФАЙЛ (Python-Сборщик)")
    print("===================================================")
    
    # 1. Bypassing Rust build version check for Python 3.14 Compatibility
    os.environ["PYO3_USE_ABI3_FORWARD_COMPATIBILITY"] = "1"
    
    # 2. Install dependencies
    print("\n[1/4] Установка PyInstaller и зависимостей...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "pyinstaller"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка при установке зависимостей: {e}")
        safe_input("\nНажмите клавишу ENTER для выхода...")
        sys.exit(1)
        
    # 3. Compile with PyInstaller
    print("\n[2/4] Компиляция проекта в один .exe файл...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--console",
        "--name=telegram_funnel_bot",
        "--hidden-import=aiogram",
        "--hidden-import=aiogram.dispatcher",
        "--hidden-import=aiogram.filters",
        "--hidden-import=aiogram.fsm.storage.memory",
        "--hidden-import=aiogram.types",
        "--hidden-import=aiosqlite",
        "--hidden-import=apscheduler",
        "--hidden-import=apscheduler.schedulers.asyncio",
        "--hidden-import=apscheduler.triggers.cron",
        "--hidden-import=apscheduler.triggers.interval",
        "--hidden-import=apscheduler.triggers.date",
        "--hidden-import=telethon",
        "--hidden-import=telethon.crypto",
        "--hidden-import=telethon.extensions",
        "--hidden-import=google.generativeai",
        "--hidden-import=google.protobuf",
        "--hidden-import=google.protobuf.descriptor",
        "--hidden-import=google.protobuf.message",
        "--hidden-import=google.protobuf.pyext._message",
        "main.py"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка при компиляции PyInstaller: {e}")
        safe_input("\nНажмите клавишу ENTER для выхода...")
        sys.exit(1)
        
    # 4. Copy configuration files
    print("\n[3/4] Копирование конфигурационных файлов в папку сборки dist...")
    dist_dir = "dist"
    os.makedirs(dist_dir, exist_ok=True)
    
    if os.path.exists(".env"):
        shutil.copy(".env", os.path.join(dist_dir, ".env"))
        print("[УСПЕХ] Файл .env успешно скопирован в папку dist!")
    elif os.path.exists(".env.example"):
        shutil.copy(".env.example", os.path.join(dist_dir, ".env"))
        print("[УСПЕХ] Шаблон .env.example скопирован как dist\\.env!")
    else:
        print("[ВНИМАНИЕ] Конфигурационные файлы не найдены в корне проекта!")
        
    # 5. Clean up temporary files
    print("\n[4/4] Очистка временных файлов сборщика...")
    if os.path.exists("build"):
        shutil.rmtree("build", ignore_errors=True)
    if os.path.exists("telegram_funnel_bot.spec"):
        try:
            os.remove("telegram_funnel_bot.spec")
        except Exception:
            pass
    print("[УСПЕХ] Временные папки очищены.")
    
    print("\n===================================================")
    print("   СБОРКА УСПЕШНО ЗАВЕРШЕНА!")
    print("\n   1. Откройте появившуюся папку \"dist\"")
    print("   2. Запустите \"telegram_funnel_bot.exe\"")
    print("===================================================")
    safe_input("\nНажмите клавишу ENTER для выхода...")

if __name__ == "__main__":
    main()
