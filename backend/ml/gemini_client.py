"""
Mineral AI Tracker - Gemini AI Client (PRD v13.2 Phase 13.2)
Version: 13.0
Description: Google Gemini AI integration for multi-model selector
Phase 13.2: Model-Agnostic Architecture with dynamic pricing
"""

import os
import asyncio
from typing import Optional
from loguru import logger


class GeminiClient:
    """
    Google Gemini AI client for cloud-based analysis
    
    Supports:
    - gemini-1.5-flash: Fast analysis (2 credits)
    - gemini-1.5-pro: Deep analysis (5 credits)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None
        
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai
                logger.info("Gemini client initialized successfully")
            except ImportError:
                logger.warning("google-generativeai not installed. Gemini features unavailable.")
                self.api_key = None
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.api_key = None
        else:
            logger.info("GEMINI_API_KEY not set. Gemini features unavailable.")
    
    def is_available(self) -> bool:
        """Check if Gemini is configured and available"""
        return bool(self.api_key and self._client)
    
    async def generate_flash(self, prompt: str) -> str:
        """
        Generate using gemini-1.5-flash (fast, 2 credits)
        
        Args:
            prompt: The input prompt for generation
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If generation fails
        """
        if not self.is_available():
            raise RuntimeError("Gemini API not configured or unavailable")
        
        try:
            model = self._client.GenerativeModel('gemini-1.5-flash')
            response = await model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini Flash generation failed: {e}")
            raise
    
    async def generate_pro(self, prompt: str) -> str:
        """
        Generate using gemini-1.5-pro (deep analysis, 5 credits)
        
        Args:
            prompt: The input prompt for generation
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If generation fails
        """
        if not self.is_available():
            raise RuntimeError("Gemini API not configured or unavailable")
        
        try:
            model = self._client.GenerativeModel('gemini-1.5-pro')
            response = await model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini Pro generation failed: {e}")
            raise
