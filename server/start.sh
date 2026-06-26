#!/usr/bin/env bash
set -e

echo "=== Offline Chatbot Server ==="

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Starting Ollama..."
    ollama serve &>/tmp/ollama.log &
    sleep 3
fi

# Pull model if needed
if ! ollama list 2>/dev/null | grep -q "qwen2.5:0.5b"; then
    echo "Pulling model (first time)..."
    ollama pull qwen2.5:0.5b
fi

echo "Starting API server on http://localhost:8000..."
python3 main.py
