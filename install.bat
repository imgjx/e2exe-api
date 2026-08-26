@echo off
chcp 65001 >nul
title 安装依赖

echo ========================================
echo    安装 Python 依赖
echo ========================================
echo.

pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo ========================================
echo    安装完成！
echo    请确保 ecl.exe 已放置到当前目录
echo ========================================
pause