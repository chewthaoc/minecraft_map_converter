from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.scrolled import ScrolledText

from .converter import (
    ConversionResult,
    convert_batch,
    convert_world,
    list_target_versions,
)


class App(ttk.Frame):
    def __init__(self, master: ttk.Window) -> None:
        super().__init__(master)
        self.pack(fill=BOTH, expand=YES, padx=20, pady=20)
        
        # Configuration
        self.master = master
        self.master.title("Minecraft 存档转换工具 (Pro)")
        self.master.minsize(800, 600)
        
        # Variables
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.direction_var = tk.StringVar(value="bedrock-to-java")
        self.version_var = tk.StringVar(value="最新")
        self.batch_output_var = tk.StringVar()
        self.repair_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="就绪 | Ready")
        
        # Internal State
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._result_queue: queue.Queue[ConversionResult] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._input_paths: list[str] = []

        # UI Construction
        self._setup_ui()
        
        # Logic Init
        self.direction_var.trace_add("write", lambda *_: self._refresh_versions())
        self._refresh_versions()
        self.after(100, self._poll_queues)

    def _setup_ui(self) -> None:
        # --- Header ---
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=X, pady=(0, 20))
        
        ttk.Label(
            header_frame, 
            text="MC World Converter", 
            font=("Helvetica", 24, "bold"),
            bootstyle=PRIMARY
        ).pack(side=LEFT)
        
        ttk.Label(
            header_frame, 
            text="v0.1.0", 
            bootstyle="secondary"
        ).pack(side=LEFT, padx=10, pady=(12, 0))

        # --- Main Content (Tabs) ---
        self.notebook = ttk.Notebook(self, bootstyle=PRIMARY)
        self.notebook.pack(fill=BOTH, expand=YES, pady=(0, 20))

        # Tab 1: Single Mode
        self.tab_single = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_single, text=" 单个模式 (Single) ")
        self._setup_single_tab()

        # Tab 2: Batch Mode
        self.tab_batch = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_batch, text=" 批量模式 (Batch) ")
        self._setup_batch_tab()

        # --- Settings/Log Area ---
        # Shared Log Area at bottom
        log_frame = ttk.LabelFrame(self, text="系统日志 (System Log)", bootstyle=INFO)
        log_frame.pack(fill=BOTH, expand=YES)
        
        self.log_text = ScrolledText(log_frame, height=8, autohide=True, bootstyle="round")
        self.log_text.pack(fill=BOTH, expand=YES)

        # Status Bar
        status_bar = ttk.Frame(self)
        status_bar.pack(fill=X, pady=(10, 0))
        ttk.Label(status_bar, textvariable=self.status_var, bootstyle=SECONDARY).pack(side=LEFT)
        
        # REFACTOR: Move Options Up
        # Removing Notebook for a second to inject Options below Header
        self.notebook.pack_forget()
        
        self._setup_global_options()
        self.notebook.pack(fill=BOTH, expand=YES, pady=10)

    def _setup_global_options(self) -> None:
        opt_container = ttk.LabelFrame(self, text="转换设置 (Settings)", bootstyle=PRIMARY)
        opt_container.pack(fill=X)

        # Grid layout for options
        opt_container.columnconfigure(1, weight=1)
        opt_container.columnconfigure(3, weight=1)

        # Row 0: Direction
        ttk.Label(opt_container, text="转换方向 (Direction):", bootstyle=INFO).grid(row=0, column=0, sticky=E, padx=5, pady=5)
        
        dir_frame = ttk.Frame(opt_container)
        dir_frame.grid(row=0, column=1, sticky=W, padx=5)
        
        modes = [
            ("Bedrock → Java", "bedrock-to-java"),
            ("Java → Bedrock", "java-to-bedrock"),
            ("Java → Java", "java-to-java"),
            ("Bedrock → Bedrock", "bedrock-to-bedrock")
        ]
        
        for text, val in modes:
            ttk.Radiobutton(
                dir_frame, 
                text=text, 
                value=val, 
                variable=self.direction_var,
                bootstyle="info-toolbutton"
            ).pack(side=LEFT, padx=2)

        # Row 0 (Right): Version
        ttk.Label(opt_container, text="目标版本 (Target Ver):", bootstyle=INFO).grid(row=0, column=2, sticky=E, padx=5, pady=5)
        self.version_combo = ttk.Combobox(opt_container, textvariable=self.version_var, state="readonly", width=15, bootstyle=INFO)
        self.version_combo.grid(row=0, column=3, sticky=W, padx=5)

        # Row 1: Extra Options
        ttk.Checkbutton(
            opt_container, 
            text="强制修复 (Force Repair / Re-save chunks)", 
            variable=self.repair_var,
            bootstyle="warning-round-toggle"
        ).grid(row=1, column=1, columnspan=3, sticky=W, padx=7, pady=10)

    def _setup_single_tab(self) -> None:
        # Input
        ttk.Label(self.tab_single, text="输入存档 (Input World):").pack(anchor=W)
        input_frame = ttk.Frame(self.tab_single)
        input_frame.pack(fill=X, pady=(5, 15))
        
        ttk.Entry(input_frame, textvariable=self.input_var).pack(side=LEFT, fill=X, expand=YES, padx=(0, 5))
        ttk.Button(input_frame, text="📁 浏览 (Browse)", command=self._pick_input, bootstyle=SECONDARY).pack(side=LEFT)

        # Output
        ttk.Label(self.tab_single, text="输出位置 (Output Folder):").pack(anchor=W)
        output_frame = ttk.Frame(self.tab_single)
        output_frame.pack(fill=X, pady=(5, 20))
        
        ttk.Entry(output_frame, textvariable=self.output_var).pack(side=LEFT, fill=X, expand=YES, padx=(0, 5))
        ttk.Button(output_frame, text="📁 浏览 (Browse)", command=self._pick_output, bootstyle=SECONDARY).pack(side=LEFT)

        # Action
        self.btn_convert_single = ttk.Button(
            self.tab_single, 
            text="🚀 开始转换 (Start Conversion)", 
            command=self._start_single_conversion,
            bootstyle="success-outline",
            width=30
        )
        self.btn_convert_single.pack(pady=10)

    def _setup_batch_tab(self) -> None:
        # List Area
        list_frame = ttk.Frame(self.tab_batch)
        list_frame.pack(fill=BOTH, expand=YES, pady=(0, 10))
        
        self.batch_list = tk.Listbox(list_frame, height=5, selectmode="extended", borderwidth=1, relief="solid")
        self.batch_list.pack(side=LEFT, fill=BOTH, expand=YES)
        
        toolbar = ttk.Frame(list_frame)
        toolbar.pack(side=LEFT, fill=Y, padx=5)
        
        ttk.Button(toolbar, text="➕ 添加", command=self._add_batch_input, width=8, bootstyle=SUCCESS).pack(pady=2)
        ttk.Button(toolbar, text="➖ 移除", command=self._remove_batch_input, width=8, bootstyle=DANGER).pack(pady=2)
        ttk.Button(toolbar, text="🗑️ 清空", command=self._clear_batch_inputs, width=8, bootstyle=SECONDARY).pack(pady=2)

        # Output Root
        ttk.Label(self.tab_batch, text="输出根目录 (Output Root Directory):").pack(anchor=W)
        out_frame = ttk.Frame(self.tab_batch)
        out_frame.pack(fill=X, pady=5)
        
        ttk.Entry(out_frame, textvariable=self.batch_output_var).pack(side=LEFT, fill=X, expand=YES, padx=(0, 5))
        ttk.Button(out_frame, text="📁 浏览", command=self._pick_batch_output, bootstyle=SECONDARY).pack(side=LEFT)

        # Action
        self.btn_convert_batch = ttk.Button(
            self.tab_batch, 
            text="🚀 批量转换 (Batch Convert)", 
            command=self._start_batch_conversion,
            bootstyle="success-outline",
            width=30
        )
        self.btn_convert_batch.pack(pady=15)

    def _pick_input(self) -> None:
        path = filedialog.askdirectory()
        if path: self.input_var.set(path)

    def _pick_output(self) -> None:
        path = filedialog.askdirectory()
        if path: self.output_var.set(path)

    def _pick_batch_output(self) -> None:
        path = filedialog.askdirectory()
        if path: self.batch_output_var.set(path)

    def _add_batch_input(self) -> None:
        path = filedialog.askdirectory()
        if path and path not in self._input_paths:
            self._input_paths.append(path)
            self.batch_list.insert(tk.END, path)

    def _remove_batch_input(self) -> None:
        selection = self.batch_list.curselection()
        for idx in reversed(selection):
            self.batch_list.delete(idx)
            del self._input_paths[idx]

    def _clear_batch_inputs(self) -> None:
        self.batch_list.delete(0, tk.END)
        self._input_paths.clear()

    def _start_single_conversion(self) -> None:
        self._initiate_conversion(mode="single")

    def _start_batch_conversion(self) -> None:
        self._initiate_conversion(mode="batch")

    def _initiate_conversion(self, mode: str) -> None:
        if self._worker and self._worker.is_alive():
            return

        # Common Params
        direction = self.direction_var.get()
        target_version = self._normalize_version()
        force_repair = self.repair_var.get()

        # Mode Specifics
        if mode == "single":
            inp = self.input_var.get().strip()
            out = self.output_var.get().strip()
            if not inp or not out:
                Messagebox.show_warning("请填写完整的输入和输出路径。", "输入错误")
                return
            
            out_path = Path(out)
            if out_path.exists() and any(out_path.iterdir()):
                confirm = Messagebox.show_question("输出目录非空，可能会覆盖文件。是否继续？", "确认覆盖")
                if confirm != "Yes": return
            
            args = (mode, inp, out, direction, target_version, force_repair)
            
        else: # batch
            if not self._input_paths:
                Messagebox.show_warning("列表为空，请添加存档。", "输入错误")
                return
            out = self.batch_output_var.get().strip()
            if not out:
                Messagebox.show_warning("请选择输出根目录。", "输入错误")
                return
            
            args = (mode, self._input_paths, out, direction, target_version, force_repair)

        # UI State Lock
        self._lock_ui(True)
        self.log_text.delete("1.0", tk.END)
        self.status_var.set("正在运行转换任务... | Running...")

        self._worker = threading.Thread(
            target=self._run_conversion,
            args=args,
            daemon=True
        )
        self._worker.start()

    def _lock_ui(self, locked: bool) -> None:
        state = DISABLED if locked else NORMAL
        self.btn_convert_single.configure(state=state)
        self.btn_convert_batch.configure(state=state)

    def _run_conversion(
        self,
        mode: str,
        input_path: str | list[str],
        output_path: str,
        direction: str,
        target_version: str | None,
        force_repair: bool,
    ) -> None:
        try:
            if mode == "batch":
                result = convert_batch(
                    input_paths=input_path, # type: ignore
                    output_root=output_path,
                    direction=direction,
                    target_version=target_version,
                    force_repair=force_repair,
                    log=self._log_queue.put,
                )
            else:
                result = convert_world(
                    input_path=input_path, # type: ignore
                    output_path=output_path,
                    direction=direction,
                    target_version=target_version,
                    force_repair=force_repair,
                    log=self._log_queue.put,
                )
            self._result_queue.put(result)
        except Exception as e:
            self._log_queue.put(f"CRITICAL ERROR: {e}")
            self._result_queue.put(ConversionResult(False, str(e), [] if mode=="batch" else None))

    def _poll_queues(self) -> None:
        while not self._log_queue.empty():
            msg = self._log_queue.get()
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)

        if not self._result_queue.empty():
            res = self._result_queue.get()
            self._lock_ui(False)
            
            status = "任务完成 | Finished" if res.success else "任务失败 | Failed"
            self.status_var.set(status)
            
            icon = "info" if res.success else "error"
            title = "成功" if res.success else "失败"
            Messagebox.show_info(res.message, title=title)
            
            self._worker = None

        self.after(100, self._poll_queues)

    def _normalize_version(self) -> str | None:
        value = self.version_var.get().strip()
        if not value or value == "最新":
            return None
        return value

    def _refresh_versions(self) -> None:
        target_platform = (
            "java"
            if self.direction_var.get() in {"bedrock-to-java", "java-to-java"}
            else "bedrock"
        )
        try:
            versions = list_target_versions(target_platform)
        except Exception:
            versions = []

        values = ["最新", *versions]
        self.version_combo["values"] = values
        if self.version_var.get() not in values:
            self.version_var.set("最新")
        self.version_combo.current(0)


def main() -> None:
    # Themes: cosmo, flatly, journal, darkly, superhero, solar
    app = ttk.Window(title="MC World Converter", themename="cosmo")
    App(app)
    app.mainloop()


if __name__ == "__main__":
    main()