@echo off
chcp 65001 >nul
title OpenClaw 自定义目录安装工具

:: ========== 可自行修改这里 ==========
set "INSTALL_DIR=D:\OpenClaw"
set "OPENCLAW_DATA=D:\OpenClaw\.openclaw"
:: ===================================

echo ==============================================
echo   OpenClaw 自定义路径安装（Windows BAT）
echo   安装目录：%INSTALL_DIR%
echo   数据目录：%OPENCLAW_DATA%
echo ==============================================
echo.

:: 创建目录
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%OPENCLAW_DATA%" mkdir "%OPENCLAW_DATA%"

:: 永久设置用户环境变量 OPENCLAW_HOME
setx OPENCLAW_HOME "%OPENCLAW_DATA%" >nul 2>&1
echo [√] 已设置环境变量 OPENCLAW_HOME

echo.
echo [开始执行 OpenClaw 安装... ]
echo.

:: 调用PowerShell 自定义目录安装
powershell -Command ^
"$installDir = '%INSTALL_DIR%'; ^
$script = Invoke-RestMethod -Uri 'https://openclaw.bot/install.ps1' -UseBasicParsing; ^
& ([scriptblock]::Create($script)) -InstallMethod git -GitDir $installDir"

echo.
echo [√] 安装命令执行完成
echo.
echo 请执行以下命令验证：
echo openclaw --version
echo.
echo 如需初始化配置，请执行：
echo openclaw onboard
echo.
pause