"""邮件发送层：Resend（默认，需域名） + Gmail SMTP（零成本备选）。

provider 在 config.yaml 的 email.provider 切换；密钥只从环境变量读取。
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.utils import formataddr

import requests


def send_email(html: str, subject: str, email: dict):
    provider = (email.get("provider") or "resend").lower()
    to = email.get("to")
    if not to:
        raise RuntimeError("收件邮箱(email.to)未配置")

    if provider == "resend":
        _send_resend(html, subject, email, to)
    elif provider == "smtp":
        _send_smtp(html, subject, email, to)
    else:
        raise RuntimeError(f"未知邮件 provider: {provider}")


def _send_resend(html, subject, email, to):
    key = email.get("resend_api_key")
    if not key:
        raise RuntimeError("Resend 模式但未配置 RESEND_API_KEY 环境变量")
    frm = email.get("resend_from") or "ai-news@yourdomain.com"
    resp = requests.post(
        "https://api.resend.com/emails",
        json={"from": frm, "to": [to], "subject": subject, "html": html},
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        timeout=20,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Resend 发送失败 {resp.status_code}: {resp.text}")
    print("  [Resend] 已发送 →", to)


def _send_smtp(html, subject, email, to):
    user = email.get("smtp_user")
    pwd = email.get("smtp_pass")
    if not user or not pwd:
        raise RuntimeError("SMTP 模式但未配置 SMTP_USER / SMTP_PASS 环境变量")
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    ctx = ssl.create_default_context()
    with smtplib.SMTP(email.get("smtp_host", "smtp.gmail.com"),
                     int(email.get("smtp_port", 587))) as s:
        s.starttls(context=ctx)
        s.login(user, pwd)
        s.sendmail(user, [to], msg.as_string())
    print("  [SMTP] 已发送 →", to)
