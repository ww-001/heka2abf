@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo [1/4] 创建 Python 虚拟环境...
set "PY=py"
py -3 -m venv .venv 2>nul || python -m venv .venv
set "VPY=.venv\Scripts\python.exe"
echo [2/4] 安装 numpy...
"%VPY%" -m pip install --upgrade pip
"%VPY%" -m pip install numpy
echo [3/4] 安装 HEKA 解析库...
copy /y "third_party\heka_reader.py" ".venv\Lib\site-packages\heka_reader.py" >nul
echo [4/4] 完成！双击 run_gui.bat 启动图形界面。
pause
endlocal