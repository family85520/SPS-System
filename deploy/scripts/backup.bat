@echo off
REM ============================================
REM deploy/scripts/backup.bat — Windows 数据库备份脚本
REM ============================================

setlocal

REM 获取应用目录（脚本所在目录的父目录）
set "SCRIPT_DIR=%~dp0"
set "APP_DIR=%SCRIPT_DIR%..\.."
set "ENV_FILE=%APP_DIR%\backend\.env"

if not exist "%ENV_FILE%" (
    echo [ERROR] 未找到 %ENV_FILE%
    exit /b 1
)

REM 读取 DATABASE_URL
for /f "tokens=1,2 delims==" %%a in ('findstr /C:"DATABASE_URL=" "%ENV_FILE%"') do (
    set "DATABASE_URL=%%b"
)

if "%DATABASE_URL%"=="" (
    echo [ERROR] .env 中未找到 DATABASE_URL
    exit /b 1
)

REM 解析 URL (postgresql+asyncpg://user:pass@host:port/dbname)
set "URL_BODY=!DATABASE_URL:*=*://"
set "USER_PASS=!URL_BODY:@=!"
set "USER_PASS=!USER_PASS:%%@=*!"
REM 简单解析：使用 PowerShell
for /f "delims=" %%p in ('powershell -Command "^$url = '%DATABASE_URL%'; $body = $url.Split('://')[1]; $up = $body.Split('@')[0]; Write-Output $up'") do (
    set "USER_PASS_PS=%%p"
)

set "BACKUP_DIR=%APP_DIR%\backups"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

for /f "tokens=2 delims==" %%d in ('powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do (
    set "TIMESTAMP=%%d"
)

set "BACKUP_FILE=%BACKUP_DIR%\db_%TIMESTAMP%.sql"

echo [INFO] 开始备份数据库...

REM 使用 psql 备份
set PGPASSWORD=psql -U scp -d scp_db -f "%BACKUP_FILE%" 2>&1

if exist "%BACKUP_FILE%" (
    for %%F in ("%BACKUP_FILE%") do (
        echo [OK] 备份完成: %BACKUP_FILE% (%%~zF bytes)
    )
) else (
    echo [ERROR] 备份失败
    exit /b 1
)

endlocal
