from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import requests
from ..database import SessionLocal
from ..models import Message, User
from pydantic import BaseModel
import logging
import json
import re
import unicodedata
from typing import Generator, List, Dict

router = APIRouter(prefix="/api/chat")  # ensure route prefix matches frontend

LLAMA_API_URL = "http://localhost:5001"

# New: short system instruction to reduce follow-up-question behavior
SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's message directly and concisely. "
    "Do not ask clarifying or follow-up questions unless explicitly requested. "
    "Provide a single, self-contained response."
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Define request schema
class ChatRequest(BaseModel):
    message: str

@router.post("/{username}")
def chat(username: str, body: ChatRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Call llama-server for AI completion
    try:
        response = requests.post(
            f"{LLAMA_API_URL}/completion",
            json={
                # prepend system prompt so model is less likely to treat its output as new user input
                "prompt": f"{SYSTEM_PROMPT}\n\nUser: {body.message}",
                "n_predict": 128,
            },
            timeout=60
        )
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Model server unreachable")

    if not response.ok:
        raise HTTPException(status_code=500, detail="Model server error")

    try:
        output = response.json().get("content", "")
    except ValueError:
        output = response.text or ""

    # Save message in database
    message = Message(user_id=user.id, content=body.message, response=output)
    db.add(message)
    db.commit()
    db.refresh(message)

    return {"response": output, "id": getattr(message, "id", None)}


# New: history endpoint so frontend can GET /api/chat/{username}/history
@router.get("/{username}/history")
def history(username: str, db: Session = Depends(get_db)) -> List[Dict]:
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Use created_at for ordering when available; otherwise fallback to id
        order_clause = None
        if hasattr(Message, "created_at"):
            try:
                order_clause = Message.created_at.asc()
            except Exception:
                order_clause = None

        query = db.query(Message).filter(Message.user_id == user.id)
        if order_clause is not None:
            query = query.order_by(order_clause)
        else:
            query = query.order_by(Message.id.asc())

        msgs = query.all()

        return [
            {
                "id": m.id,
                "content": m.content,
                "response": m.response,
                "created_at": getattr(m, "created_at", None).isoformat() if getattr(m, "created_at", None) else None,
            }
            for m in msgs
        ]
    except HTTPException:
        # re-raise known HTTP exceptions
        raise
    except Exception:
        logging.exception("Failed to fetch history for user: %s", username)
        raise HTTPException(status_code=500, detail="Failed to fetch history")


# New: streaming endpoint that proxies model server streaming output as SSE
@router.post("/{username}/stream")
def chat_stream(username: str, body: ChatRequest) -> StreamingResponse:
    # Validate
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    # Ensure user exists
    db_check = SessionLocal()
    try:
        user = db_check.query(User).filter(User.username == username).first()
    finally:
        db_check.close()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Initiate streaming request to model server
    try:
        upstream = requests.post(
            f"{LLAMA_API_URL}/completion",
            json={
                # use same system prompt for streaming calls
                "prompt": f"{SYSTEM_PROMPT}\n\nUser: {body.message}",
                "n_predict": 512,
                "stream": True
            },
            timeout=120,
            stream=True,
        )
    except requests.RequestException:
        logging.exception("Failed to connect to model server for streaming")
        raise HTTPException(status_code=502, detail="Model server unreachable")

    if not upstream.ok:
        try:
            logging.error("Model server returned: %s", upstream.text)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail="Model server error")

    def event_stream() -> Generator[str, None, None]:
        output_parts: List[str] = []
        last_char = ""  # track last emitted character to decide on spacing

        # common mojibake -> unicode fixes
        MOJIBAKE_MAP = {
            "â": "’",
            "â€™": "’",
            "â€“": "–",
            "â€”": "—",
            "â€œ": "“",
            "â€\u009d": "”",
            "Ã©": "é",
            "Ã¡": "á",
            # add more if you see other patterns
        }

        def fix_mojibake(s: str) -> str:
            if not s:
                return s
            for bad, good in MOJIBAKE_MAP.items():
                if bad in s:
                    s = s.replace(bad, good)
            return s

        def is_punct_or_symbol(ch: str) -> bool:
            """Return True if character is punctuation or symbol (Unicode categories P* or S*)."""
            if not ch:
                return False
            try:
                cat = unicodedata.category(ch)
                return cat and cat[0] in ("P", "S")
            except Exception:
                return False

        def normalize_and_space(prev_last: str, piece: str):
            """
            Preserve newlines; normalize spacing around tokens:
            - keep existing newlines
            - insert single space between adjacent alnum tokens when needed
            - insert space on lowercase->Uppercase boundary inside piece
            - never insert space before punctuation or newline
            Returns (normalized_piece, new_last_char).
            """
            if piece is None or piece == "":
                return piece, prev_last

            piece = fix_mojibake(piece)

            # Insert spaces at lowercase->Uppercase transitions inside piece
            piece = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', piece)

            # Normalize internal whitespace but preserve newline characters.
            piece = piece.replace("\r\n", "\n").replace("\r", "\n")
            piece = re.sub(r'[ \t]+', ' ', piece)
            piece = re.sub(r'\n{3,}', '\n\n', piece)

            # Find first non-space char (keeping newlines)
            first_char = None
            for c in piece:
                if not c.isspace():
                    first_char = c
                    break
                if c == '\n':
                    first_char = '\n'
                    break
            if first_char is None:
                # piece is only whitespace/newlines
                new_last = prev_last
                for c in reversed(piece):
                    if c == '\n':
                        new_last = '\n'
                        break
                    if not c.isspace():
                        new_last = c
                        break
                return piece, new_last

            # Decide whether to insert a leading space between prev_last and piece
            need_space = False
            if first_char == '\n' or is_punct_or_symbol(first_char):
                need_space = False
            else:
                if prev_last and (not prev_last.isspace()) and prev_last.isalnum() and first_char.isalnum():
                    need_space = True
                if prev_last and prev_last.islower() and first_char.isupper():
                    need_space = True

            # don't add space if piece begins with punctuation that should attach to previous token
            if piece and piece.lstrip().startswith(tuple([",", ".", ":", ";", "?", "!", "'", "’", "”", "%", ")"])):
                need_space = False

            if need_space:
                piece = " " + piece

            # determine new last non-space char (but if last is newline, record newline)
            new_last = prev_last
            for c in reversed(piece):
                if c == '\n':
                    new_last = '\n'
                    break
                if not c.isspace():
                    new_last = c
                    break

            return piece, new_last

        try:
            # Prefer iter_lines for line-delimited JSON/text chunks
            for raw in upstream.iter_lines(decode_unicode=True):
                if raw is None:
                    continue
                # preserve raw (do not strip) so embedded newline tokens remain
                chunk = raw
                if chunk == "":
                    continue

                payload = chunk
                if chunk.startswith("data:"):
                    payload = chunk[len("data:"):].lstrip()
                elif chunk.startswith("event:"):
                    yield f"{chunk}\n\n"
                    continue

                text_piece = ""
                try:
                    parsed = json.loads(payload)
                    text_piece = parsed.get("content") or parsed.get("text") or parsed.get("response") or ""
                    if not text_piece and isinstance(parsed.get("data"), dict):
                        text_piece = parsed["data"].get("content") or parsed["data"].get("text") or ""
                except Exception:
                    text_piece = payload

                if text_piece is not None and text_piece != "":
                    norm_piece, last_char = normalize_and_space(last_char, text_piece)
                    output_parts.append(norm_piece)
                    yield f"data: {norm_piece}\n\n"
        except Exception:
            logging.exception("Error while streaming from upstream; attempting fallback")
            try:
                # keepends=True preserves newline characters inside each line
                for raw in upstream.iter_content(chunk_size=1024):
                    if not raw:
                        continue
                    try:
                        chunk_text = raw.decode("utf-8", errors="ignore") if isinstance(raw, (bytes, bytearray)) else str(raw)
                    except Exception:
                        chunk_text = str(raw)
                    for line in chunk_text.splitlines(keepends=True):
                        if line == "":
                            continue
                        payload = line
                        if line.startswith("data:"):
                            payload = line[len("data:"):].lstrip()
                        elif line.startswith("event:"):
                            yield f"{line}\n\n"
                            continue

                        text_piece = ""
                        try:
                            parsed = json.loads(payload)
                            text_piece = parsed.get("content") or parsed.get("text") or parsed.get("response") or ""
                            if not text_piece and isinstance(parsed.get("data"), dict):
                                text_piece = parsed["data"].get("content") or parsed["data"].get("text") or ""
                        except Exception:
                            text_piece = payload

                        if text_piece is not None and text_piece != "":
                            norm_piece, last_char = normalize_and_space(last_char, text_piece)
                            output_parts.append(norm_piece)
                            yield f"data: {norm_piece}\n\n"
            except Exception:
                logging.exception("Fallback stream read failed")
                yield f"event: error\ndata: {json.dumps({'detail': 'Upstream stream read error'})}\n\n"
                return
        finally:
            try:
                upstream.close()
            except Exception:
                pass

        full_text = "".join(output_parts)

        # Save the full message into DB now that streaming finished
        db = SessionLocal()
        try:
            msg = Message(user_id=user.id, content=body.message, response=full_text)
            db.add(msg)
            db.commit()
            db.refresh(msg)
            created_at_val = getattr(msg, "created_at", None)
            meta = {"id": msg.id, "created_at": created_at_val.isoformat() if created_at_val else None}
            yield f"event: done\ndata: {json.dumps(meta)}\n\n"
        except Exception:
            db.rollback()
            logging.exception("Failed to save streamed message to database")
            yield f"event: error\ndata: {json.dumps({'detail': 'DB save failed'})}\n\n"
        finally:
            db.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
