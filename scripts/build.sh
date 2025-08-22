#!/usr/bin/env bash
set -euo pipefail

# Build whisper.cpp
mkdir -p external
if [ ! -d external/whisper.cpp ]; then
  git clone https://github.com/ggml-org/whisper.cpp external/whisper.cpp
fi
pushd external/whisper.cpp >/dev/null
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
popd >/dev/null

# Build llama.cpp
if [ ! -d external/llama.cpp ]; then
  git clone https://github.com/ggml-org/llama.cpp external/llama.cpp
fi
pushd external/llama.cpp >/dev/null
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j --target llama-cli
popd >/dev/null

echo "Build complete. Binaries:"
echo " - external/whisper.cpp/build/bin/whisper-cli"
echo " - external/llama.cpp/build/bin/llama-cli"
