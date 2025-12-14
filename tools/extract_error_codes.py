#!/usr/bin/env python3
"""
提取所有Python文件中logger.error的事件码工具

遍历所有.py文件，提取logger.error调用中的error_code参数值，
支持单行和多行调用模式，导出为列表。
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple


class ErrorCodeExtractor:
    """错误码提取器"""
    
    def __init__(self, root_dir: str = "."):
        """
        初始化提取器
        
        参数:
            root_dir: 项目根目录
        """
        self.root_dir = Path(root_dir)
        self.error_codes: Set[str] = set()
        self.error_code_locations: List[Dict] = []
        
    def extract_from_file(self, file_path: Path) -> List[Tuple[str, int, str]]:
        """
        从单个文件中提取错误码
        
        参数:
            file_path: 文件路径
            
        返回:
            List[Tuple[str, int, str]]: (错误码, 行号, 事件名称)列表
        """
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
            return results
        
        # 查找所有logger.error调用
        # 支持多行模式，使用re.DOTALL让.匹配换行符
        pattern = r'logger\.error\s*\((.*?)\)'
        
        # 先找到所有logger.error的位置
        for match in re.finditer(pattern, content, re.DOTALL):
            call_content = match.group(1)
            
            # 提取error_code参数
            # 支持多种格式: error_code="E-XXX-001" 或 error_code='E-XXX-001'
            error_code_pattern = r'error_code\s*=\s*["\']([^"\']+)["\']'
            error_code_match = re.search(error_code_pattern, call_content)
            
            # 提取event参数（第一个参数或event=）
            event_pattern = r'(?:event\s*=\s*["\']([^"\']+)["\']|^\s*["\']([^"\']+)["\'])'
            event_match = re.search(event_pattern, call_content)
            
            if error_code_match:
                error_code = error_code_match.group(1)
                event_name = ""
                
                if event_match:
                    event_name = event_match.group(1) or event_match.group(2) or ""
                
                # 计算行号
                line_num = content[:match.start()].count('\n') + 1
                
                results.append((error_code, line_num, event_name))
                
        return results
    
    def scan_directory(self, exclude_dirs: Set[str] = None) -> None:
        """
        扫描目录下所有Python文件
        
        参数:
            exclude_dirs: 要排除的目录名集合
        """
        if exclude_dirs is None:
            exclude_dirs = {
                '__pycache__', 
                '.git', 
                '.venv', 
                'venv', 
                'node_modules',
                '.pytest_cache',
                'dist',
                'build'
            }
        
        print(f"开始扫描目录: {self.root_dir}")
        print(f"排除目录: {exclude_dirs}")
        print("-" * 60)
        
        file_count = 0
        
        for py_file in self.root_dir.rglob('*.py'):
            # 检查是否在排除目录中
            if any(excluded in py_file.parts for excluded in exclude_dirs):
                continue
            
            file_count += 1
            relative_path = py_file.relative_to(self.root_dir)
            
            # 提取错误码
            codes = self.extract_from_file(py_file)
            
            if codes:
                print(f"✓ {relative_path}: 发现 {len(codes)} 个错误码")
                
                for error_code, line_num, event_name in codes:
                    self.error_codes.add(error_code)
                    self.error_code_locations.append({
                        'file': str(relative_path),
                        'line': line_num,
                        'error_code': error_code,
                        'event': event_name
                    })
        
        print("-" * 60)
        print(f"扫描完成: 共扫描 {file_count} 个文件")
        print(f"发现 {len(self.error_codes)} 个唯一错误码")
    
    def get_sorted_error_codes(self) -> List[str]:
        """
        获取排序后的错误码列表
        
        返回:
            List[str]: 排序后的错误码列表
        """
        return sorted(list(self.error_codes))
    
    def get_error_code_details(self) -> List[Dict]:
        """
        获取错误码详细信息（按文件和行号排序）
        
        返回:
            List[Dict]: 错误码详细信息列表
        """
        return sorted(
            self.error_code_locations,
            key=lambda x: (x['file'], x['line'])
        )
    
    def export_to_json(self, output_file: str = "error_codes.json") -> None:
        """
        导出为JSON文件
        
        参数:
            output_file: 输出文件路径
        """
        data = {
            'summary': {
                'total_unique_codes': len(self.error_codes),
                'total_occurrences': len(self.error_code_locations)
            },
            'error_codes': self.get_sorted_error_codes(),
            'details': self.get_error_code_details()
        }
        
        output_path = self.root_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n已导出到: {output_path}")
    
    def export_to_markdown(self, output_file: str = "error_codes.md") -> None:
        """
        导出为Markdown文件
        
        参数:
            output_file: 输出文件路径
        """
        output_path = self.root_dir / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 错误码列表\n\n")
            f.write(f"**统计信息**\n")
            f.write(f"- 唯一错误码数量: {len(self.error_codes)}\n")
            f.write(f"- 总出现次数: {len(self.error_code_locations)}\n\n")
            
            f.write("## 错误码清单\n\n")
            for code in self.get_sorted_error_codes():
                f.write(f"- `{code}`\n")
            
            f.write("\n## 详细信息\n\n")
            f.write("| 错误码 | 事件名称 | 文件 | 行号 |\n")
            f.write("|--------|----------|------|------|\n")
            
            for detail in self.get_error_code_details():
                f.write(f"| `{detail['error_code']}` | {detail['event']} | {detail['file']} | {detail['line']} |\n")
        
        print(f"已导出到: {output_path}")
    
    def print_summary(self) -> None:
        """打印摘要信息"""
        print("\n" + "=" * 60)
        print("错误码提取摘要")
        print("=" * 60)
        print(f"唯一错误码数量: {len(self.error_codes)}")
        print(f"总出现次数: {len(self.error_code_locations)}")
        print("\n错误码列表:")
        
        for code in self.get_sorted_error_codes():
            count = sum(1 for loc in self.error_code_locations if loc['error_code'] == code)
            print(f"  - {code} (出现 {count} 次)")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='提取Python代码中logger.error的错误码')
    parser.add_argument(
        '--dir',
        default='.',
        help='要扫描的根目录 (默认: 当前目录)'
    )
    parser.add_argument(
        '--json',
        default='error_codes.json',
        help='JSON输出文件名 (默认: error_codes.json)'
    )
    parser.add_argument(
        '--markdown',
        default='error_codes.md',
        help='Markdown输出文件名 (默认: error_codes.md)'
    )
    parser.add_argument(
        '--no-json',
        action='store_true',
        help='不导出JSON文件'
    )
    parser.add_argument(
        '--no-markdown',
        action='store_true',
        help='不导出Markdown文件'
    )
    
    args = parser.parse_args()
    
    # 创建提取器并扫描
    extractor = ErrorCodeExtractor(args.dir)
    extractor.scan_directory()
    
    # 打印摘要
    extractor.print_summary()
    
    # 导出文件
    if not args.no_json:
        extractor.export_to_json(args.json)
    
    if not args.no_markdown:
        extractor.export_to_markdown(args.markdown)


if __name__ == '__main__':
    main()

