#!/usr/bin/env bash
# ============================================================================
# Mineral AI Tracker - Multi-SLM Model Setup (PRD v8.3)
# Downloads Phi-3, Mistral and Llama-3 into the running Ollama container.
# Run AFTER `docker compose up -d` has booted the `ollama` service.
# ============================================================================

set -euo pipefail

CONTAINER="${OLLAMA_CONTAINER:-mineral-ai-ollama}"
# Fallback: locate by image name if the user named the container differently
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    CONTAINER="$(docker ps --filter "ancestor=ollama/ollama:latest" --format '{{.Names}}' | head -n1)"
fi

if [ -z "${CONTAINER}" ]; then
    echo "❌ Could not find a running Ollama container. Run: docker compose up -d ollama"
    exit 1
fi

echo "📦 Using Ollama container: ${CONTAINER}"

MODELS=(
    "phi3"      # Phi-3 mini - data extractor (~2 GB)
    "mistral"   # Mistral 7B - geology expert (~4 GB)
    "llama3"    # Llama-3 8B - risk manager (~5 GB)
    "nomic-embed-text"  # 768-dim embeddings for pgvector RAG
)

for MODEL in "${MODELS[@]}"; do
    echo ""
    echo "⬇️  Pulling ${MODEL}..."
    docker exec "${CONTAINER}" ollama pull "${MODEL}"
done

echo ""
echo "✅ All Multi-SLM models ready."
docker exec "${CONTAINER}" ollama list
