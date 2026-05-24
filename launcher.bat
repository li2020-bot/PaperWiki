@echo off
chcp 65001 >nul
REM PaperWiki Launcher (Windows)
REM 双击此文件即可启动 PaperWiki 监控服务

cd /d "%~dp0"

echo ==========================================
echo   PaperWiki - 论文自动处理服务
echo   配置: %CD%\config.yaml
echo ==========================================

if not exist "config.yaml" (
    echo [错误] 未找到 config.yaml，请先配置！
    echo 将 config.yaml.example 重命名为 config.yaml，然后编辑填写你的配置。
    pause
    exit /b 1
)

if exist "paperwiki.exe" (
    echo [启动] 开始监控论文目录...
    paperwiki.exe
    echo PaperWiki 已停止
    pause
) else (
    echo [错误] 未找到 paperwiki.exe 可执行文件
    pause
    exit /b 1
)
