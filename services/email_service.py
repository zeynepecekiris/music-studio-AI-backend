import os
from datetime import datetime

import requests


def send_new_user_notification(username: str, email: str):
    resend_api_key = os.getenv("RESEND_API_KEY", "")
    admin_email = os.getenv("ADMIN_EMAIL", "zeynep.ece933@gmail.com")
    from_email = os.getenv("FROM_EMAIL", "onboarding@resend.dev")

    if not resend_api_key:
        print("[email_service] RESEND_API_KEY not set, skipping notification")
        return

    registered_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    payload = {
        "from": from_email,
        "to": [admin_email],
        "subject": f"🎵 Yeni kullanıcı kayıt oldu: @{username}",
        "html": f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; background: #f9f9f9; border-radius: 12px;">
            <h2 style="color: #8B5CF6; margin-bottom: 4px;">🎵 MusicStudioAI</h2>
            <p style="color: #666; margin-top: 0;">Yeni kullanıcı bildirimi</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #999; font-size: 13px; width: 40%;">Kullanıcı adı</td>
                    <td style="padding: 8px 0; color: #111; font-weight: 600;">@{username}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #999; font-size: 13px;">E-posta</td>
                    <td style="padding: 8px 0; color: #111;">{email}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #999; font-size: 13px;">Kayıt zamanı</td>
                    <td style="padding: 8px 0; color: #111;">{registered_at}</td>
                </tr>
            </table>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
            <p style="color: #aaa; font-size: 12px; margin: 0;">Bu bildirim otomatik olarak gönderilmiştir.</p>
        </div>
        """,
    }

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            json=payload,
            headers={"Authorization": f"Bearer {resend_api_key}"},
            timeout=10,
        )
        response.raise_for_status()
        print(f"[email_service] Notification sent for @{username} → {response.status_code}")
    except Exception as e:
        print(f"[email_service] Failed to send notification: {e}")
