"""heka2abf graphical user interface (tkinter, no third-party dependencies).

Launch:
    python -m heka2abf.gui
or double-click run_gui.bat (Windows) / ./run_gui.sh (Linux / macOS).

Features:
  * Add a single .dat file or a whole folder (recursively finds *.dat)
  * Output location: default (sibling folder with the same name) or custom root
  * Acquisition mode: auto / episodic / gapfree; optional per-channel split
  * Background batch conversion with a live-updating log
"""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from heka2abf.convert import convert_dat  # noqa: E402

ABOUT_TEXT = """heka2abf  v0.2.1
==================

HEKA .dat -> ABF2 file converter
  Convert HEKA PatchMaster electrophysiology recordings (.dat) into
  Axon Binary Format 2 (.abf) files, directly readable by Clampfit.

Features: multi-channel interleaving, mV / pA unit normalization,
          variable-sweep auto-padding, episodic / gap-free dual mode,
          batch folder conversion.

By: WWT Lab (Wenting Wang's Lab)
Wired, We Think - connect the dots, touch the stars
"""

HELP_TEXT = """heka2abf - HEKA .dat -> ABF2 converter
=================================

Usage
-----
1) Add files: click "Add File(s)..." to pick one or more .dat files,
   or "Add Folder..." to pick a directory (recursively finds all .dat).
2) Output location:
   - "Default": a same-name folder is created next to each .dat, results go there;
   - "Custom output root": pick a root directory; results go to <root>/<name>/.
3) Pick a mode (see below) and click "Convert". The log area shows progress;
   when done, open the generated .abf in Clampfit.

Acquisition mode
----------------
- auto (default): multi-sweep series -> episodic; single-sweep / continuous -> gap-free.
- episodic: treat every series as episodic.
- gapfree: treat every series as gap-free (recommended only for continuous recordings).

Notes
-----
- The ABF2 is stored as int16 + per-channel scale factors; units are
  normalized to mV (voltage) / pA (current) by default.
- All ADC channels within one HEKA series are interleaved into a single
  ABF file. Tick "One file per channel" to split into one file per ADC.
- Variable-length sweeps (last sweep ends early) are auto-padded to the
  standard length so Clampfit displays correctly.
- Output layout: <out_dir>/<dat-stem>/<dat-stem>_g<G>_s<S>_<series-label>.abf.

FAQ
---
- "File is in use" error at export time: close the .abf in Clampfit and retry.
- GUI won't open / quits immediately: launch via run_gui.bat (Windows) or
  ./run_gui.sh (Linux / macOS) so the bundled venv Python is used.
- Sharing with a colleague: have them double-click install.bat (Windows) or
  run ./install.sh (Linux / macOS), then double-click run_gui.bat / ./run_gui.sh.
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
            "heka2abf failed to start",
            "An error occurred during startup. Please run from a console to "
            "see the full traceback,\nor send us the contents of %s." % log)
        root.destroy()
    except Exception:
        pass


class GuiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("heka2abf - HEKA .dat -> ABF2 Converter")
        self.geometry("880x580")
        self.files = []            # list of .dat paths
        self.log_q = queue.Queue()
        self._build()
        self.after(100, self._drain_log)

    # ---------- UI ----------
    def _build(self):
        pad = dict(padx=8, pady=4)

        # Top bar: title + Help/About on the right
        header = ttk.Frame(self)
        header.pack(fill="x", **pad)
        ttk.Label(header, text="heka2abf",
                  font=("Segoe UI", 13, "bold")
                  ).pack(side="left")
        ttk.Label(header, text="HEKA .dat -> ABF2 converter",
                  foreground="#555").pack(side="left", padx=10)
        ttk.Button(header, text="About", command=self._show_about).pack(side="right")
        ttk.Button(header, text="Help", command=self._show_help).pack(side="right", padx=6)

        # Input
        frm_in = ttk.LabelFrame(self, text="1. Input: HEKA .dat files")
        frm_in.pack(fill="x", **pad)
        row1 = ttk.Frame(frm_in)
        row1.pack(fill="x", padx=6, pady=4)
        ttk.Button(row1, text="Add File(s)...",
                   command=self._pick_files).pack(side="left")
        ttk.Button(row1, text="Add Folder...",
                   command=self._pick_folder).pack(side="left", padx=6)
        ttk.Button(row1, text="Clear list",
                   command=self._clear_files).pack(side="left")
        ttk.Label(row1,
                  text="(single file or whole folder; recursive scan)"
                  ).pack(side="left", padx=12)
        self.listbox = tk.Listbox(frm_in, height=6)
        self.listbox.pack(fill="x", padx=6, pady=(0, 6))

        # Output location
        frm_out = ttk.LabelFrame(self, text="2. Output location")
        frm_out.pack(fill="x", **pad)
        self.out_var = tk.StringVar(value="default")
        ttk.Radiobutton(
            frm_out,
            text="Default: create a same-name folder next to each .dat",
            variable=self.out_var, value="default"
        ).pack(anchor="w", padx=6, pady=(4, 0))
        ttk.Radiobutton(
            frm_out,
            text="Custom output root directory:",
            variable=self.out_var, value="custom"
        ).pack(anchor="w", padx=6)
        row2 = ttk.Frame(frm_out)
        row2.pack(fill="x", padx=18, pady=(0, 6))
        self.out_entry = ttk.Entry(row2)
        self.out_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(row2, text="Browse...",
                   command=self._pick_outdir).pack(side="left", padx=6)

        # Options
        frm_opt = ttk.LabelFrame(self, text="3. Options")
        frm_opt.pack(fill="x", **pad)
        row3 = ttk.Frame(frm_opt)
        row3.pack(fill="x", padx=6, pady=4)
        ttk.Label(row3, text="Acquisition mode:").pack(side="left")
        self.mode_var = tk.StringVar(value="auto")
        ttk.Combobox(row3, textvariable=self.mode_var, state="readonly",
                     values=["auto", "episodic", "gapfree"],
                     width=10).pack(side="left", padx=6)
        self.split_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            row3,
            text="One file per channel (--one-file-per-channel)",
            variable=self.split_var
        ).pack(side="left", padx=12)

        # Run
        frm_go = ttk.Frame(self)
        frm_go.pack(fill="x", **pad)
        self.go_btn = ttk.Button(frm_go, text="Convert", command=self._run)
        self.go_btn.pack(side="left")

        # Log
        frm_log = ttk.LabelFrame(self, text="Log")
        frm_log.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(frm_log, height=12, state="disabled")
        self.log.pack(fill="both", expand=True, padx=6, pady=6)

    # ---------- Input ----------
    def _pick_files(self):
        paths = filedialog.askopenfilenames(
            title="Select HEKA .dat files",
            filetypes=[("HEKA data", "*.dat"), ("All files", "*.*")])
        self._add_paths(paths)

    def _pick_folder(self):
        folder = filedialog.askdirectory(
            title="Select a folder containing .dat files")
        if not folder:
            return
        found = []
        for root, _, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(".dat"):
                    found.append(os.path.join(root, f))
        if not found:
            messagebox.showwarning(
                "Notice", "No .dat files found in this folder.")
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
        d = filedialog.askdirectory(title="Select output root directory")
        if d:
            self.out_entry.delete(0, "end")
            self.out_entry.insert(0, d)

    # ---------- Run ----------
    def _run(self):
        if not self.files:
            messagebox.showwarning(
                "Notice", "Please add .dat files first.")
            return
        custom = self.out_var.get() == "custom"
        out_root = self.out_entry.get().strip() if custom else None
        if custom and not out_root:
            messagebox.showwarning(
                "Notice", "Please select a custom output root directory.")
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
        self._log("=== Starting conversion: %d .dat file(s) ===\n" % len(files))
        for i, dat in enumerate(files, 1):
            try:
                if out_root:
                    out_dir = out_root
                else:
                    out_dir = os.path.dirname(dat)   # default: sibling folder
                self._log("[%d/%d] %s\n" % (i, len(files), os.path.basename(dat)))
                written = convert_dat(dat, out_dir=out_dir, mode=mode,
                                      one_file_per_channel=split,
                                      log=self._log)
                total_abf += len(written)
                for w in written:
                    self._log("    -> %s\n" % w)
            except Exception as e:
                self._log("    !! conversion failed: %s\n" % e)
        self._log("=== Done: %d ABF2 file(s) written ===\n" % total_abf)
        self.after(0, self._done)

    def _done(self):
        self.go_btn.state(["!disabled"])
        messagebox.showinfo(
            "Done",
            "Conversion complete. Open the generated .abf in Clampfit.")

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
        top.title("Help / Usage")
        top.geometry("640x560")
        txt = scrolledtext.ScrolledText(top, wrap="word")
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("1.0", HELP_TEXT)
        txt.configure(state="disabled")

    def _show_about(self):
        messagebox.showinfo("About heka2abf", ABOUT_TEXT)


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
            "Missing runtime dependency",
            "Missing: %s\n\n"
            "Please run install.bat (Windows) or ./install.sh "
            "(Linux / macOS) in the project folder to set up the environment, "
            "or make sure you launch via run_gui.bat / ./run_gui.sh." %
            ", ".join(missing))
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