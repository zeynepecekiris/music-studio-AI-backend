"""
Push notifications through the Expo Push API.

Callers hand over a user id and a message kind; the text is picked per device
from the app language the device registered with. Sending happens on a
background thread so a slow push service never delays an API response.
"""
import logging
import threading
from typing import Dict, List, Optional

import httpx

from db.base import SessionLocal
from db.models import PushToken

log = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

# {name} = the other person's name, {text} = message preview
TEXTS: Dict[str, Dict[str, tuple]] = {
    "friend_request": {
        "tr": ("Yeni arkadaşlık isteği", "{name} seni arkadaş olarak eklemek istiyor"),
        "en": ("New friend request", "{name} wants to add you as a friend"),
        "de": ("Neue Freundschaftsanfrage", "{name} möchte dich als Freund hinzufügen"),
        "es": ("Nueva solicitud de amistad", "{name} quiere agregarte como amigo"),
        "fr": ("Nouvelle demande d'ami", "{name} veut t'ajouter en ami"),
        "it": ("Nuova richiesta di amicizia", "{name} vuole aggiungerti agli amici"),
        "ko": ("새 친구 요청", "{name}님이 친구 추가를 원해요"),
        "zh": ("新的好友请求", "{name} 想加你为好友"),
        "ar": ("طلب صداقة جديد", "{name} يريد إضافتك كصديق"),
    },
    "friend_accepted": {
        "tr": ("Artık arkadaşsınız", "{name} arkadaşlık isteğini kabul etti"),
        "en": ("You're friends now", "{name} accepted your friend request"),
        "de": ("Ihr seid jetzt Freunde", "{name} hat deine Anfrage angenommen"),
        "es": ("Ahora son amigos", "{name} aceptó tu solicitud de amistad"),
        "fr": ("Vous êtes amis", "{name} a accepté ta demande d'ami"),
        "it": ("Ora siete amici", "{name} ha accettato la tua richiesta"),
        "ko": ("이제 친구예요", "{name}님이 친구 요청을 수락했어요"),
        "zh": ("你们已成为好友", "{name} 接受了你的好友请求"),
        "ar": ("أصبحتما صديقين", "{name} قبل طلب صداقتك"),
    },
    "message": {
        "tr": ("{name}", "{text}"), "en": ("{name}", "{text}"), "de": ("{name}", "{text}"),
        "es": ("{name}", "{text}"), "fr": ("{name}", "{text}"), "it": ("{name}", "{text}"),
        "ko": ("{name}", "{text}"), "zh": ("{name}", "{text}"), "ar": ("{name}", "{text}"),
    },
    "song_message": {
        "tr": ("{name}", "Sana bir şarkı gönderdi 🎵"),
        "en": ("{name}", "Sent you a song 🎵"),
        "de": ("{name}", "Hat dir einen Song geschickt 🎵"),
        "es": ("{name}", "Te envió una canción 🎵"),
        "fr": ("{name}", "T'a envoyé une chanson 🎵"),
        "it": ("{name}", "Ti ha inviato una canzone 🎵"),
        "ko": ("{name}", "노래를 보냈어요 🎵"),
        "zh": ("{name}", "给你发了一首歌 🎵"),
        "ar": ("{name}", "أرسل لك أغنية 🎵"),
    },
}


# Custom sounds bundled in the app (assets/sounds, registered in app.config.js)
SOUNDS = {
    "friend_request": "friend.wav",
    "friend_accepted": "friend.wav",
    "message": "message.wav",
    "song_message": "message.wav",
}


def _display(user) -> str:
    return (getattr(user, "display_name", None) or getattr(user, "username", None) or "").strip()


def notify(db, user_id: str, kind: str, data: Optional[dict] = None, **fmt) -> None:
    """Queue a push of `kind` to every device of `user_id`. Never raises."""
    try:
        rows = db.query(PushToken).filter(PushToken.user_id == user_id).all()
        if not rows:
            return
        templates = TEXTS[kind]
        messages = []
        for r in rows:
            title, body = templates.get(r.language or "", templates["en"])
            messages.append({
                "to": r.token,
                "title": title.format(**fmt),
                "body": body.format(**fmt),
                "sound": SOUNDS.get(kind, "default"),
                "data": data or {},
            })
        threading.Thread(target=_send, args=(messages,), daemon=True).start()
    except Exception:
        log.exception("push: could not queue %s for %s", kind, user_id)


def notify_new_message(db, conv, msg, sender) -> None:
    """Message push, skipped when the receiver has this chat open right now."""
    receiver_id = conv.user_b_id if conv.user_a_id == sender.id else conv.user_a_id
    from api.routes.ws import manager  # ws imports the messages routes, so import late
    if manager.is_viewing(conv.id, receiver_id):
        return
    data = {"type": "message", "conversation_id": conv.id, "user_id": sender.id}
    if msg.content:
        text = msg.content if len(msg.content) <= 140 else msg.content[:137] + "..."
        notify(db, receiver_id, "message", data, name=_display(sender), text=text)
    else:
        notify(db, receiver_id, "song_message", data, name=_display(sender))


def _send(messages: List[dict]) -> None:
    dead = []
    try:
        with httpx.Client(timeout=10) as client:
            for i in range(0, len(messages), 100):  # Expo accepts up to 100 per call
                chunk = messages[i:i + 100]
                res = client.post(EXPO_PUSH_URL, json=chunk, headers={"Accept": "application/json"})
                tickets = (res.json() or {}).get("data") or []
                for msg, ticket in zip(chunk, tickets):
                    if ticket.get("status") == "error":
                        err = (ticket.get("details") or {}).get("error")
                        log.warning("push: %s for %s…", err or ticket.get("message"), msg["to"][:24])
                        if err == "DeviceNotRegistered":
                            dead.append(msg["to"])
    except Exception:
        log.exception("push: send failed")
    if dead:
        db = SessionLocal()
        try:
            db.query(PushToken).filter(PushToken.token.in_(dead)).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()
