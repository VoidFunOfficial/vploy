"""
邮件发送辅助模块

提供通用的邮件发送功能，支持 HTML 和纯文本格式。
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import List, Optional, Dict, Any
from threading import Lock

# 导入统一配置管理器
try:
    from ..sys_configs import get_email_config
    USE_UNIFIED_CONFIG = True
except ImportError:
    USE_UNIFIED_CONFIG = False


# 全局锁，确保邮件发送的线程安全
_email_lock = Lock()


def email_send(
    smtp_server: str,
    smtp_port: int,
    username: str,
    password: str,
    from_name: str,
    to_emails: List[str],
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    use_ssl: bool = True,
    cc_emails: Optional[List[str]] = None,
    bcc_emails: Optional[List[str]] = None,
    extra_headers: Optional[Dict[str, str]] = None
) -> bool:
    """
    通用邮件发送函数

    参数:
        smtp_server: SMTP 服务器地址
        smtp_port: SMTP 服务器端口
        username: 发件人邮箱账号
        password: 发件人邮箱密码或授权码
        from_name: 发件人显示名称
        to_emails: 收件人邮箱列表
        subject: 邮件主题
        body_text: 邮件正文（纯文本格式）
        body_html: 邮件正文（HTML 格式，可选）
        use_ssl: 是否使用 SSL 连接（默认 True）
        cc_emails: 抄送邮箱列表（可选）
        bcc_emails: 密送邮箱列表（可选）
        extra_headers: 额外的邮件头（可选）

    返回:
        bool: 发送是否成功

    示例:
        >>> success = email_send(
        ...     smtp_server="smtp.163.com",
        ...     smtp_port=465,
        ...     username="test@163.com",
        ...     password="your_password",
        ...     from_name="测试系统",
        ...     to_emails=["recipient@example.com"],
        ...     subject="测试邮件",
        ...     body_text="这是一封测试邮件",
        ...     body_html="<h1>这是一封测试邮件</h1>"
        ... )
    """
    try:
        with _email_lock:
            # 创建邮件对象
            msg = MIMEMultipart('alternative')

            # 设置基本邮件头
            msg['From'] = f"{from_name} <{username}>"
            msg['To'] = ", ".join(to_emails)
            msg['Subject'] = Header(subject, 'utf-8')

            # 设置抄送和密送
            if cc_emails:
                msg['Cc'] = ", ".join(cc_emails)
            if bcc_emails:
                msg['Bcc'] = ", ".join(bcc_emails)

            # 设置额外的邮件头
            if extra_headers:
                for key, value in extra_headers.items():
                    msg[key] = value

            # 添加纯文本内容
            text_part = MIMEText(body_text, 'plain', 'utf-8')
            msg.attach(text_part)

            # 添加 HTML 内容（如果提供）
            if body_html:
                html_part = MIMEText(body_html, 'html', 'utf-8')
                msg.attach(html_part)

            # 构建完整的收件人列表（包括抄送和密送）
            all_recipients = to_emails.copy()
            if cc_emails:
                all_recipients.extend(cc_emails)
            if bcc_emails:
                all_recipients.extend(bcc_emails)

            # 发送邮件
            if use_ssl:
                # 使用 SSL 连接
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
                    server.login(username, password)
                    server.sendmail(username, all_recipients, msg.as_string())
            else:
                # 使用 STARTTLS
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(username, password)
                    server.sendmail(username, all_recipients, msg.as_string())

            return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"[email_send] SMTP 认证失败: {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"[email_send] SMTP 错误: {e}")
        return False
    except Exception as e:
        print(f"[email_send] 发送邮件失败: {e}")
        return False


def email_send_with_db_config(
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    to_emails: Optional[List[str]] = None,
    cc_emails: Optional[List[str]] = None,
    bcc_emails: Optional[List[str]] = None,
    extra_headers: Optional[Dict[str, str]] = None,
    db_path: str = "backend/sys_configs/system_config.db"
) -> bool:
    """
    使用数据库默认配置发送邮件的便捷函数

    参数:
        subject: 邮件主题
        body_text: 邮件正文（纯文本格式）
        body_html: 邮件正文（HTML 格式，可选）
        to_emails: 收件人邮箱列表（可选，如果不提供则使用数据库配置中的默认收件人）
        cc_emails: 抄送邮箱列表（可选）
        bcc_emails: 密送邮箱列表（可选）
        extra_headers: 额外的邮件头（可选）
        db_path: 数据库文件路径

    返回:
        bool: 发送是否成功

    示例:
        >>> # 使用数据库配置发送邮件
        >>> success = email_send_with_db_config(
        ...     subject="测试邮件",
        ...     body_text="这是一封测试邮件",
        ...     body_html="<h1>这是一封测试邮件</h1>"
        ... )

        >>> # 指定收件人
        >>> success = email_send_with_db_config(
        ...     subject="测试邮件",
        ...     body_text="这是一封测试邮件",
        ...     to_emails=["custom@example.com"]
        ... )
    """
    try:
        # 从数据库加载邮件配置
        if USE_UNIFIED_CONFIG:
            config = get_email_config(db_path)
        else:
            # 如果统一配置不可用，使用默认配置
            print("[email_send_with_db_config] 统一配置管理器不可用，使用默认配置")
            config = {
                'smtp_server': 'smtp.163.com',
                'smtp_port': 465,
                'username': 'imzfat@163.com',
                'password': 'VUnyu33GQ3guVmct',
                'from_name': 'VLogger 系统',
                'to_emails': ['imzfat@163.com'],
                'use_ssl': True
            }

        # 如果没有指定收件人，使用配置中的默认收件人
        if to_emails is None:
            to_emails = config.get('to_emails', ['imzfat@163.com'])

        # 调用通用邮件发送函数
        return email_send(
            smtp_server=config.get('smtp_server', 'smtp.163.com'),
            smtp_port=config.get('smtp_port', 465),
            username=config.get('username', 'imzfat@163.com'),
            password=config.get('password', 'VUnyu33GQ3guVmct'),
            from_name=config.get('from_name', 'VLogger 系统'),
            to_emails=to_emails,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            use_ssl=config.get('use_ssl', True),
            cc_emails=cc_emails,
            bcc_emails=bcc_emails,
            extra_headers=extra_headers
        )

    except Exception as e:
        print(f"[email_send_with_db_config] 使用数据库配置发送邮件失败: {e}")
        return False
