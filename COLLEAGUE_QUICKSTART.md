# heka2abf 快速上手（给同事）

> 这是 WWT 实验室的电生理数据转换工具。**只做一件事**：把 HEKA PatchMaster 录的 `.dat` 文件转成 Clampfit 能读的 `.abf` 文件。**不需要你装任何环境**。

---

## 🚀 三步上手

**1. 解压** `heka2abf_windows_v0.2.0.zip` 到任意目录
   - 例：`D:\tools\heka2abf\`
   - ⚠️ **路径里别带中文**（Windows 上偶尔抽风）

**2. 双击 `run_gui.bat`**（注意：**不是** `install.bat`）
   - 首次启动约 3-5 秒
   - GUI 窗口弹出来就对了

**3. 转换 .dat 文件**
   - "Add files" 选单个 `.dat`，或 "Add folder" 选整个文件夹
   - 点 **"Convert"** 开始转
   - 转出来的 `.abf` 用 Clampfit 直接打开

---

## 🛑 不要做的事

- ❌ **别双击 `install.bat`** — zip 里已经预装好 Python + numpy 了，不需要重建 venv。误运行可能损坏依赖。
- ❌ **别删 `.venv\` 文件夹** — 那里面是预装的 Python 3.12 + numpy + heka_reader 解析库，删了 GUI 就跑不起来。
- ❌ **别放 OneDrive / 坚果云 / 网盘同步目录** — 这些工具会"占位"未下载的小文件，破坏 `.venv\` 结构。放本地磁盘。

---

## 🛟 遇到问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 杀软 / Windows Defender 报警 "未知发布者" | PyInstaller / 自打包 .exe 的常见误报 | 右键 → 属性 → 勾选"解除锁定"；或运行时点"仍要运行" |
| 双击 .bat 后窗口一闪就关 | 路径里有中文 / 权限不足 | 移到 `D:\xxx\heka2abf\` 这种纯 ASCII 路径 |
| 弹窗 "ModuleNotFoundError: No module named 'heka_reader'" | `.venv\` 被删除 / 损坏 / 同步工具占位 | 重新解压整个 zip 到本地磁盘 |
| GUI 弹不出来 | `.venv\Scripts\pythonw.exe` 不存在 | 重新解压 |
| 转换出来的 .abf 在 Clampfit 里打不开 | 用了非标准 acquisition mode | GUI 里把 "Mode" 改成 `auto` 或显式 `episodic` / `gapfree` 重试 |

---

## ❓ 这是什么

```
HEKA PatchMaster  .dat  →  heka2abf  →  Clampfit 可读的 .abf
```

技术栈：Python 3.12 + numpy + tkinter（GUI），所有依赖都打包在 zip 里。MIT 协议开源。

转码默认按 HEKA 物理单位归一化（V→mV，A→pA）；默认单 sweep 走 gap-free，多 sweep 走 episodic。

---

📮 有问题联系：[你的名字 / email]
📦 项目主页：https://github.com/ww-001/heka2abf
📝 Bug 报告：https://github.com/ww-001/heka2abf/issues

— WWT Lab · 2026