# -*- coding: utf-8 -*-
"""
文件夹内容读取 & 按 Token 数拆分保存工具（Flet 版本）
------------------------------------------------------
依赖：
    pip install flet
    可选：pip install tiktoken   （用于更精确的 token 计算）
"""

import os
import threading
import flet as ft

# ----------------------------------------------------------------------
# Token 计算
# ----------------------------------------------------------------------
try:
    import tiktoken
    _ENC = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        if not text:
            return 0
        return len(_ENC.encode(text))

    TOKEN_METHOD = "tiktoken (cl100k_base)"
except Exception:
    _ENC = None

    def count_tokens(text: str) -> int:
        """启发式 token 估算"""
        if not text:
            return 0
        cjk_count = 0
        other_len = 0
        for ch in text:
            if ("\u4e00" <= ch <= "\u9fff") or ("\u3400" <= ch <= "\u4dbf"):
                cjk_count += 1
            else:
                other_len += 1
        return max(0, int(round(cjk_count * 1.5 + other_len / 4.0)))

    TOKEN_METHOD = "启发式估算（未检测到 tiktoken）"


# ----------------------------------------------------------------------
# 注释与过滤逻辑
# ----------------------------------------------------------------------
COMMENT_PREFIXES = {
    ".py": ("#",), ".js": ("//",), ".c": ("//",), ".cpp": ("//",),
    ".java": ("//",), ".html": ("<!--",), ".css": ("/*",), ".yaml": ("#",),
    ".sh": ("#",), ".sql": ("--",), ".ini": (";", "#")
}
DEFAULT_COMMENT_PREFIXES = ("#", "//", "--")

LIKELY_BINARY_EXT = {
    ".exe", ".dll", ".so", ".zip", ".rar", ".png", ".jpg", ".pdf", 
    ".pyc", ".db", ".sqlite", ".mp3", ".mp4"
}

def filter_lines(text: str, ext: str) -> str:
    prefixes = COMMENT_PREFIXES.get(ext.lower(), DEFAULT_COMMENT_PREFIXES)
    result = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(p) for p in prefixes):
            continue
        result.append(line)
    return "\n".join(result)

def read_file_content(path: str):
    ext = os.path.splitext(path)[1].lower()
    if ext in LIKELY_BINARY_EXT:
        return None
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb18030", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                content = f.read()
            if "\x00" in content:
                return None
            return content
        except Exception:
            continue
    return None

def chunk_text_by_tokens(text: str, max_tokens: int):
    if max_tokens <= 0:
        max_tokens = 200
    lines = text.split("\n")
    chunks, current, current_tokens = [], [], 0

    def flush_current():
        if current:
            chunks.append("\n".join(current))

    for line in lines:
        line_tokens = count_tokens(line)
        if line_tokens > max_tokens:
            flush_current()
            current.clear()
            current_tokens = 0
            approx = max(1, int(len(line) * max_tokens / max(1, line_tokens)))
            for i in range(0, len(line), approx):
                chunks.append(line[i:i + approx])
            continue
        if current_tokens + line_tokens > max_tokens and current:
            flush_current()
            current, current_tokens = [], 0
        current.append(line)
        current_tokens += line_tokens

    flush_current()
    return chunks if chunks else [text]

SEP_LINE = "=" * 60


# ----------------------------------------------------------------------
# 主应用逻辑
# ----------------------------------------------------------------------
def main(page: ft.Page):
    page.title = "文件夹内容读取 · 按 Token 拆分工具（Flet版）"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.padding = 20
    page.window_width = 850
    page.window_height = 700

    selected_folder = ft.Ref[ft.TextField]()
    output_folder = ft.Ref[ft.TextField]()
    token_limit_input = ft.Ref[ft.TextField]()
    prefix_input = ft.Ref[ft.TextField]()
    recursive_switch = ft.Ref[ft.Checkbox]()
    filter_switch = ft.Ref[ft.Checkbox]()
    log_view = ft.Ref[ft.ListView]()
    start_btn = ft.Ref[ft.ElevatedButton]()

    def log(msg: str):
        log_view.current.controls.append(ft.Text(msg, size=12, font_family="Consolas"))
        page.update()

    # 文件夹选择对话框回调
    def on_source_folder_result(e: ft.FilePickerResultEvent):
        if e.path:
            selected_folder.current.value = e.path
            page.update()

    def on_output_folder_result(e: ft.FilePickerResultEvent):
        if e.path:
            output_folder.current.value = e.path
            page.update()

    source_picker = ft.FilePicker(on_result=on_source_folder_result)
    out_picker = ft.FilePicker(on_result=on_output_folder_result)
    page.overlay.extend([source_picker, out_picker])

    # 后台打包任务
    def run_processing():
        folder = selected_folder.current.value
        out_dir = output_folder.current.value
        
        if not folder or not os.path.isdir(folder):
            log("❌ 错误：请选择有效的源文件夹！")
            start_btn.current.disabled = False
            page.update()
            return
            
        if not out_dir or not os.path.isdir(out_dir):
            log("❌ 错误：请选择有效的输出文件夹！")
            start_btn.current.disabled = False
            page.update()
            return

        try:
            token_limit = int(token_limit_input.current.value.strip())
        except ValueError:
            log("❌ 错误：Token 上限必须是正整数！")
            start_btn.current.disabled = False
            page.update()
            return

        recursive = recursive_switch.current.value
        do_filter = filter_switch.current.value
        prefix = prefix_input.current.value.strip() or "output"

        log("=" * 40)
        log(f"🚀 开始处理: {folder} | 上限: {token_limit} tokens | 递归: {recursive}")

        try:
            files = []
            if recursive:
                for root, _, names in os.walk(folder):
                    for name in names:
                        files.append(os.path.join(root, name))
            else:
                for name in sorted(os.listdir(folder)):
                    full = os.path.join(folder, name)
                    if os.path.isfile(full):
                        files.append(full)
            
            files = sorted(files)
            log(f"📁 共发现 {len(files)} 个文件，开始解析...")

            current_parts = []
            current_tokens = 0
            file_index = 1
            written_count = 0
            skipped = 0
            processed = 0

            def flush():
                nonlocal current_parts, current_tokens, file_index, written_count
                if not current_parts:
                    return
                out_name = f"{prefix}_{file_index:03d}.txt"
                out_path = os.path.join(out_dir, out_name)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(("\n\n" + SEP_LINE + "\n\n").join(current_parts))
                written_count += 1
                log(f"💾 已保存：{out_name} (约 {current_tokens} tokens)")
                file_index += 1
                current_parts = []
                current_tokens = 0

            for filepath in files:
                content = read_file_content(filepath)
                if content is None:
                    skipped += 1
                    continue
                if do_filter:
                    content = filter_lines(content, os.path.splitext(filepath)[1])
                if not content.strip():
                    skipped += 1
                    continue

                rel = os.path.relpath(filepath, folder)
                processed += 1

                header = f"{SEP_LINE}\n文件: {rel}\n{SEP_LINE}"
                block_full = header + "\n" + content
                block_tokens = count_tokens(block_full)

                if block_tokens > token_limit:
                    header_tokens = count_tokens(header)
                    budget = max(50, token_limit - header_tokens - 20)
                    sub_chunks = chunk_text_by_tokens(content, budget)
                    total_parts = len(sub_chunks)
                    for i, sub in enumerate(sub_chunks, 1):
                        sub_header = f"{SEP_LINE}\n文件: {rel} (分段 {i}/{total_parts})\n{SEP_LINE}"
                        sub_block = sub_header + "\n" + sub
                        sub_tokens = count_tokens(sub_block)
                        if current_tokens + sub_tokens > token_limit and current_parts:
                            flush()
                        current_parts.append(sub_block)
                        current_tokens += sub_tokens
                else:
                    if current_tokens + block_tokens > token_limit and current_parts:
                        flush()
                    current_parts.append(block_full)
                    current_tokens += block_tokens

            flush()
            log("-" * 40)
            log(f"✅ 完成！成功处理 {processed} 个文件，跳过 {skipped} 个，生成 {written_count} 个 txt。")
            log(f"📂 输出目录: {out_dir}")
            log("=" * 40)
        except Exception as e:
            log(f"❌ 发生异常: {e}")
        finally:
            start_btn.current.disabled = False
            page.update()

    def start_click(e):
        start_btn.current.disabled = True
        page.update()
        threading.Thread(target=run_processing, daemon=True).start()

    # ---------------- UI 布局 ----------------
    page.add(
        ft.Text("📂 文件夹内容读取 & 按 Token 拆分工具", size=18, weight=ft.FontWeight.BOLD),
        
        # 1. 选择源文件夹
        ft.Row([
            ft.TextField(ref=selected_folder, label="源文件夹路径", read_only=True, expand=True),
            ft.ElevatedButton("选择源文件夹", icon=ft.icons.FOLDER_OPEN, on_click=lambda _: source_picker.get_directory_path())
        ]),

        # 2. 选择输出文件夹
        ft.Row([
            ft.TextField(ref=output_folder, label="输出保存文件夹路径", read_only=True, expand=True),
            ft.ElevatedButton("选择输出目录", icon=ft.icons.SAVE, on_click=lambda _: out_picker.get_directory_path())
        ]),

        # 3. 参数配置区
        ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.TextField(ref=token_limit_input, label="单个txt的Token上限", value="2000", width=180),
                    ft.Text(f"当前方法: {TOKEN_METHOD}", size=11, color=ft.colors.GREY_700),
                ], alignment=ft.MainAxisAlignment.START),
                
                ft.Row([
                    ft.TextField(ref=prefix_input, label="输出文件名前缀", value="output", width=180),
                ]),

                ft.Checkbox(ref=recursive_switch, label="递归读取所有子文件夹", value=True),
                ft.Checkbox(ref=filter_switch, label="自动过滤常见注释行与空行", value=False),
            ]),
            padding=10,
            border=ft.border.all(1, ft.colors.GREY_400),
            border_radius=8
        ),

        # 4. 操作按钮
        ft.ElevatedButton(
            ref=start_btn,
            text="开始处理并打包 🚀", 
            color=ft.colors.WHITE, 
            bgcolor=ft.colors.BLUE_700,
            on_click=start_click
        ),

        ft.Divider(),

        # 5. 日志输出区
        ft.Text("运行日志:", weight=ft.FontWeight.BOLD),
        ft.Container(
            content=ft.ListView(ref=log_view, expand=True, spacing=3, auto_scroll=True),
            bgcolor=ft.colors.BLACK,
            padding=10,
            border_radius=8,
            expand=True
        )
    )

if __name__ == "__main__":
    ft.app(target=main)
