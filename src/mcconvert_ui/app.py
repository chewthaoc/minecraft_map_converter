from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .converter import (
    ConversionResult,
    convert_batch,
    convert_world,
    list_target_versions,
)


class App(ttk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master)
        self.master = master
        self.master.title("Minecraft 存档转换工具")
        self.master.minsize(760, 520)

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.direction_var = tk.StringVar(value="bedrock-to-java")
        self.version_var = tk.StringVar(value="最新")
        self.batch_var = tk.BooleanVar(value=False)
        self.repair_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="就绪")

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._result_queue: queue.Queue[ConversionResult] = queue.Queue()
        self._worker: threading.Thread | None = None

        self._build_ui()
        self.direction_var.trace_add("write", lambda *_: self._refresh_versions())
        self._refresh_versions()
        self.after(100, self._poll_queues)

    def _build_ui(self) -> None:
        padding = {"padx": 12, "pady": 8}

        self.single_input_frame = ttk.LabelFrame(self, text="输入存档")
        self.single_input_frame.grid(row=0, column=0, sticky="ew", **padding)
        self.single_input_frame.columnconfigure(1, weight=1)

        ttk.Label(self.single_input_frame, text="存档文件夹").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Entry(self.single_input_frame, textvariable=self.input_var).grid(
            row=0, column=1, sticky="ew", padx=(8, 8)
        )
        ttk.Button(
            self.single_input_frame, text="浏览...", command=self._pick_input
        ).grid(
            row=0, column=2, sticky="e"
        )

        self.batch_input_frame = ttk.LabelFrame(self, text="批量输入")
        self.batch_input_frame.grid(row=0, column=0, sticky="ew", **padding)
        self.batch_input_frame.columnconfigure(0, weight=1)

        self.input_listbox = tk.Listbox(
            self.batch_input_frame, height=5, selectmode="extended"
        )
        self.input_listbox.grid(row=0, column=0, sticky="ew")

        batch_button_frame = ttk.Frame(self.batch_input_frame)
        batch_button_frame.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        ttk.Button(batch_button_frame, text="添加...", command=self._add_input).grid(
            row=0, column=0, sticky="ew", pady=(0, 4)
        )
        ttk.Button(
            batch_button_frame, text="移除选中", command=self._remove_selected
        ).grid(row=1, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(batch_button_frame, text="清空", command=self._clear_inputs).grid(
            row=2, column=0, sticky="ew"
        )

        self.batch_input_frame.grid_remove()

        output_frame = ttk.LabelFrame(self, text="输出存档")
        output_frame.grid(row=1, column=0, sticky="ew", **padding)
        output_frame.columnconfigure(1, weight=1)

        self.output_label = ttk.Label(output_frame, text="目标文件夹")
        self.output_label.grid(row=0, column=0, sticky="w")
        ttk.Entry(output_frame, textvariable=self.output_var).grid(
            row=0, column=1, sticky="ew", padx=(8, 8)
        )
        ttk.Button(output_frame, text="浏览...", command=self._pick_output).grid(
            row=0, column=2, sticky="e"
        )

        option_frame = ttk.LabelFrame(self, text="转换方向")
        option_frame.grid(row=2, column=0, sticky="ew", **padding)
        option_frame.columnconfigure(1, weight=1)

        ttk.Radiobutton(
            option_frame,
            text="Bedrock → Java",
            value="bedrock-to-java",
            variable=self.direction_var,
        ).grid(row=0, column=0, sticky="w", padx=(0, 24))
        ttk.Radiobutton(
            option_frame,
            text="Java → Bedrock",
            value="java-to-bedrock",
            variable=self.direction_var,
        ).grid(row=0, column=1, sticky="w")

        ttk.Radiobutton(
            option_frame,
            text="Java → Java",
            value="java-to-java",
            variable=self.direction_var,
        ).grid(row=1, column=0, sticky="w", padx=(0, 24))
        ttk.Radiobutton(
            option_frame,
            text="Bedrock → Bedrock",
            value="bedrock-to-bedrock",
            variable=self.direction_var,
        ).grid(row=1, column=1, sticky="w")

        ttk.Label(option_frame, text="目标版本").grid(row=2, column=0, sticky="w")
        self.version_combo = ttk.Combobox(
            option_frame, textvariable=self.version_var, state="readonly"
        )
        self.version_combo.grid(row=2, column=1, sticky="w")

        ttk.Checkbutton(
            option_frame,
            text="批量处理",
            variable=self.batch_var,
            command=self._toggle_batch,
        ).grid(row=3, column=0, sticky="w")
        ttk.Checkbutton(
            option_frame,
            text="强制修复(重新保存)",
            variable=self.repair_var,
        ).grid(row=3, column=1, sticky="w")

        action_frame = ttk.Frame(self)
        action_frame.grid(row=3, column=0, sticky="ew", **padding)
        action_frame.columnconfigure(0, weight=1)

        self.convert_button = ttk.Button(
            action_frame, text="开始转换", command=self._start_conversion
        )
        self.convert_button.grid(row=0, column=0, sticky="w")

        ttk.Label(action_frame, textvariable=self.status_var).grid(
            row=0, column=1, sticky="e"
        )

        log_frame = ttk.LabelFrame(self, text="日志")
        log_frame.grid(row=4, column=0, sticky="nsew", **padding)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=14, wrap="word")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.configure(state="disabled")

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text["yscrollcommand"] = scrollbar.set

        self.rowconfigure(4, weight=1)
        self.columnconfigure(0, weight=1)

    def _pick_input(self) -> None:
        folder = filedialog.askdirectory(title="选择输入存档文件夹")
        if folder:
            self.input_var.set(folder)

    def _pick_output(self) -> None:
        folder = filedialog.askdirectory(title="选择输出存档所在文件夹")
        if folder:
            self.output_var.set(folder)

    def _start_conversion(self) -> None:
        if self._worker and self._worker.is_alive():
            return

        output_path = self.output_var.get().strip()
        if not output_path:
            messagebox.showwarning("提示", "请输入输出路径。")
            return

        is_batch = self.batch_var.get()
        if is_batch:
            inputs = list(self.input_listbox.get(0, "end"))
            if not inputs:
                messagebox.showwarning("提示", "请添加至少一个输入存档。")
                return
        else:
            input_path = self.input_var.get().strip()
            if not input_path:
                messagebox.showwarning("提示", "请输入输入路径。")
                return

        if not is_batch:
            output_dir = Path(output_path)
            if output_dir.exists() and any(output_dir.iterdir()):
                messagebox.showwarning("提示", "输出路径非空，请选择空目录。")
                return

        self._clear_log()
        self.status_var.set("转换中...")
        self.convert_button.configure(state="disabled")

        mode = "batch" if is_batch else "single"
        target_version = self._normalize_version()
        force_repair = self.repair_var.get()
        direction = self.direction_var.get()

        if mode == "batch":
            args = (mode, inputs, output_path, direction, target_version, force_repair)
        else:
            args = (mode, input_path, output_path, direction, target_version, force_repair)

        self._worker = threading.Thread(
            target=self._run_conversion,
            args=args,
            daemon=True,
        )
        self._worker.start()

    def _run_conversion(
        self,
        mode: str,
        input_path: str | list[str],
        output_path: str,
        direction: str,
        target_version: str | None,
        force_repair: bool,
    ) -> None:
        if mode == "batch":
            result = convert_batch(
                input_paths=input_path,
                output_root=output_path,
                direction=direction,
                target_version=target_version,
                force_repair=force_repair,
                log=self._log_queue.put,
            )
        else:
            result = convert_world(
                input_path=input_path,
                output_path=output_path,
                direction=direction,
                target_version=target_version,
                force_repair=force_repair,
                log=self._log_queue.put,
            )
        self._result_queue.put(result)

    def _toggle_batch(self) -> None:
        if self.batch_var.get():
            self.single_input_frame.grid_remove()
            self.batch_input_frame.grid()
            self.output_label.configure(text="输出根目录")
        else:
            self.batch_input_frame.grid_remove()
            self.single_input_frame.grid()
            self.output_label.configure(text="目标文件夹")

    def _add_input(self) -> None:
        folder = filedialog.askdirectory(title="选择输入存档文件夹")
        if folder and folder not in self.input_listbox.get(0, "end"):
            self.input_listbox.insert("end", folder)

    def _remove_selected(self) -> None:
        selected = list(self.input_listbox.curselection())
        for index in reversed(selected):
            self.input_listbox.delete(index)

    def _clear_inputs(self) -> None:
        self.input_listbox.delete(0, "end")

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

    def _poll_queues(self) -> None:
        while True:
            try:
                message = self._log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(message)

        try:
            result = self._result_queue.get_nowait()
        except queue.Empty:
            result = None

        if result is not None:
            self._handle_result(result)

        self.after(100, self._poll_queues)

    def _handle_result(self, result: ConversionResult) -> None:
        self.convert_button.configure(state="normal")
        if result.success:
            self.status_var.set("完成")
            messagebox.showinfo("完成", result.message)
        else:
            self.status_var.set("失败")
            message = result.message
            if result.details:
                message += f"\n\n详细信息:\n{result.details}"
            messagebox.showerror("失败", message)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


def main() -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    elif "clam" in style.theme_names():
        style.theme_use("clam")
    app = App(root)
    app.pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()
