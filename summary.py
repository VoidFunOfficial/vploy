#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
from dataclasses import dataclass, asdict
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

# 默认统计的扩展名（你可以按需增删）
DEFAULT_EXTS = [
    ".py", ".vue", ".js", ".ts", ".tsx", ".jsx",
    ".json", ".yml", ".yaml",
    ".html", ".css", ".scss", ".less",
    ".md", ".txt",
]

# 默认忽略的目录（常见前端/构建产物）
DEFAULT_IGNORES = {
    ".git", ".svn", ".hg",
    "node_modules", "dist", "build", "out",
    ".next", ".nuxt",
    ".venv", "venv", "__pycache__",
    ".idea", ".vscode",
}

# 各类文件的单行注释前缀（启发式）
LINE_COMMENT_PREFIX = {
    ".py": ["#"],
    ".js": ["//"],
    ".ts": ["//"],
    ".jsx": ["//"],
    ".tsx": ["//"],
    ".vue": ["//"],   # <script>里通常是 //
    ".css": [],       # css 通常用 /* */ 不是单行前缀
    ".scss": ["//"],  # scss 支持 //
    ".less": ["//"],  # less 支持 //
    ".html": [],      # html 注释是 <!-- -->
    ".md": [],        # md 不严格，先不当注释
}

# 多行注释的起止符（启发式）
BLOCK_COMMENT_DELIMS = {
    ".py": [("'''", "'''"), ('"""', '"""')],
    ".js": [("/*", "*/")],
    ".ts": [("/*", "*/")],
    ".jsx": [("/*", "*/")],
    ".tsx": [("/*", "*/")],
    ".vue": [("/*", "*/"), ("<!--", "-->")],  # vue 里 template/html 注释
    ".css": [("/*", "*/")],
    ".scss": [("/*", "*/")],
    ".less": [("/*", "*/")],
    ".html": [("<!--", "-->")],
}


@dataclass
class Stats:
    files: int = 0
    total_lines: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    code_lines: int = 0
    chars: int = 0      # 字符数（含空白/换行）
    words: int = 0      # 词数（按空白 split）
    bytes: int = 0      # 文件字节数（更稳定）

    def add(self, other: "Stats") -> None:
        for k in asdict(self).keys():
            setattr(self, k, getattr(self, k) + getattr(other, k))


def is_ignored_dir(path_parts: Tuple[str, ...], ignores: set) -> bool:
    return any(part in ignores for part in path_parts)


def guess_ext(filename: str) -> str:
    _, ext = os.path.splitext(filename.lower())
    return ext


def count_lines_with_comments(ext: str, text: str) -> Tuple[int, int, int]:
    """
    返回: (blank_lines, comment_lines, code_lines)
    启发式：
    - 空行：strip 后为空
    - 注释行：
        * 行注释：strip 后以注释前缀开头
        * 块注释：识别进入/退出块注释状态，块注释内的非空行算注释行
    - 其余非空行算代码行
    """
    lines = text.splitlines()
    blank = 0
    comment = 0
    code = 0

    line_prefixes = LINE_COMMENT_PREFIX.get(ext, [])
    block_delims = BLOCK_COMMENT_DELIMS.get(ext, [])

    in_block = False
    block_end = ""

    for raw in lines:
        s = raw.strip()
        if not s:
            blank += 1
            continue

        # 如果当前在块注释中
        if in_block:
            comment += 1
            if block_end and block_end in s:
                # 简单退出
                in_block = False
                block_end = ""
            continue

        # 行注释
        if any(s.startswith(p) for p in line_prefixes):
            comment += 1
            continue

        # 块注释开始（若同一行同时结束，也计为注释行）
        started_block = False
        for start, end in block_delims:
            if start in s:
                started_block = True
                comment += 1
                # 如果这一行没有结束符，进入块注释
                if end not in s or s.index(end) < s.index(start):
                    in_block = True
                    block_end = end
                break
        if started_block:
            continue

        # 其余：代码行
        code += 1

    return blank, comment, code


def read_text_safely(path: str) -> Tuple[str, int]:
    """
    尝试读取为文本；返回(文本, 字节数)。
    遇到编码问题用 errors='replace' 保证不崩。
    """
    with open(path, "rb") as f:
        data = f.read()
    size = len(data)
    # 尝试 utf-8；失败则替换
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
    return text, size


def scan(root: str, exts: List[str], ignores: set) -> Dict[str, Stats]:
    result: Dict[str, Stats] = defaultdict(Stats)

    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        # 过滤忽略目录（原地修改 dirnames 以阻止继续递归）
        parts = tuple(os.path.relpath(dirpath, root).split(os.sep))
        if parts != (".",) and is_ignored_dir(parts, ignores):
            dirnames[:] = []
            continue

        dirnames[:] = [d for d in dirnames if d not in ignores]

        for fn in filenames:
            ext = guess_ext(fn)
            if exts and ext not in exts:
                continue

            full = os.path.join(dirpath, fn)
            try:
                text, size = read_text_safely(full)
            except (OSError, IOError):
                continue

            st = Stats()
            st.files = 1
            st.bytes = size
            st.chars = len(text)
            st.words = len(text.split())

            lines = text.splitlines()
            st.total_lines = len(lines)

            blank, comment, code = count_lines_with_comments(ext, text)
            st.blank_lines = blank
            st.comment_lines = comment
            st.code_lines = code

            result[ext if ext else "(no_ext)"].add(st)

    return result


def format_table(rows: List[List[str]]) -> str:
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    out = []
    for idx, r in enumerate(rows):
        line = "  ".join(val.ljust(widths[i]) for i, val in enumerate(r))
        out.append(line)
        if idx == 0:
            out.append("  ".join("-" * w for w in widths))
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(
        description="统计目录下代码行数/字数，并按文件类型分类汇总（py/vue/js/ts...）。"
    )
    parser.add_argument("path", nargs="?", default=".", help="项目目录（默认当前目录）")
    parser.add_argument(
        "--exts", default=",".join(DEFAULT_EXTS),
        help="要统计的扩展名，逗号分隔。例如: .py,.vue,.js （留空表示统计所有文件）"
    )
    parser.add_argument(
        "--ignore", default=",".join(sorted(DEFAULT_IGNORES)),
        help="要忽略的目录名，逗号分隔"
    )
    parser.add_argument(
        "--top", type=int, default=0,
        help="（可选）显示每类前 N 个最大文件（按代码行数），0 表示不显示"
    )
    args = parser.parse_args()

    exts = [e.strip() for e in args.exts.split(",") if e.strip()] if args.exts.strip() else []
    ignores = {d.strip() for d in args.ignore.split(",") if d.strip()}

    by_ext = scan(args.path, exts, ignores)

    # 汇总总计
    total = Stats()
    for st in by_ext.values():
        total.add(st)

    # 输出表格
    header = ["Type", "Files", "Lines", "Code", "Comments", "Blank", "Words", "Chars", "Bytes"]
    rows = [header]

    for ext in sorted(by_ext.keys(), key=lambda k: (k == "(no_ext)", k)):
        st = by_ext[ext]
        rows.append([
            ext,
            str(st.files),
            str(st.total_lines),
            str(st.code_lines),
            str(st.comment_lines),
            str(st.blank_lines),
            str(st.words),
            str(st.chars),
            str(st.bytes),
        ])

    rows.append([
        "TOTAL",
        str(total.files),
        str(total.total_lines),
        str(total.code_lines),
        str(total.comment_lines),
        str(total.blank_lines),
        str(total.words),
        str(total.chars),
        str(total.bytes),
    ])

    print(format_table(rows))


if __name__ == "__main__":
    main()
