#!/usr/bin/env bash
set -euo pipefail

mkdir -p models/whisper models/llm

# Whisper base.en model (ggml)
if [ ! -f models/whisper/ggml-base.en.bin ]; then
  echo "Downloading Whisper ggml-base.en.bin ..."
  curl -L 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin?download=true' -o models/whisper/ggml-base.en.bin
fi

# TinyLlama 1.1B Chat v1.0 GGUF Q4_K_M (works well on CPU)
if [ ! -f models/llm/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf ]; then
  echo "Downloading TinyLlama Q4_K_M GGUF ..."
  curl -L 'https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf?download=true' -o models/llm/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf
fi

echo "Models downloaded to models/"
