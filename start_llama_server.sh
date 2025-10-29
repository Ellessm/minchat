#!/bin/bash

# --------------------------------------------
# Launch llama.cpp server using installed binary
# --------------------------------------------

# Path to your model directory
MODEL_DIR="/Users/levyminchala/Documents/code_projects/minchat/models"

# Model file to load
MODEL_FILE="gemma-2-9b-it-Q6_K_L.gguf"

# Full path to model
MODEL_PATH="$MODEL_DIR/$MODEL_FILE"

# Server port
PORT=5001

# Performance settings
N_GPU_LAYERS=35
CONTEXT_SIZE=4096

# Check if the model exists
if [ ! -f "$MODEL_PATH" ]; then
    echo "Error: Model file not found at $MODEL_PATH"
    exit 1
fi

# Locate llama-server or fallback to llama-cli
if command -v llama-server &>/dev/null; then
    LLAMA_BIN=$(command -v llama-server)
elif command -v llama-cli &>/dev/null; then
    LLAMA_BIN=$(command -v llama-cli)
else
    echo "Error: Neither llama-server nor llama-cli found in PATH."
    exit 1
fi

# Start the server
echo "Starting llama server..."
$LLAMA_BIN -m "$MODEL_PATH" \
           --port $PORT \
           --ctx-size $CONTEXT_SIZE \
           --n-gpu-layers $N_GPU_LAYERS
