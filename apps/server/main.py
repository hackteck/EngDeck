import os
import sqlite3
import json
import subprocess
import uuid
from tempfile import NamedTemporaryFile
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

DB_PATH = os.path.join(os.path.dirname(__file__), "engdeck.db")

WHISPER_BIN = os.environ.get("ENGDECK_WHISPER_BIN") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../external/whisper.cpp/build/bin/whisper-cli"))
WHISPER_MODEL = os.environ.get("ENGDECK_WHISPER_MODEL") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models/whisper/ggml-base.en.bin"))

LLAMA_BIN = os.environ.get("ENGDECK_LLAMA_BIN") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../external/llama.cpp/build/bin/llama-cli"))
LLAMA_MODEL = os.environ.get("ENGDECK_LLAMA_MODEL") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models/llm/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf"))

FFMPEG = "ffmpeg"

app = FastAPI(title="EngDeck API", version="1.0.0")

# Mount static web (built Vue) if present
WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../apps/web/dist"))
if os.path.isdir(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="static")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB ---
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            kind TEXT,
            payload TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS stats (
            user_id TEXT PRIMARY KEY,
            words_learned INTEGER DEFAULT 0,
            mistakes_articles INTEGER DEFAULT 0,
            mistakes_prepositions INTEGER DEFAULT 0,
            mistakes_tenses INTEGER DEFAULT 0,
            mistakes_spelling INTEGER DEFAULT 0
        );
        """
    )
    conn.commit()
    conn.close()

init_db()

# --- Models ---
class GrammarRequest(BaseModel):
    user_id: str
    text: str

class ExerciseRequest(BaseModel):
    user_id: str
    limit: int = 5

# --- Helpers ---
def ensure_wav(path_in: str, path_out: str):
    # Convert to 16k mono wav
    cmd = [FFMPEG, "-y", "-i", path_in, "-ac", "1", "-ar", "16000", path_out]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def run_whisper(wav_path: str) -> str:
    # Run whisper.cpp
    cmd = [WHISPER_BIN, "-m", WHISPER_MODEL, "-f", wav_path, "-otxt", "-of", wav_path + ".out"]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    txt_file = wav_path + ".out.txt"
    with open(txt_file, "r", encoding="utf-8") as f:
        return f.read().strip()

def run_llama(prompt: str, n_predict: int = 256) -> str:
    cmd = [
        LLAMA_BIN,
        "-m", LLAMA_MODEL,
        "-p", prompt,
        "-n", str(n_predict),
        "--temp", "0.2",
        "--top-k", "20",
        "--top-p", "0.95",
        "--repeat-penalty", "1.05"
    ]
    res = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = res.stdout.decode("utf-8", errors="ignore")
    return output

def update_stats_from_issues(user_id: str, issues: List[dict]):
    conn = db()
    conn.execute("INSERT OR IGNORE INTO stats (user_id) VALUES (?)", (user_id,))
    for it in issues:
        cat = it.get("category","").lower()
        if "article" in cat:
            conn.execute("UPDATE stats SET mistakes_articles = mistakes_articles + 1 WHERE user_id = ?", (user_id,))
        elif "preposition" in cat:
            conn.execute("UPDATE stats SET mistakes_prepositions = mistakes_prepositions + 1 WHERE user_id = ?", (user_id,))
        elif "tense" in cat:
            conn.execute("UPDATE stats SET mistakes_tenses = mistakes_tenses + 1 WHERE user_id = ?", (user_id,))
        elif "spelling" in cat:
            conn.execute("UPDATE stats SET mistakes_spelling = mistakes_spelling + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- API ---
@app.post("/stt")
async def stt(user_id: str = Form(...), audio: UploadFile = File(...)):
    # Save upload
    raw_path = os.path.join("/tmp", f"engdeck_{uuid.uuid4().hex}_{audio.filename}")
    with open(raw_path, "wb") as f:
        f.write(await audio.read())

    wav_path = raw_path + ".wav"
    try:
        ensure_wav(raw_path, wav_path)
        text = run_whisper(wav_path)

        conn = db()
        conn.execute("INSERT INTO users (id) VALUES (?) ON CONFLICT(id) DO NOTHING", (user_id,))
        conn.execute("INSERT INTO events (user_id, kind, payload) VALUES (?, ?, ?)", (user_id, "stt", json.dumps({"text": text})))
        conn.commit()
        conn.close()

        return {"ok": True, "text": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})
    finally:
        for p in [raw_path, wav_path, wav_path + ".out.txt"]:
            try:
                os.remove(p)
            except Exception:
                pass

GRAMMAR_SYSTEM = """You are an English teacher. Your job is to return a STRICT JSON object with grammar and vocabulary feedback.
Always output ONLY JSON with keys: corrected, issues.
- corrected: string with corrected sentence(s).
- issues: array of {span, category, message, suggestion}.
Categories: Articles, Prepositions, Tenses, Spelling, WordChoice, Agreement, Punctuation.
"""

def build_grammar_prompt(text: str) -> str:
    return f"""{GRAMMAR_SYSTEM}

Student: "{text}"
Teacher (JSON):
"""

@app.post("/grammar")
async def grammar(req: GrammarRequest):
    prompt = build_grammar_prompt(req.text)
    raw = run_llama(prompt, n_predict=256)

    # Attempt to extract JSON from model output
    json_start = raw.find("{")
    json_end = raw.rfind("}")
    if json_start != -1 and json_end != -1 and json_end > json_start:
        try:
            payload = json.loads(raw[json_start:json_end+1])
        except Exception:
            payload = {"corrected": req.text, "issues": []}
    else:
        payload = {"corrected": req.text, "issues": []}

    issues = payload.get("issues", [])
    update_stats_from_issues(req.user_id, issues)

    # log event
    conn = db()
    conn.execute("INSERT INTO events (user_id, kind, payload) VALUES (?, ?, ?)", (req.user_id, "grammar", json.dumps(payload)))
    conn.commit()
    conn.close()

    return {"ok": True, **payload}

EXERCISE_SYSTEM = """You are an English tutor. Create short practice tasks focused on the user's weak areas.
Return STRICT JSON with key: exercises = array of {type, prompt, answer}.
Types allowed: fill_blank, choose, transform.
Keep prompts short (~12 words)."""

def build_exercise_prompt(stats: dict, limit: int) -> str:
    focus = []
    if stats.get("mistakes_articles",0) > 0: focus.append("Articles")
    if stats.get("mistakes_prepositions",0) > 0: focus.append("Prepositions")
    if stats.get("mistakes_tenses",0) > 0: focus.append("Tenses")
    if stats.get("mistakes_spelling",0) > 0: focus.append("Spelling")
    if not focus:
        focus = ["Articles", "Prepositions"]
    focus_str = ", ".join(focus)
    return f"""{EXERCISE_SYSTEM}

User weak areas: {focus_str}
Number of tasks: {limit}
Respond with JSON only.
"""

@app.post("/exercise")
async def exercise(req: ExerciseRequest):
    # get stats
    conn = db()
    row = conn.execute("SELECT words_learned, mistakes_articles, mistakes_prepositions, mistakes_tenses, mistakes_spelling FROM stats WHERE user_id = ?", (req.user_id,)).fetchone()
    conn.close()
    stats = {"words_learned":0, "mistakes_articles":0, "mistakes_prepositions":0, "mistakes_tenses":0, "mistakes_spelling":0}
    if row:
        stats = dict(zip(stats.keys(), row))

    prompt = build_exercise_prompt(stats, req.limit)
    raw = run_llama(prompt, n_predict=256)
    json_start = raw.find("{")
    json_end = raw.rfind("}")
    if json_start != -1 and json_end != -1 and json_end > json_start:
        try:
            payload = json.loads(raw[json_start:json_end+1])
        except Exception:
            payload = {"exercises": []}
    else:
        payload = {"exercises": []}

    return {"ok": True, **payload}
