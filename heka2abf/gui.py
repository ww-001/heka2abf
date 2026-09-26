"""heka2abf 图形界面（tkinter，无第三方依赖）。

启动方式：
    python heka2abf/gui.py
或双击 run_gui.bat

功能：
  * 添加单个 .dat 文件或整个文件夹（递归搜索 *.dat）
  * 导出位置：默认在 .dat 所在目录生成同名文件夹，或指定导出根目录
  * 采集模式：auto / episodic / gapfree；可按通道拆分文件
  * 后台执行批量转换，日志实时显示
"""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from heka2abf.convert import convert_dat  # noqa: E402

ABOUT_TEXT = """heka2abf  v0.2.0
==================

HEKA .dat → ABF2 文件转换器
  把 HEKA PatchMaster 电生理记录（.dat）转换成 Axon Binary Format 2
  （ABF2），生成的 .abf 文件可直接用 Clampfit 打开分析。

功能：多通道交织、mV / pA 单位换算、变长 sweep 自动补全、
      episodic / gap-free 双模式、批量文件夹转换。

出品：WWT Lab
Wired， We Think · 星河为络，思接苍穹
"""

HELP_TEXT = """heka2abf — HEKA .dat → ABF2 转换器
==================================

使用方法
--------
1) 添加文件：点“添加文件…”选单个 .dat，或点“添加文件夹…”选整个目录（自动递归找出所有 .dat）。
2) 导出位置：
   · “默认”：每个 .dat 的同级目录下自动生成“<文件名>”文件夹，结果放里面；
   · “自定义根目录”：指定一个根目录，结果放 <根目录>/<文件名>/。
3) 选好模式（见下）后点“导出”，日志区会显示进度；完成后可用 Clampfit 打开生成的 .abf。

采集模式
--------
· auto（默认）：多 sweep 系列 → episodic；单 sweep 系列/连续记录 → gap-free；
· episodic：全部按 episodic 处理；
· gapfree：全部按 gap-free 处理（建议仅用于连续记录）。

说明
----
· 生成的 ABF2 用 int16 + 缩放系数存储，单位默认换算为 mV（电压）/ pA（电流）；
· 同一 HEKA Series 的多通道会交织保存在一个文件里；勾选“每通道单独文件”
  可拆分为每个 ADC 通道一个文件；
· 变长 sweep（最后一个 sweep 提前结束）会自动补足到标准长度，保证 Clampfit 正常显示；
· 数据文件保存在 <输出>/<dat文件名>/ 下，命名：<dat名>_g<组>_s<系列>_<系列名>.abf。

常见问题
--------
· 导出时报“文件被占用”：请先关闭 Clampfit 中打开的 .abf 再重试；
· 打不开/闪退：确保是用 run_gui.bat 启动（使用自带环境的 Python）;
· 需要给同事使用：同事双击 install.bat 自动安装环境，再双击 run_gui.bat。
"""


def _fatal_errors_to_log(exc_info_log):
    """When launched without a console, write startup errors to a log file."""
    import traceback
    here = os.path.dirname(os.path.abspath(__file__))
    log = os.path.join(here, "gui_error.log")
    try:
        with open(log, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
    except Exception:
        pass
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "heka2abf 启动失败",
            "程序启动时出错，请开启控制台运行查看详细错误，\n"
            "或把 %s 的内容发给我们。" % log)
        root.destroy()
    except Exception:
        pass


class GuiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("heka2abf — HEKA .dat → ABF2 转换器")
        self.geometry("780x560")
        self.files = []            # list of .dat paths
        self.log_q = queue.Queue()
        self._build()
        self.after(100, self._drain_log)

    # ---------- UI ----------
    def _build(self):
        pad = dict(padx=8, pady=4)

        # 顶部栏：标题 + 右上角帮助/关于
        header = ttk.Frame(self)
        header.pack(fill="x", **pad)
        ttk.Label(header, text="heka2abf", font=("Microsoft YaHei UI", 13, "bold")
                  ).pack(side="left")
        ttk.Label(header, text="HEKA .dat → ABF2 转换器",
                  foreground="#555").pack(side="left", padx=10)
        ttk.Button(header, text="关于", command=self._show_about).pack(side="right")
        ttk.Button(header, text="使用说明", command=self._show_help).pack(side="right", padx=6)

        # 输入
        frm_in = ttk.LabelFrame(self, text="1. 输入：HEKA .dat 文件")
        frm_in.pack(fill="x", **pad)
        row1 = ttk.Frame(frm_in)
        row1.pack(fill="x", padx=6, pady=4)
        ttk.Button(row1, text="添加文件…", command=self._pick_files).pack(side="left")
        ttk.Button(row1, text="添加文件夹…", command=self._pick_folder).pack(side="left", padx=6)
        ttk.Button(row1, text="清空列表", command=self._clear_files).pack(side="left")
        ttk.Label(row1, text="（支持单个文件或整个文件夹，自动递归）").pack(side="left", padx=12)
        self.listbox = tk.Listbox(frm_in, height=6)
        self.listbox.pack(fill="x", padx=6, pady=(0, 6))

        # 导出位置
        frm_out = ttk.LabelFrame(self, text="2. 导出位置")
        frm_out.pack(fill="x", **pad)
        self.out_var = tk.StringVar(value="default")
        ttk.Radiobutton(frm_out, text="默认：在每个 .dat 同级目录下新建同名文件夹",
                        variable=self.out_var, value="default").pack(anchor="w", padx=6, pady=(4, 0))
        ttk.Radiobutton(frm_out, text="自定义导出根目录：",
                        variable=self.out_var, value="custom").pack(anchor="w", padx=6)
        row2 = ttk.Frame(frm_out)
        row2.pack(fill="x", padx=18, pady=(0, 6))
        self.out_entry = ttk.Entry(row2)
        self.out_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(row2, text="浏览…", command=self._pick_outdir).pack(side="left", padx=6)

        # 选项
        frm_opt = ttk.LabelFrame(self, text="3. 选项")
        frm_opt.pack(fill="x", **pad)
        row3 = ttk.Frame(frm_opt)
        row3.pack(fill="x", padx=6, pady=4)
        ttk.Label(row3, text="采集模式:").pack(side="left")
        self.mode_var = tk.StringVar(value="auto")
        ttk.Combobox(row3, textvariable=self.mode_var, state="readonly",
                     values=["auto", "episodic", "gapfree"],
                     width=10).pack(side="left", padx=6)
        self.split_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="每通道单独文件（--one-file-per-channel）",
                        variable=self.split_var).pack(side="left", padx=12)

        # 导出
        frm_go = ttk.Frame(self)
        frm_go.pack(fill="x", **pad)
        self.go_btn = ttk.Button(frm_go, text="导出", command=self._run)
        self.go_btn.pack(side="left")

        # 日志
        frm_log = ttk.LabelFrame(self, text="日志")
        frm_log.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(frm_log, height=12, state="disabled")
        self.log.pack(fill="both", expand=True, padx=6, pady=6)

    # ---------- 输入 ----------
    def _pick_files(self):
        paths = filedialog.askopenfilenames(
            title="选择 HEKA .dat 文件",
            filetypes=[("HEKA data", "*.dat"), ("所有文件", "*.*")])
        self._add_paths(paths)

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="选择包含 .dat 的文件夹")
        if not folder:
            return
        found = []
        for root, _, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(".dat"):
                    found.append(os.path.join(root, f))
        if not found:
            messagebox.showwarning("提示", "该文件夹下没有找到 .dat 文件")
            return
        self._add_paths(found)

    def _add_paths(self, paths):
        for p in paths:
            p = os.path.abspath(p)
            if p not in self.files:
                self.files.append(p)
        self._refresh_list()

    def _clear_files(self):
        self.files = []
        self._refresh_list()

    def _refresh_list(self):
        self.listbox.delete(0, "end")
        for p in self.files:
            self.listbox.insert("end", p)

    def _pick_outdir(self):
        d = filedialog.askdirectory(title="选择导出根目录")
        if d:
            self.out_entry.delete(0, "end")
            self.out_entry.insert(0, d)

    # ---------- 执行 ----------
    def _run(self):
        if not self.files:
            messagebox.showwarning("提示", "请先添加 .dat 文件")
            return
        custom = self.out_var.get() == "custom"
        out_root = self.out_entry.get().strip() if custom else None
        if custom and not out_root:
            messagebox.showwarning("提示", "请选择自定义导出根目录")
            return
        self.go_btn.state(["disabled"])
        t = threading.Thread(target=self._worker, args=(list(self.files),
                                                        out_root,
                                                        self.mode_var.get(),
                                                        self.split_var.get()),
                             daemon=True)
        t.start()

    def _worker(self, files, out_root, mode, split):
        total_abf = 0
        self._log("=== 开始转换：%d 个 .dat 文件 ===\n" % len(files))
        for i, dat in enumerate(files, 1):
            try:
                if out_root:
                    out_dir = out_root
                else:
                    out_dir = os.path.dirname(dat)   # 默认：同级目录下建同名文件夹
                self._log("[%d/%d] %s\n" % (i, len(files), os.path.basename(dat)))
                written = convert_dat(dat, out_dir=out_dir, mode=mode,
                                      one_file_per_channel=split,
                                      log=self._log)
                total_abf += len(written)
                for w in written:
                    self._log("    -> %s\n" % w)
            except Exception as e:
                self._log("    !! 转换失败：%s\n" % e)
        self._log("=== 完成：共写入 %d 个 ABF2 文件 ===\n" % total_abf)
        self.after(0, self._done)

    def _done(self):
        self.go_btn.state(["!disabled"])
        messagebox.showinfo("完成", "转换完成，共写入 ABF2 文件。可用 Clampfit 打开查看。")

    def _log(self, text):
        self.log_q.put(text)

    def _drain_log(self):
        try:
            while True:
                line = self.log_q.get_nowait()
                self.log.configure(state="normal")
                self.log.insert("end", line)
                self.log.see("end")
                self.log.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._drain_log)

    def _show_help(self):
        top = tk.Toplevel(self)
        top.title("帮助 / 使用说明")
        top.geometry("640x560")
        txt = scrolledtext.ScrolledText(top, wrap="word")
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("1.0", HELP_TEXT)
        txt.configure(state="disabled")

    def _show_about(self):
        messagebox.showinfo("关于 heka2abf", ABOUT_TEXT)


def _check_deps():
    """Verify the conversion dependencies are importable; else guidance."""
    missing = []
    try:
        import numpy  # noqa: F401
    except ImportError:
        missing.append("numpy")
    try:
        import heka_reader  # noqa: F401
    except ImportError:
        missing.append("heka_reader")
    if missing:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "缺少运行依赖",
            "缺少：%s\n\n请在软件目录运行 install.bat 自动安装环境，\n"
            "或确认使用的是软件自带环境的 run_gui.bat 启动。" % ", ".join(missing))
        root.destroy()
        return False
    return True


def main():
    if not _check_deps():
        return 1
    try:
        GuiApp().mainloop()
        return 0
    except Exception:
        _fatal_errors_to_log(sys.exc_info())
        return 1


if __name__ == "__main__":
    sys.exit(main())