@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo [1/4] 创建 Python 虚拟环境...

rem --- 挑选一个"真"解释器：只有 -V 退出码为 0 的才采用 ---
rem     这挡住 Windows 的 Microsoft Store stub（应用执行别名）——
rem     它的提示写在 stdout，2>nul 屏蔽不掉；而 venv 根本没建成这件事
rem     本身不会暴露，同事只会看到后续一串"找不到指定的路径"。
set "BOOTPY="
for %%C in (py python python3) do (
    if not defined BOOTPY (
        %%C -V >nul 2>&1
        if not errorlevel 1 set "BOOTPY=%%C"
    )
)

if not defined BOOTPY (
    echo.
    echo [错误] 未找到可用的 Python 解释器。
    echo.
    echo   1^) 到 https://www.python.org/downloads/ 下载安装，务必勾选 Add to PATH
    echo   2^) 或关闭 Windows 的应用执行别名：设置 - 应用 - 高级应用设置
    echo      - 应用执行别名，把 python.exe 与 python3.exe 两个开关关掉
    echo      ^(它们只是 Microsoft Store 的占位符，不会真正执行脚本^)
    echo.
    pause
    exit /b 1
)

rem --- 已存在的 .venv 还可能有效，也可能因原解释器被卸载/移动而失效 ---
rem     只测文件存在是不够的：过期 venv 的 python.exe 还在，但一跑就报
rem     No Python at ...，所以必须真的执行一次 -V 看退出码。
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -V >nul 2>&1
    if errorlevel 1 (
        echo 检测到失效的 .venv ^(原解释器可能已被卸载或移动^)，正在重建...
        rmdir /s /q .venv
    )
)

if not exist ".venv\Scripts\python.exe" (
    "%BOOTPY%" -m venv .venv
    if errorlevel 1 (
        echo [错误] 虚拟环境创建失败，请检查上面的报错。
        pause
        exit /b 1
    )
)

set "VPY=.venv\Scripts\python.exe"

echo [2/4] 安装 numpy...
"%VPY%" -m pip install --upgrade pip
if errorlevel 1 goto :failed
"%VPY%" -m pip install numpy
if errorlevel 1 goto :failed

echo [3/4] 安装 HEKA 解析库...
copy /y "third_party\heka_reader.py" ".venv\Lib\site-packages\heka_reader.py" >nul
if errorlevel 1 goto :failed

echo [4/4] 完成！双击 run_gui.bat 启动图形界面。
pause
endlocal
exit /b 0

:failed
echo.
echo [错误] 安装过程失败，请把上面的报错信息发给 WWT。
pause
endlocal
exit /b 1
