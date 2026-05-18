import os
import time
import hashlib
import logging
from typing import Optional, Literal

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

app = FastAPI(title="GB29 Railway Webhook Bot", version="0.1.0")

BOT_SECRET = os.getenv("BOT_SECRET", "")
EXECUTION_MODE = os.getenv("EXECUTION_MODE", "PAPER").upper()  # LOG_ONLY / PAPER / LIVE
ALLOW_LIVE = os.getenv("ALLOW_LIVE", "false").lower() == "true"
MAX_POSITION = float(os.getenv("MAX_POSITION", "1"))
DUPLICATE_TTL_SECONDS = int(os.getenv("DUPLICATE_TTL_SECONDS", "60"))

position_state = {
    "side": "FLAT",
    "qty": 0.0,
    "symbol": None,
    "last_action": None,
    "last_reason": None,
    "updated_at": None,
}

seen_payloads = {}


class TVSignal(BaseModel):
    secret: str
    strategy: str = "GB29"
    broker: Optional[str] = "paper"
    account: Optional[str] = "SIM"
    symbol: str
    action: Literal["BUY", "SELL", "CLOSE_LONG", "CLOSE_SHORT", "CLOSE_ALL"]
    qty: float = Field(default=1.0, gt=0)
    order_type: Optional[str] = "MKT"
    reason: Optional[str] = None
    order_id: Optional[str] = None


def cleanup_seen(now: float):
    expired = [k for k, v in seen_payloads.items() if now - v > DUPLICATE_TTL_SECONDS]
    for k in expired:
        del seen_payloads[k]


def reject_if_unsafe(signal: TVSignal):
    if not BOT_SECRET:
        raise HTTPException(status_code=500, detail="BOT_SECRET not configured")

    if signal.secret != BOT_SECRET:
        raise HTTPException(status_code=401, detail="Bad secret")

    if signal.account and signal.account.upper() == "LIVE" and not ALLOW_LIVE:
        raise HTTPException(status_code=403, detail="LIVE blocked. Set ALLOW_LIVE=true only after SIM testing.")

    if signal.qty > MAX_POSITION:
        raise HTTPException(status_code=400, detail=f"Qty exceeds MAX_POSITION={MAX_POSITION}")


def paper_execute(signal: TVSignal):
    now = int(time.time())

    if signal.action == "BUY":
        position_state.update({
            "side": "LONG",
            "qty": signal.qty,
            "symbol": signal.symbol,
            "last_action": signal.action,
            "last_reason": signal.reason,
            "updated_at": now,
        })

    elif signal.action == "SELL":
        position_state.update({
            "side": "SHORT",
            "qty": signal.qty,
            "symbol": signal.symbol,
            "last_action": signal.action,
            "last_reason": signal.reason,
            "updated_at": now,
        })

    elif signal.action == "CLOSE_LONG":
        if position_state["side"] == "LONG":
            position_state.update({
                "side": "FLAT",
                "qty": 0.0,
                "last_action": signal.action,
                "last_reason": signal.reason,
                "updated_at": now,
            })

    elif signal.action == "CLOSE_SHORT":
        if position_state["side"] == "SHORT":
            position_state.update({
                "side": "FLAT",
                "qty": 0.0,
                "last_action": signal.action,
                "last_reason": signal.reason,
                "updated_at": now,
            })

    elif signal.action == "CLOSE_ALL":
        position_state.update({
            "side": "FLAT",
            "qty": 0.0,
            "last_action": signal.action,
            "last_reason": signal.reason,
            "updated_at": now,
        })

    return {
        "mode": EXECUTION_MODE,
        "paper_position": position_state,
    }


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "GB29 Railway Webhook Bot",
        "mode": EXECUTION_MODE,
        "position": position_state,
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "timestamp": int(time.time()),
        "mode": EXECUTION_MODE,
        "position": position_state,
    }


@app.post("/webhook")
async def webhook(request: Request):
    raw = await request.body()
    now = time.time()
    cleanup_seen(now)

    fingerprint = hashlib.sha256(raw).hexdigest()

    if fingerprint in seen_payloads:
        logging.warning("DUPLICATE ignored | hash=%s", fingerprint)
        return {
            "ok": True,
            "status": "duplicate_ignored",
            "hash": fingerprint,
            "position": position_state,
        }

    seen_payloads[fingerprint] = now

    try:
        data = await request.json()
        signal = TVSignal(**data)
    except Exception as e:
        logging.exception("Bad payload")
        raise HTTPException(status_code=400, detail=f"Bad payload: {str(e)}")

    reject_if_unsafe(signal)

    logging.info(
        "SIGNAL | strategy=%s broker=%s account=%s symbol=%s action=%s qty=%s reason=%s order_id=%s",
        signal.strategy,
        signal.broker,
        signal.account,
        signal.symbol,
        signal.action,
        signal.qty,
        signal.reason,
        signal.order_id,
    )

    if EXECUTION_MODE in ["LOG_ONLY", "PAPER"]:
        result = paper_execute(signal)
        return {
            "ok": True,
            "status": "accepted",
            "execution": result,
            "hash": fingerprint,
        }

    if EXECUTION_MODE == "LIVE":
        raise HTTPException(status_code=501, detail="LIVE execution not implemented yet")

    raise HTTPException(status_code=500, detail="Invalid EXECUTION_MODE")
