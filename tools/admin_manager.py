#!/usr/bin/env python3
"""
管理员账号管理工具

提供命令行界面用于管理系统管理员账号：
- 添加管理员账号
- 删除管理员账号
- 修改管理员密码
- 列出所有管理员
- 启用/禁用管理员账号
"""

import sys
import os
import argparse
from typing import Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.sys_configs.auth_config import get_auth_config


class AdminManager:
    """管理员账号管理器"""
    
    def __init__(self):
        self.auth_config = get_auth_config()
    
    def list_admins(self):
        """列出所有管理员账号"""
        conn = self.auth_config.config_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, role, is_active, created_at, last_login
            FROM users
            WHERE role = 'admin'
            ORDER BY id
        """)
        
        admins = cursor.fetchall()
        
        if not admins:
            print("未找到管理员账号")
            return
        
        print("\n" + "="*80)
        print(f"{'ID':<5} {'用户名':<15} {'状态':<8} {'创建时间':<20} {'最后登录':<20}")
        print("="*80)
        
        for admin in admins:
            admin_id, username, role, is_active, created_at, last_login = admin
            status = "启用" if is_active else "禁用"
            last_login_str = last_login if last_login else "从未登录"
            print(f"{admin_id:<5} {username:<15} {status:<8} {created_at:<20} {last_login_str:<20}")
        
        print("="*80 + "\n")
    
    def add_admin(self, username: str, password: str) -> bool:
        """添加管理员账号"""
        if self.auth_config.get_user_by_username(username):
            print(f"错误: 用户名 '{username}' 已存在")
            return False
        
        if self.auth_config.create_user(username, password, role="admin"):
            print(f"成功: 管理员账号 '{username}' 创建成功")
            return True
        else:
            print(f"错误: 创建管理员账号 '{username}' 失败")
            return False
    
    def remove_admin(self, username: str) -> bool:
        """删除管理员账号"""
        user = self.auth_config.get_user_by_username(username)
        
        if not user:
            print(f"错误: 用户 '{username}' 不存在")
            return False
        
        if user['role'] != 'admin':
            print(f"错误: 用户 '{username}' 不是管理员")
            return False
        
        # 防止删除最后一个管理员
        conn = self.auth_config.config_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1")
        admin_count = cursor.fetchone()[0]
        
        if admin_count <= 1:
            print("错误: 不能删除最后一个管理员账号")
            return False
        
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        
        print(f"成功: 管理员账号 '{username}' 已删除")
        return True
    
    def change_password(self, username: str, new_password: str) -> bool:
        """修改管理员密码"""
        user = self.auth_config.get_user_by_username(username)
        
        if not user:
            print(f"错误: 用户 '{username}' 不存在")
            return False
        
        if user['role'] != 'admin':
            print(f"错误: 用户 '{username}' 不是管理员")
            return False
        
        conn = self.auth_config.config_manager.get_connection()
        cursor = conn.cursor()
        
        salt = self.auth_config._generate_salt()
        password_hash = self.auth_config._hash_password(new_password, salt)
        
        cursor.execute("""
            UPDATE users
            SET password_hash = ?, salt = ?, updated_at = CURRENT_TIMESTAMP
            WHERE username = ?
        """, (password_hash, salt, username))
        
        conn.commit()
        
        print(f"成功: 管理员 '{username}' 的密码已更新")
        return True
    
    def toggle_status(self, username: str, enable: bool) -> bool:
        """启用或禁用管理员账号"""
        user = self.auth_config.get_user_by_username(username)

        if not user:
            print(f"错误: 用户 '{username}' 不存在")
            return False

        if user['role'] != 'admin':
            print(f"错误: 用户 '{username}' 不是管理员")
            return False

        # 防止禁用最后一个启用的管理员
        if not enable:
            conn = self.auth_config.config_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1")
            admin_count = cursor.fetchone()[0]

            if admin_count <= 1:
                print("错误: 不能禁用最后一个启用的管理员账号")
                return False

        conn = self.auth_config.config_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users
            SET is_active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE username = ?
        """, (1 if enable else 0, username))

        conn.commit()

        status = "启用" if enable else "禁用"
        print(f"成功: 管理员 '{username}' 已{status}")
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='VoidPoly 管理员账号管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有管理员
  python admin_manager.py list

  # 添加管理员
  python admin_manager.py add -u newadmin -p password123

  # 删除管理员
  python admin_manager.py remove -u oldadmin

  # 修改密码
  python admin_manager.py passwd -u admin -p newpassword

  # 禁用管理员
  python admin_manager.py disable -u admin

  # 启用管理员
  python admin_manager.py enable -u admin
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # list 命令
    subparsers.add_parser('list', help='列出所有管理员账号')

    # add 命令
    add_parser = subparsers.add_parser('add', help='添加管理员账号')
    add_parser.add_argument('-u', '--username', required=True, help='用户名')
    add_parser.add_argument('-p', '--password', required=True, help='密码')

    # remove 命令
    remove_parser = subparsers.add_parser('remove', help='删除管理员账号')
    remove_parser.add_argument('-u', '--username', required=True, help='用户名')

    # passwd 命令
    passwd_parser = subparsers.add_parser('passwd', help='修改管理员密码')
    passwd_parser.add_argument('-u', '--username', required=True, help='用户名')
    passwd_parser.add_argument('-p', '--password', required=True, help='新密码')

    # disable 命令
    disable_parser = subparsers.add_parser('disable', help='禁用管理员账号')
    disable_parser.add_argument('-u', '--username', required=True, help='用户名')

    # enable 命令
    enable_parser = subparsers.add_parser('enable', help='启用管理员账号')
    enable_parser.add_argument('-u', '--username', required=True, help='用户名')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = AdminManager()

    try:
        if args.command == 'list':
            manager.list_admins()

        elif args.command == 'add':
            manager.add_admin(args.username, args.password)

        elif args.command == 'remove':
            manager.remove_admin(args.username)

        elif args.command == 'passwd':
            manager.change_password(args.username, args.password)

        elif args.command == 'disable':
            manager.toggle_status(args.username, enable=False)

        elif args.command == 'enable':
            manager.toggle_status(args.username, enable=True)

    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()

