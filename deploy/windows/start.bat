@echo off
chcp 65001
setlocal

set APP_DIR=%~dp0..\..
cd /d %APP_DIR%\backend

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 启动服务
echo 启动排班管理系统后端服务...
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
