"""
Blocking and reporting helpers (App Store guideline 1.2: user-generated content).

A block works both ways: neither person sees the other's profile, wall posts,
songs, stories, feed items or messages, and neither can message or friend the
other. Routes call hidden_user_ids() and filter with it.
"""
import os
import threading
from datetime import datetime
from typing import Optional, Set

import requests
from sqlalchemy import or_
from sqlalchemy.orm import Session

from config.settings import settings
from db.models import UserBlock

# A post reported by this many different people is hidden until reviewed
AUTO_HIDE_REPORTS = 3


def hidden_user_ids(db: Session, user_id: Optional[str]) -> Set[str]:
    """Everyone I blocked plus everyone who blocked me."""
    if not user_id:
        return set()
    rows = db.query(UserBlock.blocker_id, UserBlock.blocked_id).filter(
        or_(UserBlock.blocker_id == user_id, UserBlock.blocked_id == user_id)
    ).all()
    return {b if a == user_id else a for a, b in rows}


def is_blocked_between(db: Session, a: Optional[str], b: Optional[str]) -> bool:
    if not a or not b or a == b:
        return False
    return db.query(UserBlock).filter(
        or_(
            (UserBlock.blocker_id == a) & (UserBlock.blocked_id == b),
            (UserBlock.blocker_id == b) & (UserBlock.blocked_id == a),
        )
    ).first() is not None


def notify_admin_of_report(report_id: str, reporter: str, target_type: str, target_id: str,
                           target_user: Optional[str], reason: str, note: Optional[str]) -> None:
    """E-mail the admin so a report is looked at within a day (Resend, background)."""
    key = os.getenv("RESEND_API_KEY", "")
    admin = settings.ADMIN_EMAIL
    if not key or not admin:
        print(f"[moderation] report {report_id} stored (no e-mail configured)")
        return
    sender = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
    when = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    html = f"""
    <div style="font-family:sans-serif;max-width:520px;padding:24px">
      <h2 style="margin:0 0 8px">⚠️ Yeni şikayet</h2>
      <p style="color:#666;margin:0 0 16px">{when}</p>
      <p><b>Tür:</b> {target_type} &nbsp; <b>Sebep:</b> {reason}</p>
      <p><b>İçerik id:</b> {target_id}</p>
      <p><b>Şikayet edilen:</b> @{target_user or '-'} &nbsp; <b>Şikayet eden:</b> @{reporter}</p>
      <p><b>Not:</b> {(note or '-')}</p>
      <p style="color:#999;font-size:12px">Rapor id: {report_id}. 3 farklı şikayet alan gönderi otomatik gizlenir.</p>
    </div>"""

    def _go():
        try:
            requests.post(
                "https://api.resend.com/emails",
                json={"from": sender, "to": [admin], "subject": f"⚠️ Şikayet: {target_type} ({reason})", "html": html},
                headers={"Authorization": f"Bearer {key}"},
                timeout=10,
            ).raise_for_status()
        except Exception as e:  # never fail the request over an e-mail
            print(f"[moderation] report e-mail failed: {e}")

    threading.Thread(target=_go, daemon=True).start()
