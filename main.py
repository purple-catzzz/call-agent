import os, json, asyncio, base64, httpx, difflib, wave, io
from datetime import datetime
from fastapi import FastAPI, Request, WebSocket, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect
from groq import Groq
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from database import get_db, init_db
from menu import MENU

# audioop was removed in Python 3.13 — fall back to audioop-lts
try:
    import audioop
except ModuleNotFoundError:
    import audioop_lts as audioop  # pip install audioop-lts


load_dotenv()

app = FastAPI()

class CallRequest(BaseModel):
    table_number: int

# Global lock to prevent Voicebox from crashing on concurrent TTS requests
tts_lock = asyncio.Lock()

# Hardcoded for Twilio Trial
CUSTOMER_PHONE = "+917483691261"

def get_best_match(name, choices):
    matches = difflib.get_close_matches(name, choices, n=1, cutoff=0.5)
    return matches[0] if matches else None

# Enable CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()

# ── Clients ──────────────────────────────────────────────────────────────────
twilio_client = Client(os.environ["TWILIO_SID"], os.environ["TWILIO_TOKEN"])
groq_client   = Groq(api_key=os.environ["GROQ_KEY"])
deepgram      = DeepgramClient(os.environ["DEEPGRAM_KEY"])

TWILIO_NUMBER = os.environ["TWILIO_NUMBER"]
SERVER_URL    = os.environ["SERVER_URL"]   # e.g. https://abc.ngrok.io

# ── System prompt — built from menu.py so there's ONE source of truth ─────────
def _build_menu_str() -> str:
    """Generate a readable menu list directly from the MENU dictionary."""
    return ", ".join(MENU.keys())

SYSTEM_PROMPT = """You are a friendly and fast AI waiter representing Veena Stores. You are speaking over a voice call to a customer at Table {{table_number}}.

Here is your official menu (these are the ONLY items available):
{menu_items}

YOUR CRITICAL RULES:
1. NEVER MENTION PRICES: The customer has a physical menu card on their table. Do not speak about prices under any circumstances.
2. VOICE FORMATTING: You are speaking over a phone line. Do not use bullet points, asterisks, bolding, or emojis. Write plain text that sounds completely natural when spoken aloud. Keep responses brief.
3. EXACT GREETING: The system has already spoken the exact greeting. Do not repeat the greeting. Just naturally continue the conversation based on the user's reply.
4. MENU INQUIRIES: If the customer asks what is available, read the items to them in a natural flow. Describe dishes appetizingly if asked. If they order something not on the menu, tell them it is unavailable and suggest an alternative.
5. CUSTOMIZATION PROMPT: Once the customer tells you their initial order, quickly repeat back the items and quantities. Immediately after repeating it back, you MUST ask: "Any customizations needed for these?"
6. FINAL CHECK: After noting any customizations they want (like "extra spicy" or "no onions"), you MUST ask: "Is there anything more?"
7. CLOSING: When the customer indicates they are done (e.g., by saying "that's it", "no", "no more", "no need", or "thank you"), say exactly: "Perfect, I've sent that to the kitchen. Enjoy your meal! [HANGUP]" and stop speaking.""".format(menu_items=_build_menu_str())


# ─────────────────────────────────────────────────────────────────────────────
# 1. API Endpoints
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/call")
async def call_table(request: CallRequest):
    table_number = request.table_number

    # 1. Validate table number range
    if table_number < 1 or table_number > 20:
        raise HTTPException(status_code=400, detail="Invalid table number. Must be between 1 and 20.")

    # 2. Check table status in DB
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT status FROM tables WHERE id = ?", (table_number,))
    table_row = c.fetchone()
    if not table_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Table {table_number} does not exist.")
    if table_row["status"] == "Occupied":
        conn.close()
        raise HTTPException(status_code=400, detail=f"Table {table_number} is already occupied.")

    # 3. Make Twilio call FIRST — only mark Occupied if it succeeds
    try:
        twilio_client.calls.create(
            to=CUSTOMER_PHONE,
            from_=TWILIO_NUMBER,
            url=f"{SERVER_URL}/call-twiml/{table_number}",
        )
    except Exception as e:
        conn.close()
        print(f"[CALL ERROR] Twilio failed for Table {table_number}: {e}")
        raise HTTPException(status_code=500, detail=f"Twilio call failed: {str(e)}")

    conn.execute("UPDATE tables SET status = 'Occupied' WHERE id = ?", (table_number,))
    conn.commit()
    conn.close()
    print(f"[CALL] Dialing {CUSTOMER_PHONE} for Table {table_number}")
    return {"status": "ok", "table": table_number}


@app.post("/form-submit")
async def form_submit(request: Request):
    """
    Webhook target for the Google Apps Script (apps_script.js).
    Google Forms sends arbitrary key/value JSON, e.g.:
        {"Table Number": "5", "Name": "Charan"}
    We search for any key containing 'table' (case-insensitive) and
    extract the integer value, then delegate to call_table.
    """
    body: dict = await request.json()
    table_number = None
    for key, value in body.items():
        if "table" in key.lower():
            try:
                table_number = int(str(value).strip())
                break
            except ValueError:
                pass
    if table_number is None:
        raise HTTPException(status_code=400, detail=f"No 'table' field found in form data: {list(body.keys())}")
    return await call_table(CallRequest(table_number=table_number))


@app.api_route("/call-twiml/{table_number}", methods=["GET", "POST"])
async def call_twiml(table_number: int):
    resp = VoiceResponse()
    connect = Connect()
    ws_url = SERVER_URL.replace("https://", "wss://").replace("http://", "ws://")
    connect.stream(url=f"{ws_url}/media-stream/{table_number}")
    resp.append(connect)
    return Response(content=str(resp), media_type="application/xml")


@app.get("/api/tables")
def get_tables():
    conn = get_db()
    tables = conn.execute("SELECT * FROM tables").fetchall()
    conn.close()
    return [dict(t) for t in tables]


@app.get("/api/tables/{table_id}")
def get_table_details(table_id: int):
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE table_id = ?", (table_id,)).fetchall()
    transcript = conn.execute("SELECT text FROM transcripts WHERE table_id = ? ORDER BY id DESC LIMIT 1", (table_id,)).fetchone()
    conn.close()
    return {
        "orders": [dict(o) for o in orders],
        "transcript": transcript["text"] if transcript else None
    }


@app.post("/api/tables/{table_id}/checkout")
def checkout_table(table_id: int):
    conn = get_db()
    conn.execute("DELETE FROM orders WHERE table_id = ?", (table_id,))
    conn.execute("DELETE FROM transcripts WHERE table_id = ?", (table_id,))
    conn.execute("UPDATE tables SET status = 'Available' WHERE id = ?", (table_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# 3. WebSocket — real-time audio bridge
#    Twilio ↔ Deepgram STT → Groq LLM → Deepgram TTS → Twilio
# ─────────────────────────────────────────────────────────────────────────────
@app.websocket("/media-stream/{table_number}")
async def media_stream(ws: WebSocket, table_number: int):
    await ws.accept()
    print(f"[WS] Call connected for Table {table_number}")

    hour = datetime.now().hour
    if hour < 12:
        time_of_day = "morning"
    elif hour < 17:
        time_of_day = "noon"
    else:
        time_of_day = "evening"

    # SYSTEM_PROMPT already has menu baked in; just fill the table number
    dynamic_prompt = SYSTEM_PROMPT.replace("{table_number}", str(table_number))

    opening_message = f"Good {time_of_day}, welcome to Veena Stores. Hi sir, what would you like to have today?"

    conversation = [
        {"role": "system", "content": dynamic_prompt},
        {"role": "assistant", "content": opening_message}
    ]
    # Use a proper queue so STT results are NEVER dropped while LLM is running
    transcript_queue: asyncio.Queue[str] = asyncio.Queue()
    stream_sid        = None
    conversation_task = None

    # ── Deepgram live STT connection ─────────────────────────────────────────
    dg_conn = deepgram.listen.asynclive.v("1")

    async def on_message(self, result, **kwargs):
        sentence = result.channel.alternatives[0].transcript
        if result.is_final and sentence.strip():
            # Always enqueue — never discard speech while LLM is busy
            await transcript_queue.put(sentence)
            print(f"[STT] {sentence}")

    async def on_error(self, error, **kwargs):
        print(f"[STT ERROR] {error}")

    dg_conn.on(LiveTranscriptionEvents.Transcript, on_message)
    dg_conn.on(LiveTranscriptionEvents.Error, on_error)

    await dg_conn.start(LiveOptions(
        model="nova-2",
        language="en-IN",          # handles Indian accents well
        encoding="mulaw",
        sample_rate=8000,
        channels=1,
        interim_results=False,
        endpointing=400,           # ms of silence = end of utterance
    ))

    # ── Main message loop — drains the queue so no speech is lost ───────────
    async def process_conversation():
        nonlocal stream_sid
        while True:
            # Block until a transcript arrives — no busy-polling
            user_text = await transcript_queue.get()

            # Drain any additional segments that arrived while we waited
            while not transcript_queue.empty():
                user_text += " " + transcript_queue.get_nowait()
            user_text = user_text.strip()

            print(f"[USER] {user_text}")
            conversation.append({"role": "user", "content": user_text})

            # Groq LLM reply
            reply = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=conversation,
                max_tokens=250,
                temperature=0.7,
            ).choices[0].message.content.strip()

            should_hangup = "[HANGUP]" in reply
            if should_hangup:
                reply = reply.replace("[HANGUP]", "").strip()

            conversation.append({"role": "assistant", "content": reply})
            print(f"[AGENT] {reply}")

            print("\n" + "="*50)
            print("FULL CONVERSATION SO FAR:")
            for msg in conversation:
                if msg["role"] == "user":
                    print(f"  YOU  : {msg['content']}")
                elif msg["role"] == "assistant":
                    print(f"  AGENT: {msg['content']}")
            print("="*50 + "\n")

            # Voicebox TTS → send to Twilio
            audio = await voicebox_tts(reply)
            if audio and stream_sid:
                await send_audio_to_twilio(ws, audio, stream_sid)

                if should_hangup:
                    print("[*] Agent requested hangup. Waiting for audio to finish playing...")
                    await asyncio.sleep((len(audio) / 8000.0) + 1.0)
                    await ws.close()
                    return

    conversation_task = asyncio.create_task(process_conversation())

    # ── Receive Twilio media frames ───────────────────────────────────────────
    try:
        async for raw in ws.iter_text():
            msg = json.loads(raw)
            event = msg.get("event")

            if event == "start":
                stream_sid = msg["start"]["streamSid"]
                print(f"[TWILIO] Stream started: {stream_sid}")
                
                # Send the initial greeting asynchronously so we don't block the media stream
                async def play_greeting():
                    audio = await voicebox_tts(opening_message)
                    if audio:
                        await send_audio_to_twilio(ws, audio, stream_sid)
                asyncio.create_task(play_greeting())

            elif event == "media":
                payload = base64.b64decode(msg["media"]["payload"])
                await dg_conn.send(payload)

            elif event == "stop":
                print("[TWILIO] Call ended")
                break

    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        # Cancel the conversation task so it doesn't leak after disconnect
        if conversation_task and not conversation_task.done():
            conversation_task.cancel()
            try:
                await conversation_task
            except asyncio.CancelledError:
                pass
        await dg_conn.finish()
        print("[WS] Disconnected")

        # Save the conversation transcript and extract orders
        if stream_sid and len(conversation) > 1:
            transcript_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in conversation if m['role'] != 'system'])
            
            # Extract orders using Groq
            extraction_prompt = f"""You are a JSON extractor. Analyze this restaurant conversation.
Extract a strict JSON array of items the customer ordered. Do not include items they didn't explicitly order.
Example format: [{{"item": "Masala Dosa", "qty": 2}}]
If nothing was ordered, return [].
Do NOT wrap in markdown blocks, return ONLY raw JSON.

Transcript:
{transcript_text}"""
            
            try:
                extract_res = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": extraction_prompt}],
                    temperature=0.0
                ).choices[0].message.content.strip()
                
                # Strip markdown code blocks if the LLM still includes them
                if extract_res.startswith("```"):
                    extract_res = extract_res.split("```")[1].replace("json\n", "").strip()
                
                orders = json.loads(extract_res)
                
                conn = get_db()
                c = conn.cursor()
                c.execute("INSERT INTO transcripts (table_id, text) VALUES (?, ?)", (table_number, transcript_text))
                
                menu_keys = list(MENU.keys())
                for o in orders:
                    item = o.get("item")
                    qty = o.get("qty", 1)
                    if item:
                        match = get_best_match(item, menu_keys)
                        if match:
                            price = MENU[match]
                            c.execute("INSERT INTO orders (table_id, item_name, quantity, price) VALUES (?, ?, ?, ?)",
                                      (table_number, match, qty, price))
                conn.commit()
                conn.close()
                print(f"[*] Extraction complete for Table {table_number}")
            except Exception as e:
                print(f"[EXTRACTION ERROR] {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Voicebox Local TTS API (Async Polling)
# ─────────────────────────────────────────────────────────────────────────────
async def convert_to_mulaw(wav_data: bytes) -> bytes | None:
    # Pure Python conversion without ffmpeg (requires standard libraries)
    try:
        with wave.open(io.BytesIO(wav_data), 'rb') as wav_file:
            params = wav_file.getparams()
            nchannels, sampwidth, framerate, nframes = params[:4]
            
            frames = wav_file.readframes(nframes)
            
            # Twilio requires 8000 Hz
            if framerate != 8000:
                frames, _ = audioop.ratecv(frames, sampwidth, nchannels, framerate, 8000, None)
            
            # Twilio requires 1 channel (mono)
            if nchannels > 1:
                frames = audioop.tomono(frames, sampwidth, 1, 1)
            
            # Convert to mulaw
            mulaw_frames = audioop.lin2ulaw(frames, sampwidth)
            return mulaw_frames
    except Exception as e:
        print(f"[AUDIO CONVERSION ERROR] Failed to convert audio: {e}")
        return None

async def voicebox_tts(text: str) -> bytes | None:
    url = "http://127.0.0.1:17493/generate"
    try:
        async with tts_lock:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(url, json={
                    "text": text,
                    "profile_id": "4fe7b178-91ce-465c-a32a-7da1875d3302",
                    "language": "en",
                    "engine": "luxtts"
                })
                if r.status_code != 200:
                    print(f"[TTS ERROR] {r.status_code}: {r.text}")
                    return None
                    
                gen_id = r.json().get("id")
                
                # Read the SSE stream for completion status
                async with client.stream("GET", f"http://127.0.0.1:17493/generate/{gen_id}/status", timeout=60.0) as poll_r:
                    async for line in poll_r.aiter_lines():
                        line = line.strip()
                        if line.startswith("data:"):
                            # 'data: {...}' -> get everything after 'data:' and strip whitespace
                            try:
                                payload = line[5:].strip()
                                data = json.loads(payload)
                                status = data.get("status")
                                if status == "completed":
                                    # Fetch the audio
                                    audio_r = await client.get(f"http://127.0.0.1:17493/audio/{gen_id}")
                                    if audio_r.status_code == 200:
                                        mulaw_audio = await convert_to_mulaw(audio_r.content)
                                        if mulaw_audio:
                                            print(f"[TTS SUCCESS] Voicebox generated {len(mulaw_audio)} bytes")
                                            return mulaw_audio
                                    break
                                elif status == "failed":
                                    print("[TTS ERROR] Generation failed in Voicebox.")
                                    break
                            except Exception as parse_e:
                                print(f"[SSE PARSE ERROR] {parse_e}")
                
                print("[TTS ERROR] Voicebox generation timed out or stream ended unexpectedly.")
                return None
    except Exception as e:
        print(f"[TTS EXCEPTION] {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Send audio bytes back to Twilio over the WebSocket
# ─────────────────────────────────────────────────────────────────────────────
async def send_audio_to_twilio(ws: WebSocket, audio: bytes, stream_sid: str):
    # Twilio expects base64-encoded mulaw audio in a media event
    chunk_size = 160  # 20ms chunks at 8kHz mulaw
    for i in range(0, len(audio), chunk_size):
        chunk = audio[i:i + chunk_size]
        payload = base64.b64encode(chunk).decode("utf-8")
        await ws.send_text(json.dumps({
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": payload}
        }))
    # Send mark event so Twilio knows audio chunk is done
    await ws.send_text(json.dumps({
        "event": "mark",
        "streamSid": stream_sid,
        "mark": {"name": "audio_done"}
    }))
