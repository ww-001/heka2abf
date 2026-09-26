# heka2abf

把 HEKA PatchMaster 的 `.dat` 文件转换为 **ABF2**（Axon Binary Format 2）文件的
Python 命令行工具，转换结果可由 Clampfit / pyABF 直接打开。

## 特性

* 读取：基于 [campagnola/heka_reader](https://github.com/campagnola/heka_reader)
  解析 HEKA .dat 的树形结构（Group → Series → Sweep → Trace）。
* 写入：**自研的 ABF2 写入器**（不依赖任何 ABF 写入库 —— pyABF 只支持写 ABF1）。
  按真实 Clampfit 文件的头部布局实现：FB 文件段、PIL/ADC/STR/DATA/SIC 分节、
  SSCH 字符串区；存储为 **int16 + 每通道缩放系数**（与 pClamp 原生文件一致），
  数值已按 HEKA 的 DataScaler/ZeroData 换算成物理单位。
* 单位：默认把电压 **V → mV**、电流 **A → pA**（信号值同步换算），Clampfit 中
  直接显示 mV / pA。
* 组织：输出按源文件分文件夹 —— `<out>/<dat文件主名>/<...>.abf`，同一 .dat 的
  结果都在同名文件夹里。
* 多通道：同一 HEKA Series 内各 ADC 通道交织保存在一个 ABF 文件（通道 = trace 的
  ADC 通道号；sweep = HEKA sweep）；也可用 `--one-file-per-channel` 按通道拆分文件。
* 采集模式：多 sweep 系列 → **episodic（mode 5）**；单 sweep 系列/连续记录 →
  **gap-free（mode 3）**——与真实 Clampfit 文件一致。
* **变长 sweep**：HEKA 常见的"最后一个 sweep 提前结束"（例如记录被中断）由 ABF2
  的 SIC 同步数组原生支持，Clampfit / pyABF 都能正确逐 sweep 读取。
* **起始时间**：每个 sweep 的起始时刻（HEKA `SweepRecord.Time`）写入 SIC，转换后
  Clampfit 中 sweep 的绝对时间与 PatchMaster 一致。

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\pip install numpy pyabf
# heka_reader 没有 PyPI 包（且无 setup.py），手动放入 site-packages：
#   从 https://github.com/campagnola/heka_reader/archive/refs/heads/master.zip
#   解压后把 heka_reader.py 复制到 .\.venv\Lib\site-packages\
```

## 使用说明

### 图形界面（推荐）

```powershell
run_gui.bat        # 或 python heka2abf/gui.py
```

1. **添加文件**：点"添加文件…"选单个 .dat，或"添加文件夹…"选整个目录（自动递归找出所有 .dat）；
2. **导出位置**：默认在每个 .dat 同级目录下新建"<dat文件名>"文件夹存放结果；
   也可以选择"自定义导出根目录"；
3. 按需调整采集模式（auto / episodic / gapfree）、是否按通道拆分；
4. 点**导出**，日志区实时显示进度，完成后用 Clampfit 打开生成的 .abf。

### 命令行

```powershell
# 查看 .dat 结构（不转换）
.\.venv\Scripts\python -m heka2abf.cli data.dat --inspect

# 转换（结果在 out/<dat文件名>/ 下）
.\.venv\Scripts\python -m heka2abf.cli data.dat -o out/

# 按通道拆分（一个通道一个文件）
.\.venv\Scripts\python -m heka2abf.cli data.dat -o out/ --one-file-per-channel

# 强制模式（默认 auto：单 sweep 系列→gap-free，多 sweep 系列→episodic）
.\.venv\Scripts\python -m heka2abf.cli data.dat -o out/ --mode episodic
.\.venv\Scripts\python -m heka2abf.cli data.dat -o out/ --mode gapfree
```

## 发给同事使用

软件目录已自带一键安装脚本，同事用法：

1. 把整个 `heka2abf` 文件夹复制给同事（包含 `install.bat`、`run_gui.bat`、
   `third_party\heka_reader.py` 等）；
2. 同事电脑需装有 **Python 3.9+**（python.org 安装时勾选 "Add Python to PATH"）；
3. 双击 `install.bat`：自动创建独立的 `.venv` 环境，安装 numpy 并复制 HEKA
   解析库（一次即可）；
4. 之后双击 `run_gui.bat` 打开图形界面，无需再配置任何东西。

注意：

* 转换功能只需要 **numpy + heka_reader**（install.bat 自动装好）；pyabf 仅用于
  自带测试，不需要安装；
* 一定要用 `run_gui.bat` 启动（它使用自带环境的 Python，且无控制台窗口）；
  不要直接 `python heka2abf/gui.py` 用系统 Python 跑（会缺依赖）；
* 若同事电脑不方便装 Python，下一步可以打包成免安装 exe（PyInstaller），
  或者把装好环境的整个文件夹连同 `.venv` 一起拷过去直接用。

### 常见问题

* **某个系列最后的 sweep 提前结束（记录中断）**：转换时会自动把短 sweep 尾端补到
  标准长度（保持最后一值），保证 Clampfit 正常显示；
* **单 sweep 的刺激实验文件希望按 episodic 显示**：加 `--mode episodic`；
* **单位**：默认电压 V→mV、电流 A→pA（数值同步换算）；如需保留原始单位，改
  `heka2abf/convert.py` 中 `_normalize_unit()` 即可。

## 结构映射

| HEKA | ABF2 |
|---|---|
| Series | 一个文件 |
| ADC 通道（trace） | ABF 通道（交织存储） |
| Sweep | ABF sweep（episodic 模式，mode 5） |
| XInterval（秒） | PIL.fADCSequenceInterval（微秒） |
| YUnit / trace Label | ADC 通道单位 / 名称（STR 字符串索引） |

## 验证

`tests/test_abf2writer.py` 用 pyABF 回读写入结果：
* 合成数据往返：通道数 / sweep 数 / 采样率 / 名称单位 / 波形完全一致；
* 用真实 Clampfit ABF2（`reference/model_vc_ramp.abf`）的 50 个 sweep 数据重写后
  回读，与原物理值**逐点零误差**；
* `tests/test_real_dat.py`：对真实 HEKA .dat（4 个文件、含变长 sweep、双通道
  IV 曲线、30+ sweep 的 CC 注入、膜测试等）做"HEKA 原始值 → 写入 → pyABF 回读"
  全量逐点对比，**最大绝对误差 = 0**。

## 已知限制

* heka_reader 直接读取存储样本数组，PatchMaster 开启可选有损压缩（min/max 成对
  存储）的文件会原样读出压缩值；标准膜片钳记录通常不压缩。
* SSCH 字符串头中两个偏移字段（条目内第 12/16 字节）按真实文件的规律生成
  （44+首串长度 / 44+总长）；pyABF 完全不读它们。若 Clampfit 的字符串窗显示异常
  属于这类装饰性字段问题，不影响数据读取。

## 测试与参考数据

* `tests/test_abf2writer.py`：合成数据 + `reference/` 里真实 Clampfit ABF2
  文件的读取回放验证，无需真实 HEKA 数据；
* `tests/test_real_dat.py`：用自己的真实 HEKA .dat 做端到端逐点对比：
  `python tests/test_real_dat.py <你的.dat> …`（可传多个文件）；
* `reference/*.abf` 为 pyABF 仓库的测试数据（
  [swharden/pyABF](https://github.com/swharden/pyABF)，MIT 许可），仅作格式对照。

## 参考

* ABF2 结构依据 pyABF 源码（[swharden/pyABF](https://github.com/swharden/pyABF)）
  与真实 Clampfit 文件（`reference/`, 可用 `tools/abf2_dump.py` 解剖）。
* 同类项目 [junzhanj/HEKADatConverter](https://github.com/junzhanj/HEKADatConverter)
  （写 ABF1，本工具在数据保真与 ABF2 上更强）。