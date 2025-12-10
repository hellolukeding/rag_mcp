import base64
import hashlib
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from database.models import db_manager
from utils.jwt import create_jwt
from utils.logger import logger


def _generate_captcha_text(length: int = 5) -> str:
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # avoid confusing chars
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def _render_svg_captcha(text: str, width: int = 180, height: int = 60) -> str:
    # Simple SVG with character transforms and noise lines
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    parts.append(f'<rect width="100%" height="100%" fill="#f6f7fb"/>')
    # background noise lines
    for i in range(6):
        x1 = secrets.randbelow(width)
        y1 = secrets.randbelow(height)
        x2 = secrets.randbelow(width)
        y2 = secrets.randbelow(height)
        stroke = f'rgba(0,0,0,{0.06 + secrets.randbelow(20)/200})'
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="1"/>')

    # draw characters
    cx = 18
    for ch in text:
        rotate = secrets.randbelow(30) - 15
        ty = 35 + (secrets.randbelow(11) - 5)
        font_size = 28 + secrets.randbelow(6)
        fill = f'rgba({50+secrets.randbelow(120)},{50+secrets.randbelow(120)},{50+secrets.randbelow(120)},1)'
        parts.append(
            f'<text x="{cx}" y="{ty}" font-family="Arial,Helvetica,sans-serif" font-size="{font_size}" fill="{fill}" transform="rotate({rotate} {cx} {ty})">{ch}</text>'
        )
        cx += 28

    parts.append('</svg>')
    return '\n'.join(parts)


router = APIRouter()


class CaptchaStartResponse(BaseModel):
    session_id: str
    expires_at: Optional[str] = None


class CaptchaSubmitRequest(BaseModel):
    session_id: str
    events: dict


class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_session_id: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/auth/captcha/start", response_model=CaptchaStartResponse)
async def captcha_start():
    # create a session id and persist empty session; client will submit events
    session_id = secrets.token_hex(16)
    expires_dt = datetime.utcnow() + timedelta(minutes=5)
    # store a datetime object (db helper will handle normalization)
    await db_manager.insert_behavior_captcha(session_id=session_id, events=None, expires_at=expires_dt)
    logger.info(f"Created behavior captcha session: {session_id}")
    return CaptchaStartResponse(session_id=session_id, expires_at=expires_dt.isoformat())


@router.post("/auth/captcha/image/start")
async def captcha_image_start():
    """Generate an SVG image captcha, store hash of the answer, and return data url."""
    session_id = secrets.token_hex(16)
    text = _generate_captcha_text(5)
    svg = _render_svg_captcha(text)
    b64 = base64.b64encode(svg.encode('utf-8')).decode('ascii')
    data_url = f"data:image/svg+xml;base64,{b64}"

    # store hash of expected answer (lowercased)
    answer_hash = hashlib.sha256(text.lower().encode('utf-8')).hexdigest()
    expires_dt = datetime.utcnow() + timedelta(minutes=5)
    await db_manager.insert_behavior_captcha(session_id=session_id, events={"type": "image", "answer_hash": answer_hash}, expires_at=expires_dt)
    logger.info(f"Created image captcha session: {session_id}")
    return {"session_id": session_id, "image": data_url, "expires_at": expires_dt.isoformat()}


class ImageVerifyRequest(BaseModel):
    session_id: str
    answer: str


@router.post("/auth/captcha/image/verify")
async def captcha_image_verify(req: ImageVerifyRequest):
    session = await db_manager.get_captcha_by_session(req.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Captcha session not found")

    # compare hash
    events_raw = session.get("events")
    try:
        stored = json.loads(events_raw) if isinstance(
            events_raw, str) else events_raw or {}
    except Exception:
        stored = {}
    expected_hash = stored.get("answer_hash")
    if not expected_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No image captcha stored for this session")

    test_hash = hashlib.sha256(
        req.answer.strip().lower().encode('utf-8')).hexdigest()
    verified = secrets.compare_digest(test_hash, expected_hash)
    if verified:
        await db_manager.mark_captcha_verified(req.session_id)

    return {"session_id": req.session_id, "verified": verified}


@router.post("/auth/captcha/submit")
async def captcha_submit(req: CaptchaSubmitRequest):
    # store events and perform a simple heuristic verification
    session = await db_manager.get_captcha_by_session(req.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Captcha session not found")

    # store events
    await db_manager.insert_behavior_captcha(session_id=req.session_id, events=req.events, expires_at=session.get("expires_at"))

    # Simple heuristic: require at least 4 events and duration >= 800ms
    verified = False
    try:
        events = req.events.get("events") if isinstance(
            req.events, dict) else None
        if isinstance(events, list) and len(events) >= 4:
            # expect events have timestamps in ms
            times = [e.get("t")
                     for e in events if isinstance(e, dict) and "t" in e]
            if len(times) >= 2:
                duration = max(times) - min(times)
                if duration >= 800:
                    verified = True
    except Exception:
        verified = False

    if verified:
        await db_manager.mark_captcha_verified(req.session_id)

    return {"session_id": req.session_id, "verified": verified}


@router.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    # Check captcha
    captcha = await db_manager.get_captcha_by_session(req.captcha_session_id)
    if not captcha or not captcha.get("verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Captcha not verified")

    # Lookup user
    user = await db_manager.get_user_by_username(req.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Verify password using stored salt+hash
    import hashlib

    salt = user.get("password_salt")
    expected_hash = user.get("password_hash")
    test_hash = hashlib.pbkdf2_hmac("sha256", req.password.encode(
        "utf-8"), salt.encode("utf-8"), 100_000).hex()
    if not secrets.compare_digest(test_hash, expected_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # issue JWT
    payload = {
        "sub": str(user["id"]),
        "username": user["username"]
    }
    token = create_jwt(payload, expire_seconds=3600)
    return LoginResponse(access_token=token)
