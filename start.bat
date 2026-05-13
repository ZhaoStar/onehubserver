@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: =====================================================
::  OneHub 启动脚本 (Windows 本地开发)
:: =====================================================

cd /d "%~dp0"

echo.
echo ============================================
echo   OneHub 后端服务
echo ============================================

:: 检查 .env 文件
if not exist ".env" (
    echo [警告] 未找到 .env 文件，将使用默认配置
    echo 请复制 .env.example 为 .env 并填写配置
    echo.
)

:: 检测 Python
set PYTHON=
for %%p in (python python3) do (
    where %%p >nul 2>&1
    if !errorlevel!==0 (
        set PYTHON=%%p
        goto :found_python
    )
)
:found_python

if "%PYTHON%"=="" (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo [信息] 使用 Python: %PYTHON%
%PYTHON% --version
echo.

:: 检查 FFmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 未找到 ffmpeg，视频转MP3功能将不可用
    echo 请下载 FFmpeg 并添加到 PATH: https://ffmpeg.org/download.html
    echo.
) else (
    echo [信息] FFmpeg 已就绪
    echo.
)

:: 安装依赖（可选）
if exist "requirements.txt" (
    echo [信息] 检查依赖...
    %PYTHON% -m pip install -r requirements.txt -q 2>nul
    echo [信息] 依赖检查完成
    echo.
)

:: 启动服务
echo [信息] 启动服务 http://localhost:8000
echo [信息] API 文档 http://localhost:8000/docs
echo [信息] 按 Ctrl+C 停止
echo ============================================
echo.

%PYTHON% -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
