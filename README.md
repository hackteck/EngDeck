# EngDeck: Offline English Learning App (Steam Deck)

This monorepo contains:
- **apps/server** — FastAPI backend (STT with whisper.cpp, grammar & exercises with llama.cpp), SQLite personalization
- **apps/web** — Vue 3 + Vite frontend (audio recorder, grammar checker, exercises)
- **packages/ui** — Minimal shared Vue components
- **external/** — Sources & builds of `whisper.cpp` and `llama.cpp`
- **models/** — Downloaded models (Whisper base.en, TinyLlama 1.1B Chat Q4_K_M)
- **scripts/** — Build & download scripts

## TL;DR (Steam Deck / SteamOS)
```bash
# 0) Switch to Desktop Mode on Steam Deck
# 1) Enable writes & install toolchain + ffmpeg (once)
sudo steamos-readonly disable
sudo pacman -Sy --needed base-devel cmake git ffmpeg python python-pip nodejs npm

# 2) Clone this project (if you downloaded the zip, skip)
# git clone <this repo> engdeck && cd engdeck

# 3) Build whisper.cpp & llama.cpp
bash scripts/build.sh

# 4) Download models (Whisper base.en + TinyLlama 1.1B Q4_K_M)
bash scripts/download_models.sh

# 5) Install Python deps & run backend
cd apps/server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# 6) Install Node deps & run frontend (new terminal)
cd ../../apps/web
npm install
npm run dev -- --host
```

Open the frontend in the Deck's browser at `http://<Deck-IP>:5173` or run it locally in Desktop mode and use the app:

- Record speech → STT via Whisper → automatic grammar feedback via TinyLlama
- Practice exercises generated from your weak areas
- All offline after the first model download

## Notes
- Binaries are used via subprocess: `external/whisper.cpp/build/bin/whisper-cli` and `external/llama.cpp/build/bin/llama-cli`.
- Models are stored in `models/` and paths are hardcoded in server for simplicity.
- SQLite DB at `apps/server/engdeck.db`.
```

## AppImage: полностью автономный билд
- Встроенный **CPython (python-build-standalone)** — без внешних зависимостей.
- Внутри AppImage лежат: бинарники `whisper-cli` и `llama-cli`, модели (`ggml-base.en.bin`, `TinyLlama-1.1B-Chat-Q4_K_M.gguf`), статический фронтенд, Python-пакеты.

### Сборка вручную локально
```bash
# в корне проекта
bash scripts/build.sh
bash scripts/download_models.sh
cd apps/web && npm install && npm run build && cd ../..

# подготовка AppDir произойдет в CI; локально можно повторить шаги из workflow
```

### GitHub Actions (ручной запуск)
Workflow в `.github/workflows/build-appimage.yml` запускается вручную из вкладки Actions (workflow_dispatch).
