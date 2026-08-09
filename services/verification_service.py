import random
import string
import os
from datetime import datetime, timedelta

import requests

# {email: {"code": "123456", "expires_at": datetime}}
_codes: dict = {}

CODE_EXPIRY_MINUTES = 10


def _generate_code() -> str:
    return ''.join(random.choices(string.digits, k=6))


def create_and_send_code(email: str) -> bool:
    code = _generate_code()
    _codes[email.lower()] = {
        "code": code,
        "expires_at": datetime.utcnow() + timedelta(minutes=CODE_EXPIRY_MINUTES),
    }

    resend_api_key = os.getenv("RESEND_API_KEY", "")
    from_email = os.getenv("FROM_EMAIL", "onboarding@resend.dev")

    if not resend_api_key:
        print(f"[verification] RESEND_API_KEY not set — code for {email}: {code}")
        return True

    payload = {
        "from": from_email,
        "to": [email],
        "subject": "🎵 MusicStudioAI — Doğrulama Kodunuz",
        "html": f"""
        <div style="font-family: sans-serif; max-width: 420px; margin: 0 auto; padding: 32px; background: #f9f9f9; border-radius: 12px;">
            <h2 style="color: #8B5CF6; margin-bottom: 4px;">🎵 MusicStudioAI</h2>
            <p style="color: #444; margin-top: 8px;">E-posta adresinizi doğrulamak için aşağıdaki kodu girin:</p>
            <div style="font-size: 38px; font-weight: 900; letter-spacing: 10px; color: #111; text-align: center; margin: 28px 0; padding: 20px; background: #fff; border-radius: 10px; border: 2px solid #e5e5e5;">
                {code}
            </div>
            <p style="color: #999; font-size: 13px; text-align: center;">Bu kod {CODE_EXPIRY_MINUTES} dakika geçerlidir.</p>
            <p style="color: #ccc; font-size: 11px; text-align: center; margin-top: 24px;">Bu kodu siz istemediyseniz görmezden gelin.</p>
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
        print(f"[verification] Code sent to {email} → {response.status_code}")
        return True
    except Exception as e:
        print(f"[verification] Failed to send code to {email}: {e}")
        return False


def verify_code(email: str, code: str) -> bool:
    entry = _codes.get(email.lower())
    if not entry:
        return False
    if datetime.utcnow() > entry["expires_at"]:
        _codes.pop(email.lower(), None)
        return False
    if entry["code"] != code:
        return False
    _codes.pop(email.lower(), None)
    return True
