@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

echo ========================================
echo  Cluster Manager - Windows 构建脚本
echo  产物: cluster-manager-deploy.zip
echo ========================================

:: ── 步骤 1：构建前端 ────────────────────────────────────────
echo.
echo [1/3] 构建前端 (npm run build)...
cd frontend

where node >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 https://nodejs.org
    exit /b 1
)

call npm install
if errorlevel 1 ( echo [错误] npm install 失败 & exit /b 1 )

call npm run build
if errorlevel 1 ( echo [错误] npm run build 失败 & exit /b 1 )

cd ..
echo   -^> 前端已构建到 backend\static\

:: ── 步骤 2：清理旧包 ────────────────────────────────────────
echo.
echo [2/3] 清理旧部署包...
if exist cluster-manager-deploy.zip del /f cluster-manager-deploy.zip

:: ── 步骤 3：打包部署目录 ────────────────────────────────────
echo.
echo [3/3] 打包部署目录...

:: 用 PowerShell 的 Compress-Archive 打包
:: 排除不必要的目录: __pycache__, *.pyc, dist/, .git 等
powershell -NoProfile -Command ^
    "Get-ChildItem -Path 'backend' -Recurse | " ^
    "Where-Object { $_.FullName -notmatch '\\__pycache__' -and " ^
    "               $_.FullName -notmatch '\\.pyc$' -and " ^
    "               $_.FullName -notmatch '\\dist\\' -and " ^
    "               $_.FullName -notmatch '\\build\\' } | " ^
    "Compress-Archive -DestinationPath 'cluster-manager-deploy.zip' -Force"

if not exist cluster-manager-deploy.zip (
    echo [错误] 打包失败
    exit /b 1
)

:: 显示包大小
for %%F in (cluster-manager-deploy.zip) do set SIZE=%%~zF
set /a SIZE_MB=!SIZE! / 1048576
echo   -^> 打包完成: cluster-manager-deploy.zip (!SIZE_MB! MB)

:: ── 完成提示 ────────────────────────────────────────────────
echo.
echo ========================================
echo  构建完成！
echo ========================================
echo.
echo 部署步骤：
echo   1. 传输到 ARM 服务器：
echo      scp cluster-manager-deploy.zip root@^<arm-ip^>:/opt/
echo.
echo   2. 在 ARM 服务器上运行 deploy.sh（见项目根目录）：
echo      ssh root@^<arm-ip^> 'cd /opt ^&^& unzip cluster-manager-deploy.zip -d cluster-manager ^&^& cd cluster-manager ^&^& chmod +x deploy.sh ^&^& ./deploy.sh'
echo.
echo   3. Windows 浏览器访问：
echo      http://^<arm-ip^>:8000
echo ========================================
