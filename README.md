# heka2abf

> 🇨🇳 **中文版说明见下方「中文简介」段** / For Chinese users, see "中文简介" section below.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/github/actions/status/ww-001/heka2abf/tests.yml?branch=main&label=tests)](../../actions)
[![GitHub release](https://img.shields.io/github/v/release/ww-001/heka2abf?include_prereleases)](../../releases)

**Latest stable:** v0.2.0 · **First release:** v0.2.0 · **Platform:** Windows 10/11 (primary) · macOS / Linux (CLI) · **Stack:** Python 3.9+ + numpy + pyabf (tests) + tkinter

A Python tool (CLI + tkinter GUI) that converts HEKA PatchMaster `.dat` files
to **ABF2** (Axon Binary Format 2), the format readable by Molecular Devices
Clampfit and the [swharden/pyABF](https://github.com/swharden/pyABF) library.

The project includes a **self-contained ABF2 writer** — no external ABF
write dependency is required (pyABF only supports writing ABF1, which loses
information). The writer mirrors real Clampfit file layout: FB file section,
PIL / ADC / STR / DATA / SIC sections, SSCH string area; **int16 + per-channel
scale factors** storage (matching pClamp-native files); values are converted
to physical units via HEKA's `DataScaler` / `ZeroData`.

---

## ✨ Features

| Category | Capability |
|---|---|
| **HEKA reader** | Parses HEKA `.dat` tree (Group → Series → Sweep → Trace) via the vendored [campagnola/heka_reader](https://github.com/campagnola/heka_reader) module. |
| **ABF2 writer** | Self-contained; mirrors real Clampfit layout (FB / PIL / ADC / STR / DATA / SIC + SSCH strings); int16 + per-channel scale. |
| **Multi-channel** | ADC channels within a series are interleaved into one ABF file (channel = trace ADC number, sweep = HEKA sweep). Use `--one-file-per-channel` to split per ADC. |
| **Unit normalization** | V → mV, A → pA by default (signal values scaled in lockstep); configurable in `heka2abf/convert.py`. |
| **Acquisition mode auto** | Multi-sweep series → episodic (mode 5); single-sweep / continuous → gap-free (mode 3). Override with `--mode episodic` / `--mode gapfree`. |
| **Variable-length sweeps** | HEKA's "last-sweep-cut-short" pattern (interrupted recordings) is handled natively via the ABF2 SIC synch array — Clampfit and pyABF read each sweep correctly. |
| **Sweep start times** | HEKA `SweepRecord.Time` written to SIC; absolute sweep timing in Clampfit matches PatchMaster. |
| **Organization** | Output goes to `<out>/<dat file stem>/<...>.abf` so each `.dat`'s results stay together. |
| **GUI** | Tkinter interface (no third-party GUI deps) — add files / folders, output location, mode, real-time log. |
| **CLI** | `heka2abf data.dat -o out/` plus `--inspect` for structure dump. |

---

## 🚀 Quick Start

### From PyPI (once published)

```bash
pip install heka2abf
# heka_reader.py is NOT on PyPI (vendored, no upstream license);
# install.bat / install.sh copies it into site-packages automatically.
```

### From source (development)

```bash
git clone https://github.com/ww-001/heka2abf.git
cd heka2abf
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
pip install numpy pyabf
cp third_party/heka_reader.py .venv/lib/python*/site-packages/
# Windows (PowerShell)
.\.venv\Scripts\pip install numpy pyabf
copy /y third_party\heka_reader.py .venv\Lib\site-packages\heka_reader.py
```

### GUI launch

| OS | Command |
|---|---|
| Windows | Double-click `run_gui.bat` |
| macOS / Linux | `python -m heka2abf.gui` |

### CLI conversion

```bash
# Inspect a .dat bundle (no conversion)
heka2abf data.dat --inspect

# Convert (output to out/<dat-stem>/<...>.abf)
heka2abf data.dat -o out/

# One ABF per ADC channel
heka2abf data.dat -o out/ --one-file-per-channel

# Force acquisition mode
heka2abf data.dat -o out/ --mode episodic
heka2abf data.dat -o out/ --mode gapfree
```

---

## 📦 Sharing with Colleagues (Windows-only pack-and-go)

The repo ships with one-click installers for non-Python-expert users:

1. Copy the whole `heka2abf` folder to the colleague (must include
   `install.bat`, `run_gui.bat`, `third_party/heka_reader.py`);
2. The colleague's machine needs **Python 3.9+** (from python.org, with
   "Add Python to PATH" ticked);
3. They double-click `install.bat` — creates an isolated `.venv`, installs
   numpy, copies the HEKA parser. One-time setup;
4. Then double-click `run_gui.bat` to launch the GUI — no further setup.

Notes:

* Conversion only needs **numpy + heka_reader** (installed by `install.bat`).
  `pyabf` is only used by the bundled tests and is **not** required.
* Always launch with `run_gui.bat` (it uses the bundled venv Python and hides
  the console window). Don't launch `python heka2abf/gui.py` with the system
  Python — it won't find dependencies.
* For fully-no-install delivery, a PyInstaller-bundled `.exe` is the next step.

---

## 🗂️ HEKA → ABF2 Mapping

| HEKA | ABF2 |
|---|---|
| Series | One file |
| ADC channel (trace) | ABF channel (interleaved) |
| Sweep | ABF sweep (episodic mode, mode 5) |
| `XInterval` (seconds) | `PIL.fADCSequenceInterval` (microseconds) |
| `YUnit` / trace `Label` | ADC channel unit / name (STR string index) |

---

## ✅ Verification

`tests/test_abf2writer.py` reads the writer's output back via pyABF:

* **Synthetic round-trip** — channel count / sweep count / sample rate /
  names + units / waveform all match exactly.
* **Real-Clampfit-file emulation** — `reference/model_vc_ramp.abf` (50 sweeps)
  is rewritten and re-read; the max absolute physical-value difference stays
  within int16 quantization.
* `tests/test_real_dat.py` (gated by the `real_dat` marker, **skipped on CI**) —
  end-to-end comparison on real HEKA `.dat` files including variable-length
  sweeps, two-channel IV curves, 30+ sweep CC injection, membrane tests.
  **Max absolute error = 0** on every sample.

Run locally:

```bash
# synthetic (always runs)
pytest tests/test_abf2writer.py -v

# real-file round-trip (requires your own .dat files; skipped on CI)
pytest tests/test_real_dat.py -v -m real_dat -- path/to/your.dat [path/to/...]
```

---

## ⚠️ Known Limitations

* HEKA files written with PatchMaster's optional lossy compression (min/max
  pairs) are read back as raw min/max values by `heka_reader`. Standard
  patch-clamp recordings are uncompressed, so this doesn't affect typical use.
* Two SSCH-string header offset fields (bytes 12 / 16 within the entry) are
  generated by the heuristic of real Clampfit files (44 + first-string length /
  44 + total length); pyABF does not read them, and Clampfit's string window
  ignores them in practice.

---

## 🧰 Reference Data

* `reference/*.abf` — real Clampfit ABF2 files from the
  [swharden/pyABF](https://github.com/swharden/pyABF) repo (MIT licensed);
  used as format references.
* `tools/abf2_dump.py` — hex-dump a real ABF2 file (FB section, section
  index, PIL / ADC / STR / DATA / SIC fields). Use this to study what
  Clampfit writes and to cross-check the files produced by heka2abf.
* `third_party/heka_reader.py` — Luke Campagnola's HEKA `.dat` parser,
  vendored as a single-file module (upstream has no PyPI release and no
  license file; `install.bat` / `install.sh` copy it into site-packages).

---

## 📝 Citation

If you use heka2abf in your research, please cite:

```bibtex
@software{heka2abf,
  author       = {Wang, Wenting},
  title        = {heka2abf: HEKA PatchMaster .dat to ABF2 file converter},
  version      = {0.2.0},
  year         = {2026},
  url          = {https://github.com/ww-001/heka2abf},
  note         = {Self-contained ABF2 writer (int16 + per-channel scale), multi-channel interleaved, episodic/gap-free auto mode, variable-length sweep handling via SIC.}
}
```

---

## 📜 License

[MIT](LICENSE) — Copyright © 2026 Wenting Wang. See [LICENSE](LICENSE) for the
full text.

---

## 🛠️ Development

```bash
git clone https://github.com/ww-001/heka2abf.git
cd heka2abf
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"                              # editable install with test deps
pytest tests/test_abf2writer.py -v                   # synthetic-data tests
```

For contributors:

* Run `pytest tests/test_abf2writer.py -v` before sending a PR — it must
  stay green across Python 3.9–3.12 (CI matrix).
* New code must round-trip cleanly under int16 quantization (max abs error
  ≤ `peak * 1e-4`).
* Update `CHANGELOG.md` under a new section heading `[X.Y.Z] - YYYY-MM-DD`.

---

## 中文简介

**heka2abf** 是把 HEKA PatchMaster 的 `.dat` 文件转换成 **ABF2**
（Axon Binary Format 2）文件的 Python 工具（命令行 + 图形界面），转换结果
可直接被 Molecular Devices Clampfit 以及 [swharden/pyABF](https://github.com/swharden/pyABF) 打开分析。

项目自带**完整的 ABF2 写入器** —— 不依赖任何 ABF 写入库（pyABF 只能写 ABF1，
会丢失信息）。写入器按真实 Clampfit 文件布局实现：FB 文件段、PIL / ADC /
STR / DATA / SIC 分节、SSCH 字符串区；采用 **int16 + 每通道缩放系数** 存储
（与 pClamp 原生文件一致），数值已按 HEKA 的 `DataScaler` / `ZeroData` 换算
成物理单位。

### 主要功能

* **HEKA 解析**：基于 vendored 的 [campagnola/heka_reader](https://github.com/campagnola/heka_reader) 模块解析 HEKA `.dat` 的树形结构（Group → Series → Sweep → Trace）。
* **ABF2 写入器**：自研，不依赖外部库；按真实 Clampfit 头部布局（FB / PIL / ADC / STR / DATA / SIC + SSCH 字符串）实现；int16 + 每通道缩放系数。
* **多通道交织**：同一 HEKA Series 内的 ADC 通道交织保存到一个 ABF 文件（通道 = trace ADC 号，sweep = HEKA sweep）；可用 `--one-file-per-channel` 按通道拆分。
* **单位换算**：默认 V → mV、A → pA（信号值同步缩放）；可在 `heka2abf/convert.py` 中配置。
* **采集模式自动**：多 sweep 系列 → episodic（mode 5）；单 sweep / 连续记录 → gap-free（mode 3）。可用 `--mode episodic` / `--mode gapfree` 强制。
* **变长 sweep 处理**：HEKA 常见的"最后 sweep 提前结束"（记录中断）通过 ABF2 SIC 同步数组原生支持 —— Clampfit / pyABF 能正确逐 sweep 读取。
* **sweep 起始时间**：HEKA `SweepRecord.Time` 写入 SIC；Clampfit 中 sweep 的绝对时间与 PatchMaster 一致。
* **输出组织**：结果保存到 `<输出>/<dat 文件主名>/<...>.abf`，同一 `.dat` 的结果都在同名文件夹里。
* **图形界面**：Tkinter 实现（无第三方 GUI 依赖）—— 添加文件 / 文件夹、输出位置、模式选择、实时日志。
* **命令行**：`heka2abf data.dat -o out/`，支持 `--inspect` 查看结构。

### 快速上手

```bash
# 源码运行（开发机，需 Python 3.9+）
git clone https://github.com/ww-001/heka2abf.git
cd heka2abf
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
pip install numpy pyabf
cp third_party/heka_reader.py .venv/lib/python*/site-packages/
# Windows (PowerShell)
.\.venv\Scripts\pip install numpy pyabf
copy /y third_party\heka_reader.py .venv\Lib\site-packages\heka_reader.py
```

| 操作系统 | 启动 GUI |
|---|---|
| Windows | 双击 `run_gui.bat` |
| macOS / Linux | `python -m heka2abf.gui` |

### 命令行转换

```powershell
# 查看 .dat 结构（不转换）
heka2abf data.dat --inspect

# 转换（结果在 out/<dat文件主名>/ 下）
heka2abf data.dat -o out/

# 按通道拆分
heka2abf data.dat -o out/ --one-file-per-channel

# 强制模式
heka2abf data.dat -o out/ --mode episodic
heka2abf data.dat -o out/ --mode gapfree
```

### 发给同事使用（Windows 一键装机包）

仓库自带一键安装脚本：

1. 把整个 `heka2abf` 文件夹复制给同事（包含 `install.bat`、`run_gui.bat`、`third_party/heka_reader.py` 等）；
2. 同事电脑需装 **Python 3.9+**（python.org 安装时勾选 "Add Python to PATH"）；
3. 双击 `install.bat`：自动创建独立的 `.venv` 环境，安装 numpy 并复制 HEKA 解析库（一次性）；
4. 之后双击 `run_gui.bat` 打开图形界面，无需再配置。

注意：

* 转换功能只需要 **numpy + heka_reader**（`install.bat` 自动装好）。`pyabf` 仅用于自带测试，**不需要**安装。
* 一定要用 `run_gui.bat` 启动（自带 venv Python，无控制台窗口）。不要直接用系统 Python 跑 `python heka2abf/gui.py` —— 缺依赖。
* 若要彻底免安装，下一步可用 PyInstaller 打包成 `.exe`。

### 结构映射

| HEKA | ABF2 |
|---|---|
| Series | 一个文件 |
| ADC 通道（trace） | ABF 通道（交织） |
| Sweep | ABF sweep（episodic 模式，mode 5）|
| `XInterval`（秒） | `PIL.fADCSequenceInterval`（微秒）|
| `YUnit` / trace `Label` | ADC 通道单位 / 名称（STR 字符串索引）|

### 验证

`tests/test_abf2writer.py` 用 pyABF 回读写入结果：

* **合成数据往返**：通道数 / sweep 数 / 采样率 / 名称单位 / 波形完全一致；
* **真实 Clampfit 文件回放**：`reference/model_vc_ramp.abf`（50 sweeps）的物理值重写后回读，差异落在 int16 量化误差内；
* `tests/test_real_dat.py`（标 `real_dat` 标记，**CI 上默认跳过**）：用自己的真实 HEKA `.dat`（变长 sweep、双通道 IV 曲线、30+ sweep CC 注入、膜测试等）做端到端逐点对比，**最大绝对误差 = 0**。

本地运行：

```bash
# 合成测试（始终跑）
pytest tests/test_abf2writer.py -v

# 真实文件回放（需要你自己的 .dat；CI 上跳过）
pytest tests/test_real_dat.py -v -m real_dat -- path/to/your.dat [path/to/...]
```

### 已知限制

* HEKA 文件若开启 PatchMaster 的可选有损压缩（min/max 成对存储），`heka_reader` 会原样读出压缩值；标准膜片钳记录通常不压缩。
* SSCH 字符串头中两个偏移字段（条目内第 12/16 字节）按真实 Clampfit 文件规律生成（44 + 首串长度 / 44 + 总长）；pyABF 完全不读它们，Clampfit 字符串窗在实践中忽略。

### 参考数据

* `reference/*.abf` —— 真实 Clampfit ABF2 文件，来自 [swharden/pyABF](https://github.com/swharden/pyABF)（MIT 许可），仅作格式对照；
* `tools/abf2_dump.py` —— hex 转储一个真实 ABF2 文件（FB / PIL / ADC / STR / DATA / SIC 全字段），用于研究 Clampfit 写出来的结构；
* `third_party/heka_reader.py` —— Luke Campagnola 的 HEKA `.dat` 解析模块，vendored 单文件（原仓库无 PyPI 包，无许可证）；`install.bat` / `install.sh` 会复制到 `site-packages`。

### 引用本工具

```bibtex
@software{heka2abf,
  author       = {Wang, Wenting},
  title        = {heka2abf: HEKA PatchMaster .dat 到 ABF2 文件转换器},
  version      = {0.2.0},
  year         = {2026},
  url          = {https://github.com/ww-001/heka2abf},
  note         = {自研 ABF2 写入器（int16 + 每通道缩放），多通道交织，episodic/gap-free 自动模式，变长 sweep 通过 SIC 同步数组处理'}
}
```

### License

[MIT](LICENSE) — Copyright © 2026 Wenting Wang。完整条款见 [LICENSE](LICENSE)。