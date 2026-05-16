"""
Mineral AI Tracker - Ollama Integration (PRD v8.3)
Version: 8.3
Description: Multi-SLM Local LLM integration using Ollama (Phi-3, Mistral, Llama-3)
"""

import httpx
from typing import List, Optional
from loguru import logger
from config import settings


class OllamaClient:
    """Client for interacting with local Ollama instance (Multi-SLM)"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        phi3_model: Optional[str] = None,
        mistral_model: Optional[str] = None,
        llama3_model: Optional[str] = None,
    ):
        self.base_url = base_url or (settings.OLLAMA_URL if hasattr(settings, 'OLLAMA_URL') else "http://ollama:11434")
        # Multi-SLM model identifiers (PRD v8.3)
        self.phi3_model = phi3_model or getattr(settings, 'OLLAMA_PHI3_MODEL', 'phi-3')
        self.mistral_model = mistral_model or getattr(settings, 'OLLAMA_MISTRAL_MODEL', 'mistral')
        self.llama3_model = llama3_model or getattr(settings, 'OLLAMA_LLAMA3_MODEL', 'llama3')
        self.timeout = 120
    
    async def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> List[float]:
        """
        Generate embedding for text using Ollama
        
        Args:
            text: Text to embed
            model: Model to use for embedding (default: nomic-embed-text)
        
        Returns:
            List of float values representing the embedding
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": model,
                        "prompt": text
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get("embedding", [])
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []
    
    async def generate_sequential(
        self,
        model: str,
        prompt: str,
        keep_alive: int = 0,
        timeout: float = 180.0,
    ) -> str:
        """
        Sequential Memory-Optimized Mode (PRD v8.3).

        Loads the model into RAM/VRAM, runs the prompt, then unloads it
        immediately via Ollama's `keep_alive: 0` flag. This trades latency
        for memory, allowing Multi-SLM orchestration on 16 GB machines.

        Use this for the Debate Protocol (Phi-3 -> Mistral -> Llama-3).
        """
        logger.info(f"🧠 Loading {model} into memory (sequential mode)...")
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": keep_alive,
        }
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"🧹 Unloading {model} from memory.")
                return data.get("response", "")
        except Exception as e:
            logger.error(f"generate_sequential error for {model}: {e}")
            raise

    async def chat_completion(
        self,
        prompt: str,
        model: str = "llama3",
        context: Optional[str] = None
    ) -> str:
        """
        Generate chat completion using Ollama
        
        Args:
            prompt: User prompt
            model: Model to use (default: llama3)
            context: Optional context for RAG
        
        Returns:
            Generated response text
        """
        try:
            messages = []
            
            if context:
                messages.append({
                    "role": "system",
                    "content": f"Context: {context}"
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Error generating chat completion: {e}")
            return ""
    
    async def check_health(self) -> bool:
        """Check if Ollama service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def pull_model(self, model: str) -> bool:
        """
        Pull a model from Ollama registry
        
        Args:
            model: Model name to pull
        
        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error pulling model {model}: {e}")
            return False


# Singleton instance
ollama_client = OllamaClient()
