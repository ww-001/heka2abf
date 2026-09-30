# heka2abf v0.2.1 (2026-09-30)

修复 v0.2.0 中**中文 Windows 上 `.bat` 启动脚本输出乱码**的问题。

**如果你在 v0.2.0 遇到过双击 `install.bat` 后中文变成 `鍒涘缓` 之类，就是这个版本要解决的。**

---

## 修了什么

### 1. `install.bat` 中文乱码

该文件含中文字符（如 `echo [1/4] 创建 Python 虚拟环境...`）却存为 **UTF-8 无 BOM**，
CMD 会按 OEM/ANSI 代码页解码，输出乱码。现统一为 **UTF-8 with BOM** 并补上
`chcp 65001 >nul`，让控制台也切到 UTF-8。

`run_gui.bat` / `run_gui_console.bat` 同样补上 `chcp 65001 >nul`。

### 2. `install.bat` 的解释器探测写法有缺陷

v0.2.0 里是这么写的：

```bat
py -3 -m venv .venv 2>nul || python -m venv .venv
```

Win10/11 自带的"应用执行别名"里，`python.exe` 是 **Microsoft Store 的占位符**。
它的提示写在 **stdout**，所以 `2>nul` 屏蔽不掉；而且 venv 根本没建成这件事
本身不会暴露，同事只会看到后面一串"找不到指定的路径"。

改为**显式检测一次**：只有 `-V` 退出码为 0 的解释器才采用；检测不到就打印
可操作的错误提示（去哪下载、或者去关哪个开关）并退出，不再静默失败。

### 3. venv 失效不再卡死

如果机器上的 Python 被卸载或移动过，`.venv` 里的 `python.exe` 还在，但一跑就报
`No Python at ...`。新版本会**执行一次 `-V` 验证**，确认失效后自动重建，
而不是让同事对着报错发呆。

### 4. 机制性修复

- 新增 `.gitattributes`：`*.bat` / `*.cmd` 设 `text eol=crlf`，仓库内统一存 LF、
  检出时转 CRLF。此前行尾完全靠每个文件手动维护，必然会漏。
- `make_windows_bundle.bat` 补 BOM，行尾 LF → CRLF。

---

## 怎么用

下载 `heka2abf_windows_v0.2.1.zip` 解压即用，**不需要装任何环境**。
详见仓库里的 `COLLEAGUE_QUICKSTART.md`。

从源码安装的改用 `pip install heka2abf==0.2.1`。

> **注意**：如果你已经下载过 v0.2.0 且一切正常，**不需要急着换**——
> v0.2.1 的改动主要影响 `install.bat`（源码安装路径）。
> 走 bundle 的同事解压后直接双击 `run_gui.bat`，v0.2.0 也是可用的。
> 但如果你遇到过中文乱码，请务必换到 v0.2.1。

## 完整变更

见 [CHANGELOG.md](https://github.com/ww-001/heka2abf/blob/main/CHANGELOG.md)。
