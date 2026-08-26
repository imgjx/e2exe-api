@echo off
chcp 65001 >nul
title 易语言编译服务

echo ========================================
echo    易语言编译服务启动中...
echo ========================================
echo.
echo 服务地址: http://localhost:8800
echo API文档:
echo   POST /MakeE     - 提交编译
echo   POST /State     - 查询状态
echo   POST /DownFile  - 下载文件
echo   GET  /Health    - 健康检查
echo   GET  /ListTasks - 列出任务
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

python app.py

pause