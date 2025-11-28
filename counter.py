import os
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed

import networkx as nx
import matplotlib.pyplot as plt


def find_py_files(root_dir: str = "."):
    """遍历目录，返回所有 .py 文件的绝对路径列表"""
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".py"):
                full_path = os.path.join(dirpath, filename)
                py_files.append(os.path.abspath(full_path))
    return py_files


def path_to_module_name(root_dir: str, file_path: str) -> str:
    """
    将文件路径转换为类似包名的 module 名：
    root/a/b/c.py -> a.b.c
    """
    rel_path = os.path.relpath(file_path, root_dir)
    rel_no_ext = os.path.splitext(rel_path)[0]
    # 兼容 Windows 的反斜杠
    return rel_no_ext.replace(os.sep, ".")


def process_file(args):
    """
    单文件处理：
    - 读取文件，统计行数和字数
    - 解析 AST，提取 import 关系（只返回字符串，稍后再和模块名匹配）
    """
    file_path, module_name = args
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print(f"读取文件出错: {file_path} -> {e}")
        return {
            "path": file_path,
            "module": module_name,
            "lines": 0,
            "words": 0,
            "imports": set(),
        }

    # 统计行数和“字数”（按空白分割）
    # 行数用 splitlines() 比逐行循环快一点
    lines_list = content.splitlines()
    line_count = len(lines_list)
    word_count = len(content.split())

    # 解析 AST 获取 import
    imports = set()
    try:
        tree = ast.parse(content, filename=file_path)
        for node in ast.walk(tree):
            # 处理 import xxx, import xxx as y
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name:
                        imports.add(alias.name.split(".")[0])
            # 处理 from xxx import y
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
    except SyntaxError:
        # 有些文件可能不符合语法，直接跳过 import 分析
        pass

    return {
        "path": file_path,
        "module": module_name,
        "lines": line_count,
        "words": word_count,
        "imports": imports,
    }


def build_dependency_graph(results, module_name_map):
    """
    根据每个文件的 import 集合，构建模块之间的依赖图
    - 节点：模块名
    - 边：A -> B 表示 A import B
    """
    G = nx.DiGraph()

    # 先添加所有节点
    for r in results:
        G.add_node(r["module"])

    # 建立 module 首段名 -> 完整模块名 的索引
    # 比如 a.b.c -> a
    first_segment_to_modules = {}
    for full_name in module_name_map.values():
        first_seg = full_name.split(".")[0]
        first_segment_to_modules.setdefault(first_seg, set()).add(full_name)

    # 添加边
    for r in results:
        src = r["module"]
        for imp in r["imports"]:
            # 先匹配 import 的“第一段”和我们模块的“第一段”
            if imp in first_segment_to_modules:
                for target_module in first_segment_to_modules[imp]:
                    if target_module != src:
                        G.add_edge(src, target_module)

    return G


def draw_graph(G, title="Python 文件依赖网络图"):
    """绘制网络图"""
    if len(G.nodes) == 0:
        print("没有节点可绘制。")
        return

    # spring_layout 对中小规模图效果不错
    pos = nx.spring_layout(G, k=0.5, iterations=50)

    plt.figure(figsize=(10, 8))
    nx.draw(
        G,
        pos,
        with_labels=True,
        node_size=800,
        font_size=8,
        arrows=True,
        arrowstyle="-|>",
        arrowsize=12,
    )
    plt.title(title)
    plt.tight_layout()
    plt.show()


def main(root_dir: str = "."):
    root_dir = os.path.abspath(root_dir)
    print(f"统计目录: {root_dir}")

    # 1. 找到所有 py 文件
    py_files = find_py_files(root_dir)
    print(f"发现 Python 文件数量: {len(py_files)}")

    if not py_files:
        return

    # 2. 路径 -> 模块名 映射
    module_name_map = {
        path: path_to_module_name(root_dir, path) for path in py_files
    }

    # 3. 多线程处理所有文件以加速
    tasks = [(path, module_name_map[path]) for path in py_files]
    results = []

    max_workers = os.cpu_count() or 4
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(process_file, t): t[0] for t in tasks}
        for future in as_completed(future_to_path):
            res = future.result()
            results.append(res)

    # 4. 汇总统计信息
    total_lines = sum(r["lines"] for r in results)
    total_words = sum(r["words"] for r in results)

    print("\n===== 全局统计 =====")
    print(f"总行数: {total_lines}")
    print(f"总字数(按空白分隔): {total_words}\n")

    print("===== 各文件统计 =====")
    for r in sorted(results, key=lambda x: x["path"]):
        print(
            f"{r['path']}  ->  行数: {r['lines']}, 字数: {r['words']}"
        )

    # 5. 构建依赖图并绘制
    print("\n正在构建依赖网络图...")
    G = build_dependency_graph(results, module_name_map)
    print(f"图中节点数: {len(G.nodes)}, 边数: {len(G.edges)}")

    draw_graph(G, title="Python 文件 import 依赖网络图")


if __name__ == "__main__":
    # 默认统计当前目录，可以自己改成别的路径
    main(".")
