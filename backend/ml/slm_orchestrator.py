"""
Mineral AI Tracker - Multi-SLM Orchestrator (PRD v8.3)
Version: 9.0
Description: The Debate Protocol - Multi-SLM orchestration for AI intelligence
PRD v9.0 Phase 9.9: Enhanced graceful degradation for external API failures
PRD v9.0 Phase 10.2: Hive Mind cognitive injection for swarm intelligence
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
import json
import httpx
from loguru import logger

# Import models
from models.geology import GeologicalData, GeoEvent
from models.finance import CompanyFinancials, AssetScore
from ml.ollama_client import OllamaClient
from utils.fmp_client import fetch_fmp_fundamentals, format_fmp_for_prompt
from engines.technical import TechnicalAnalyzer, default_technical_analyzer
from engines.rag_engine import RAGEngine
from notifications.telegram import send_telegram_alert
from notifications.discord import send_discord_alert


class SLMMeta(Enum):
    """SLM Model identifiers"""
    PHI3 = "phi-3"  # Data Extractor
    MISTRAL = "mistral"  # Geology Expert
    LLAMA3 = "llama3"  # Risk Manager


@dataclass
class DebateStep:
    """Single step in the debate protocol"""
    slm: SLMMeta
    timestamp: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    reasoning: str
    confidence: int


@dataclass
class DebateResult:
    """Final result from the debate protocol"""
    signal_type: str  # BUY, SELL, HOLD, SHORT
    confidence_score: int  # 0-100
    recommendation: str
    debate_log: List[DebateStep]
    consensus_score: float  # 0-1, how much the SLMs agreed
    pydantic_passed: bool
    pydantic_errors: List[str]


class SLMOrchestrator:
    """
    Multi-SLM Orchestrator implementing The Debate Protocol
    
    Pipeline:
    1. Phi-3 (Data Extractor): Raw HTML/Markdown -> Clean JSON
    2. Pydantic Firewall: Validate against physics/finance laws
    3. Mistral (Geologist): Assess geological/fundamental quality
    4. Llama-3 (Risk Manager): Devil's advocate, check DXY/macro
    5. Consensus: If disagree, lower Confidence Score
    """
    
    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client
        self.debate_log: List[DebateStep] = []
        self.technical_analyzer = TechnicalAnalyzer()
        self.market_api_base = "http://localhost:8000"  # Default to local backend
        self.rag_engine = RAGEngine(ollama_client)  # Phase 12: RAG engine for historical context
    
    async def _fetch_technical_analysis(self, ticker: str) -> Dict[str, Any]:
        """Fetch technical analysis data for a ticker"""
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                # Get OHLC data from market proxy
                response = await client.get(
                    f"http://localhost:8000/api/market/ohlc/{ticker}",
                    params={"period": "3m", "interval": "1d"}
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("degraded"):
                        logger.warning(f"OHLC data degraded for {ticker}")
                        return {}
                    # Calculate technical indicators
                    ohlc_data = data.get("data", [])
                    if ohlc_data:
                        analyzer = default_technical_analyzer
                        return analyzer.calculate_indicators(ohlc_data)
        except Exception as e:
            logger.warning(f"Failed to fetch technical analysis for {ticker}: {e}")
        return {}
    
    async def _fetch_hive_consensus(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch Hive Mind consensus for a ticker (PRD v9.0 Phase 10.2)
        
        Calls the hive aggregator to get swarm intelligence from other users' analyses.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"http://localhost:8000/api/hive/consensus/{ticker}"
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Hive consensus returned status {response.status_code}")
                    return {}
        except Exception as e:
            logger.warning(f"Failed to fetch hive consensus for {ticker}: {e}")
            return {}
    
    async def _trigger_sentinel_alerts(
        self,
        signal_type: str,
        confidence: int,
        recommendation: str,
        ticker: str,
        hive_data: Dict[str, Any]
    ):
        """
        Trigger Sentinel alerts based on user-configured thresholds (PRD v9.0 Phase 10.2)
        
        Checks user's alert_configs and sends notifications via Telegram/Discord
        if the signal meets the configured thresholds.
        """
        try:
            # Fetch user alert configurations from database
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="mineral_ai_tracker",
                user="mineral_user",
                password="mineralpass123",
                cursor_factory=RealDictCursor
            )
            
            try:
                with conn.cursor() as cur:
                    # Get active alert configs
                    cur.execute("""
                        SELECT config_id, min_confidence_threshold, signal_types,
                               telegram_chat_id, discord_webhook_url
                        FROM alert_configs
                        WHERE is_active = TRUE
                    """)
                    configs = cur.fetchall()
                    
                    for config in configs:
                        # Check if confidence meets threshold
                        if confidence < config.get("min_confidence_threshold", 85):
                            continue
                        
                        # Check if signal type matches
                        allowed_signals = config.get("signal_types", [])
                        if allowed_signals and signal_type not in allowed_signals:
                            continue
                        
                        # Prepare alert message
                        hive_info = ""
                        if hive_data and hive_data.get("total_signals", 0) > 0:
                            hive_info = f"\n🐝 Hive Consensus: {hive_data.get('majority_signal')} ({hive_data.get('average_confidence'):.0f}% confidence from {hive_data.get('total_signals')} agents)"
                        
                        message = f"""🚨 Mineral AI Alert

Ticker: {ticker}
Signal: {signal_type}
Confidence: {confidence}/100
Recommendation: {recommendation}{hive_info}

This alert was triggered because the signal met your configured threshold.
"""
                        
                        # Send Telegram alert
                        if config.get("telegram_chat_id"):
                            try:
                                await send_telegram_alert(
                                    chat_id=config["telegram_chat_id"],
                                    message=message
                                )
                                logger.info(f"Sent Telegram alert for {ticker}")
                            except Exception as e:
                                logger.warning(f"Failed to send Telegram alert: {e}")
                        
                        # Send Discord alert
                        if config.get("discord_webhook_url"):
                            try:
                                await send_discord_alert(
                                    webhook_url=config["discord_webhook_url"],
                                    title=f"🚨 Alert: {ticker} - {signal_type}",
                                    description=message,
                                    signal_type=signal_type
                                )
                                logger.info(f"Sent Discord alert for {ticker}")
                            except Exception as e:
                                logger.warning(f"Failed to send Discord alert: {e}")
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"Failed to trigger sentinel alerts: {e}")
    
    def run_full_analysis(self, ticker: str, user_id: str, is_public: bool = False) -> Dict[str, Any]:
        """
        Wrapper method for Celery task - runs complete analysis pipeline (PRD v10.0 Phase 10.3)
        
        This wrapper is designed to be called from Celery workers to run the entire
        analysis pipeline in a synchronous context, handling exceptions and saving
        results to the database with user_id association.
        
        Args:
            ticker: Stock ticker symbol
            user_id: User UUID for data isolation
            is_public: Whether to share with Hive Mind
        
        Returns:
            Dict with analysis result including signal_id
        """
        import asyncio
        from scrapers.discovery import discover_news
        from scrapers.crawler import fetch_markdown
        from api.intelligence import load_system_settings_dict, save_signal_to_db, generate_signal_embedding
        
        try:
            logger.info(f"run_full_analysis: Starting for {ticker} (user_id: {user_id})")
            
            # Run in async context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    self._run_full_analysis_async(ticker, user_id, is_public)
                )
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"run_full_analysis failed for {ticker}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "ticker": ticker,
            }
    
    async def _run_full_analysis_async(self, ticker: str, user_id: str, is_public: bool) -> Dict[str, Any]:
        """Async helper for run_full_analysis wrapper"""
        from scrapers.discovery import discover_news
        from scrapers.crawler import fetch_markdown
        from api.intelligence import load_system_settings_dict, save_signal_to_db, generate_signal_embedding
        
        # Initialize components
        ollama = OllamaClient()
        sys_settings = load_system_settings_dict()
        
        # Step 1: Discovery
        logger.info(f"run_full_analysis: Discovery for {ticker}")
        articles = await discover_news(ticker)
        if not articles:
            raise Exception(f"No articles found for {ticker}")
        
        # Step 2: Crawl
        logger.info(f"run_full_analysis: Crawl for {ticker}")
        combined_text = ""
        for article in articles[:3]:
            try:
                text = await fetch_markdown(article["url"])
                combined_text += f"\n\n{article['title']}\n{text}"
            except Exception as e:
                logger.warning(f"Failed to crawl {article['url']}: {e}")
        
        if not combined_text:
            raise Exception(f"No content crawled for {ticker}")
        
        # Step 3: Run SLM orchestrator
        logger.info(f"run_full_analysis: SLM orchestrator for {ticker}")
        result = await self.analyze_discovery(
            raw_data=combined_text,
            source=f"celery:{ticker}",
            system_settings=sys_settings,
        )
        
        # Step 4: Save to database
        logger.info(f"run_full_analysis: Save to database for {ticker}")
        threshold = sys_settings.get("min_confidence_score", 85)
        if result.pydantic_passed and result.confidence_score >= threshold:
            embedding = await generate_signal_embedding(ollama, combined_text)
            signal_id = save_signal_to_db(
                result,
                asset_id=ticker,
                source=f"celery:{ticker}",
                user_id=user_id,
                embedding=embedding,
            )
            
            # Trigger Sentinel alerts
            await self._trigger_sentinel_alerts(
                signal_type=result.signal_type,
                confidence=result.confidence_score,
                recommendation=result.recommendation,
                ticker=ticker,
                hive_data={}
            )
        else:
            signal_id = None
        
        return {
            "status": "success",
            "signal_id": signal_id,
            "signal_type": result.signal_type,
            "confidence": result.confidence_score,
            "recommendation": result.recommendation,
        }
    
    async def analyze_discovery(
        self,
        raw_data: str,
        source: str,
        system_settings: Dict[str, Any]
    ) -> DebateResult:
        """
        Analyze a geological discovery using the debate protocol
        """
        logger.info(f"Starting debate protocol for discovery from {source}")
        self.debate_log = []
        
        # Step 1: Phi-3 (Data Extractor)
        try:
            phi3_result = await self._phi3_extract(raw_data, source)
            self.debate_log.append(phi3_result)
        except Exception as e:
            logger.error(f"Phi-3 extraction failed: {e}")
            return DebateResult(
                signal_type="HOLD",
                confidence_score=0,
                recommendation="Data extraction failed",
                debate_log=self.debate_log,
                consensus_score=0.0,
                pydantic_passed=False,
                pydantic_errors=[f"Phi-3 error: {str(e)}"]
            )
        
        # Step 2: Pydantic Firewall
        try:
            pydantic_result, pydantic_errors = self._pydantic_firewall(
                phi3_result.output_data,
                system_settings
            )
            if not pydantic_result:
                return DebateResult(
                    signal_type="HOLD",
                    confidence_score=0,
                    recommendation="Pydantic validation failed - data rejected",
                    debate_log=self.debate_log,
                    consensus_score=0.0,
                    pydantic_passed=False,
                    pydantic_errors=pydantic_errors
                )
        except Exception as e:
            logger.error(f"Pydantic validation failed: {e}")
            return DebateResult(
                signal_type="HOLD",
                confidence_score=0,
                recommendation=f"Pydantic error: {str(e)}",
                debate_log=self.debate_log,
                consensus_score=0.0,
                pydantic_passed=False,
                pydantic_errors=[str(e)]
            )
        
        # Sequential Mode breather: let the OS reclaim Phi-3's RAM before
        # loading Mistral (PRD v8.3 Sequential Memory-Optimized Mode).
        await asyncio.sleep(2)

        # Step 3: Mistral (Geologist Expert)
        try:
            mistral_result = await self._mistral_analyze(phi3_result.output_data)
            self.debate_log.append(mistral_result)
        except Exception as e:
            logger.error(f"Mistral analysis failed: {e}")
            mistral_result = DebateStep(
                slm=SLMMeta.MISTRAL,
                timestamp=self._get_timestamp(),
                input_data=phi3_result.output_data,
                output_data={"confidence": 50, "reasoning": "Analysis failed"},
                reasoning="Analysis failed",
                confidence=50
            )
        
        # Breather between Mistral and Llama-3 unloads.
        await asyncio.sleep(2)

        # Step 4: Llama-3 (Risk Manager)
        # PRD v8.7 Phase 9.5: feed Llama-3 a Data-Sovereignty prompt with
        # FMP fundamentals (HARD), Mistral verdict (TRUSTED) and the original
        # scrape (UNVERIFIED). The FMP fetch happens BEFORE Llama-3 is loaded
        # into RAM, preserving Sequential Memory Mode (`keep_alive=0`).
        try:
            llama3_result = await self._llama3_risk_check(
                phi3_data=phi3_result.output_data,
                mistral_step=mistral_result,
                raw_news_text=raw_data,
                system_settings=system_settings,
            )
            self.debate_log.append(llama3_result)
        except Exception as e:
            logger.error(f"Llama-3 risk check failed: {e}")
            llama3_result = DebateStep(
                slm=SLMMeta.LLAMA3,
                timestamp=self._get_timestamp(),
                input_data=phi3_result.output_data,
                output_data={"confidence": 50, "reasoning": "Risk check failed"},
                reasoning="Risk check failed",
                confidence=50
            )
        
        # Step 5: Consensus
        consensus_result = self._calculate_consensus(mistral_result, llama3_result)
        
        # Final decision
        if consensus_result["confidence"] >= system_settings.get("min_confidence_score", 85):
            signal_type = consensus_result["signal"]
        else:
            signal_type = "HOLD"
        
        # ------------------------------------------------------------------
        # Phase 10.2: The Sentinel - Alert Integration
        # ------------------------------------------------------------------
        # Trigger alerts if signal meets user's configured thresholds
        await self._trigger_sentinel_alerts(
            signal_type=signal_type,
            confidence=consensus_result["confidence"],
            recommendation=consensus_result["reasoning"],
            ticker=phi3_result.output_data.get("ticker", "UNKNOWN"),
            hive_data=hive_data if 'hive_data' in locals() else {}
        )
        
        return DebateResult(
            signal_type=signal_type,
            confidence_score=consensus_result["confidence"],
            recommendation=consensus_result["reasoning"],
            debate_log=self.debate_log,
            consensus_score=consensus_result["consensus_score"],
            pydantic_passed=True,
            pydantic_errors=[]
        )
    
    async def _phi3_extract(self, raw_data: str, source: str) -> DebateStep:
        """
        Step 1: Phi-3 extracts structured JSON from raw HTML/Markdown
        """
        logger.info("Step 1: Phi-3 data extraction")
        
        prompt = f"""Extract structured geological data from the following text. Return ONLY valid JSON.

Source: {source}

Text:
{raw_data}

Extract the following fields if present:
- ticker (stock symbol)
- commodity_type (e.g., copper, gold, lithium)
- copper_grade (percentage)
- gold_grade_g_t (g/ton)
- tonnage (millions of tons)
- resource_category (Inferred, Indicated, Measured, Reserve)
- country_code (2-letter ISO code)
- discovery_date (ISO 8601)
- company_name

Return JSON only, no explanation."""

        try:
            # Sequential Memory-Optimized Mode (PRD v8.3): load Phi-3,
            # answer, then unload from RAM via keep_alive=0.
            response = await self.ollama.generate_sequential(
                model=self.ollama.phi3_model,
                prompt=prompt,
            )

            # Parse JSON from response
            json_str = self._extract_json(response)
            extracted_data = json.loads(json_str) if json_str else {}

            return DebateStep(
                slm=SLMMeta.PHI3,
                timestamp=self._get_timestamp(),
                input_data={"raw_length": len(raw_data)},
                output_data=extracted_data,
                reasoning=f"Extracted {len(extracted_data)} fields from raw data",
                confidence=90
            )
        except Exception as e:
            logger.error(f"Phi-3 extraction error: {e}")
            raise
    
    def _pydantic_firewall(
        self,
        data: Dict[str, Any],
        system_settings: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        Step 2: Pydantic V2 validates data against physics and finance laws
        """
        logger.info("Step 2: Pydantic firewall validation")
        errors = []
        
        try:
            # Try to validate as GeologicalData
            geo_data = GeologicalData(
                discovery_id=data.get("discovery_id", "temp"),
                ticker=data.get("ticker"),
                commodity_type=data.get("commodity_type", "unknown"),
                copper_grade=data.get("copper_grade"),
                gold_grade_g_t=data.get("gold_grade_g_t"),
                tonnage=data.get("tonnage", 1.0),
                resource_category=data.get("resource_category", "inferred"),
                country_code=data.get("country_code", "XX"),
                discovery_date=data.get("discovery_date", "2024-01-01"),
                source=data.get("source", "unknown"),
                confidence_score=50
            )
            
            # Check against system thresholds
            max_grade = system_settings.get("max_geological_grade_copper", 15.0)
            if geo_data.copper_grade and geo_data.copper_grade > max_grade:
                errors.append(f"Copper grade {geo_data.copper_grade}% exceeds threshold {max_grade}%")
            
            return True, errors
            
        except Exception as e:
            errors.append(str(e))
            return False, errors
    
    async def _mistral_analyze(self, data: Dict[str, Any]) -> DebateStep:
        """
        Step 3: Mistral (Geology Expert) assesses geological quality
        """
        logger.info("Step 3: Mistral geology expert analysis")
        
        prompt = f"""You are a senior geologist with 30 years of experience in mineral exploration. Assess the following discovery data:

Data: {json.dumps(data, indent=2)}

Analyze:
1. Geological quality and feasibility
2. Resource category reliability
3. Jurisdiction risk (political stability)
4. Development timeline estimate

Provide:
- confidence (0-100)
- reasoning (detailed analysis)
- recommendation (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)

Return JSON only."""

        try:
            # Sequential Memory-Optimized Mode: load Mistral, answer, unload.
            response = await self.ollama.generate_sequential(
                model=self.ollama.mistral_model,
                prompt=prompt,
            )

            json_str = self._extract_json(response)
            result = json.loads(json_str) if json_str else {"confidence": 50, "reasoning": "Analysis failed"}

            return DebateStep(
                slm=SLMMeta.MISTRAL,
                timestamp=self._get_timestamp(),
                input_data=data,
                output_data=result,
                reasoning=result.get("reasoning", ""),
                confidence=result.get("confidence", 50)
            )
        except Exception as e:
            logger.error(f"Mistral analysis error: {e}")
            raise
    
    async def _llama3_risk_check(
        self,
        phi3_data: Dict[str, Any],
        mistral_step: Optional[DebateStep] = None,
        raw_news_text: str = "",
        system_settings: Optional[Dict[str, Any]] = None,
    ) -> DebateStep:
        """
        Step 4: Llama-3 (Risk & Portfolio Manager) - final BUY/SELL/PASS verdict.

        PRD v8.7 Phase 9.5 - XML-Tagged Structured Prompting w/ Data Sovereignty:
          <HARD_DETERMINISTIC_DATA>     FMP API fundamentals (immutable truth)
          <INTERNAL_EXPERT_CONSENSUS>   Mistral geologist verdict (trusted)
          <UNSTRUCTURED_MARKET_NOISE>   Raw scrape / press release (unverified)

        PRD v8.8 Phase 10 - Technical Timing Data:
          <TECHNICAL_TIMING_DATA>       SMA, RSI, MACD, Bollinger Bands (timing signals)

        The CRITICAL RULES OF ENGAGEMENT instruct Llama-3 to ALWAYS prefer
        the FMP block when it conflicts with the noise block (DATA SOVEREIGNTY).
        """
        logger.info("Step 4: Llama-3 risk manager (Data-Sovereignty + Technical Timing prompt)")

        # ------------------------------------------------------------------
        # Resolve ticker + fetch FMP fundamentals BEFORE loading Llama-3.
        # This guarantees the network round-trip is over by the time we call
        # generate_sequential() and Llama-3 is paged into RAM.
        # ------------------------------------------------------------------
        ticker = (
            (phi3_data.get("ticker") if isinstance(phi3_data, dict) else None)
            or (phi3_data.get("company_name") if isinstance(phi3_data, dict) else None)
            or "UNKNOWN"
        )
        ticker = str(ticker).upper().strip()

        fmp_data: Dict[str, Any] = {}
        if ticker and ticker != "UNKNOWN":
            try:
                fmp_data = await fetch_fmp_fundamentals(
                    ticker=ticker,
                    system_settings=system_settings,
                )
                if fmp_data:
                    logger.info(f"📊 FMP fundamentals loaded for {ticker}: "
                                f"P/E={fmp_data.get('pe_ratio')}, "
                                f"MCap={fmp_data.get('market_cap')}")
                else:
                    logger.warning(f"FMP returned no data for {ticker}")
            except httpx.HTTPStatusError as e:
                # Phase 9.9: Graceful degradation - log but continue on 429/500 errors
                if e.response.status_code in [429, 500, 502, 503, 504]:
                    logger.warning(f"FMP rate limited or unavailable for {ticker} (continuing without): {e}")
                    fmp_data = {}
                else:
                    raise
            except httpx.TimeoutException:
                # Phase 9.9: Graceful degradation - log but continue on timeout
                logger.warning(f"FMP timeout for {ticker} (continuing without)")
                fmp_data = {}
            except Exception as e:
                logger.warning(f"FMP fetch error for {ticker} (continuing without): {e}")
                fmp_data = {}

        # ------------------------------------------------------------------
        # Fetch Technical Analysis (Phase 10)
        # ------------------------------------------------------------------
        ta_data: Dict[str, Any] = {}
        if ticker and ticker != "UNKNOWN":
            try:
                ta_data = await self._fetch_technical_analysis(ticker)
            except httpx.HTTPStatusError as e:
                # Phase 9.9: Graceful degradation - log but continue on 429/500 errors
                if e.response.status_code in [429, 500, 502, 503, 504]:
                    logger.warning(f"Technical analysis rate limited or unavailable for {ticker} (continuing without): {e}")
                    ta_data = {}
                else:
                    raise
            except httpx.TimeoutException:
                # Phase 9.9: Graceful degradation - log but continue on timeout
                logger.warning(f"Technical analysis timeout for {ticker} (continuing without)")
                ta_data = {}
            except Exception as e:
                logger.warning(f"Technical analysis error for {ticker} (continuing without): {e}")
                ta_data = {}

        # ------------------------------------------------------------------
        # Fetch Hive Mind Consensus (Phase 10.2)
        # ------------------------------------------------------------------
        hive_data: Dict[str, Any] = {}
        if ticker and ticker != "UNKNOWN":
            try:
                hive_data = await self._fetch_hive_consensus(ticker)
                if hive_data and hive_data.get("total_signals", 0) > 0:
                    logger.info(f"🐝 Hive consensus loaded for {ticker}: "
                                f"{hive_data.get('total_signals')} signals, "
                                f"avg_conf={hive_data.get('average_confidence')}, "
                                f"majority={hive_data.get('majority_signal')}")
            except Exception as e:
                logger.warning(f"Hive consensus fetch error for {ticker} (continuing without): {e}")
                hive_data = {}

        # ------------------------------------------------------------------
        # Fetch Historical RAG Context (Phase 12)
        # ------------------------------------------------------------------
        rag_data: Dict[str, Any] = {}
        if ticker and ticker != "UNKNOWN":
            try:
                rag_data = await self.rag_engine.get_production_targets_context(ticker)
                if rag_data and rag_data.get("total", 0) > 0:
                    logger.info(f"📚 RAG context loaded for {ticker}: "
                                f"{rag_data.get('total')} historical chunks found")
            except Exception as e:
                logger.warning(f"RAG context fetch error for {ticker} (continuing without): {e}")
                rag_data = {}

        max_pe = (system_settings or {}).get("max_pe_ratio", 25)

        # ------------------------------------------------------------------
        # Build the three sovereignty blocks + technical timing block.
        # ------------------------------------------------------------------
        hard_block = format_fmp_for_prompt(fmp_data)
        mistral_verdict = (
            (mistral_step.reasoning if mistral_step and mistral_step.reasoning else None)
            or "[Mistral consensus unavailable]"
        )
        # Llama-3 still needs concise noise; cap to ~1.5k chars to keep prompt small.
        noise_text = (raw_news_text or "[no scraped text supplied]").strip()
        if len(noise_text) > 1500:
            noise_text = noise_text[:1500] + "\n... [truncated]"

        # Format technical timing data
        ta_block = ""
        if ta_data:
            ta_block = f"""RSI: {ta_data.get('rsi', 'N/A')}
SMA 50: {ta_data.get('sma_50', 'N/A')}
SMA 200: {ta_data.get('sma_200', 'N/A')}
MACD: {ta_data.get('macd', 'N/A')}
MACD Signal: {ta_data.get('macd_signal', 'N/A')}
Bollinger Upper: {ta_data.get('bb_upper', 'N/A')}
Bollinger Lower: {ta_data.get('bb_lower', 'N/A')}
Current Price: {ta_data.get('current_price', 'N/A')}
Interpretation: {ta_data.get('interpretation', 'N/A')}"""
        else:
            ta_block = "[Technical analysis unavailable - proceeding without timing signals]"

        # Format hive mind consensus block
        hive_block = ""
        if hive_data and hive_data.get("total_signals", 0) > 0:
            hive_block = f"""Total recent analyses by other agents: {hive_data.get('total_signals')}
Average Crowd Confidence: {hive_data.get('average_confidence')}
Majority Crowd Signal: {hive_data.get('majority_signal')}"""
        else:
            hive_block = "[No Hive Mind consensus available - proceeding without swarm intelligence]"

        # Format historical RAG context block (Phase 12)
        rag_block = ""
        if rag_data and rag_data.get("total", 0) > 0:
            rag_chunks = rag_data.get("chunks", [])
            rag_content = ""
            for chunk in rag_chunks:
                rag_content += f"""
Date: {chunk.get('published_date', 'N/A')}
Source: {chunk.get('document_type', 'N/A')}
Title: {chunk.get('title', 'N/A')}
Content: {chunk.get('content', '')[:500]}...
Similarity: {chunk.get('similarity', 0):.2f}
---"""
            rag_block = f"""Historical Statements from Earnings Calls/SEC Filings:
{rag_content}"""
        else:
            rag_block = "[No historical context available - proceeding without RAG]"

        prompt = f"""You are the Lead Risk & Portfolio Manager for an elite Quantitative Hedge Fund.
Your task is to evaluate an investment opportunity and make a final execution decision (BUY, SELL, or PASS) with a Confidence Score (0-100).

<HARD_DETERMINISTIC_DATA>
[SOURCE: FMP Institutional API - ABSOLUTE TRUTH]
{hard_block}
</HARD_DETERMINISTIC_DATA>

<INTERNAL_EXPERT_CONSENSUS>
[SOURCE: Mistral Domain Expert - TRUSTED ANALYSIS]
{mistral_verdict}
</INTERNAL_EXPERT_CONSENSUS>

<UNSTRUCTURED_MARKET_NOISE>
[SOURCE: Web Scrape / Press Release - UNVERIFIED]
{noise_text}
</UNSTRUCTURED_MARKET_NOISE>

<TECHNICAL_TIMING_DATA>
[SOURCE: Technical Analysis Engine - TIMING SIGNALS]
{ta_block}
</TECHNICAL_TIMING_DATA>

<HIVE_MIND_CONSENSUS>
[SOURCE: Swarm Intelligence - CROWD WISDOM]
{hive_block}
</HIVE_MIND_CONSENSUS>

<HISTORICAL_RAG_CONTEXT>
[SOURCE: Historical Earnings Calls / SEC Filings - EXECUTIVE PROMISES TRACKING]
{rag_block}
</HISTORICAL_RAG_CONTEXT>

CRITICAL RULES OF ENGAGEMENT:
1. DATA SOVEREIGNTY: The numbers in <HARD_DETERMINISTIC_DATA> are immutable facts. If the <UNSTRUCTURED_MARKET_NOISE> claims a different valuation, P/E, or financial metric, you MUST ignore the noise and use the HARD DATA. If the noise contradicts the HARD DATA, explicitly call out the discrepancy in your reasoning.
2. RISK FILTERING: If the Forward P/E in HARD DATA is above our threshold (>{max_pe}) AND Free Cash Flow Margin is negative or near-zero, you must severely penalize the Confidence Score, regardless of how positive the news or the Geologist is.
3. MACRO AWARENESS: Factor in the current macro environment (Strong DXY penalizes commodities; high US10Y penalizes growth multiples).
4. TECHNICAL TIMING (NEW): Use <TECHNICAL_TIMING_DATA> to adjust your entry timing:
   - If fundamentals are STRONG but RSI > 75 (Overbought), recommend a smaller entry position or PASS until a pullback.
   - If fundamentals are STRONG and RSI < 30 (Oversold) AND MACD is bullish, INCREASE your confidence and consider a larger entry position.
   - If price is at/above upper Bollinger Band, be cautious - the move may be overextended.
   - If price is at/below lower Bollinger Band, this may be an attractive entry point if fundamentals support it.
5. HIVE MIND CONSIDERATION (NEW): Consider the <HIVE_MIND_CONSENSUS>. If your independent analysis drastically opposes the swarm, double-check your data, but always trust <HARD_DETERMINISTIC_DATA> over the crowd. The crowd can be wrong, but strong consensus (>80% confidence, >5 signals) should be a factor in your decision.
6. HISTORICAL CONSISTENCY CHECK (NEW): CRITICAL - Compare current management statements in <UNSTRUCTURED_MARKET_NOISE> against <HISTORICAL_RAG_CONTEXT>. If executives made similar promises in the past that were NOT delivered, this is a RED FLAG and you MUST lower confidence. If they have a track record of delivering on promises, this is a GREEN FLAG and you may increase confidence.
7. NEVER fabricate data. If a HARD DATA field is "N/A" you must say so and lower your confidence accordingly.

Based on the above, return JSON ONLY in this exact shape (no prose outside the braces):
{{
  "recommendation": "BUY" | "SELL" | "PASS",
  "confidence": 0-100,
  "reasoning": "<= 4 sentences explaining the decision, citing HARD DATA fields, technical timing, hive consensus, historical consistency, and any noise contradiction>",
  "data_conflicts": ["<list of specific conflicts between HARD DATA and NOISE, or empty list>"]
}}"""

        try:
            # Sequential Memory-Optimized Mode: load Llama-3, answer, unload.
            response = await self.ollama.generate_sequential(
                model=self.ollama.llama3_model,
                prompt=prompt,
            )

            json_str = self._extract_json(response)
            result = json.loads(json_str) if json_str else {
                "confidence": 50,
                "reasoning": "Risk check failed - could not parse Llama-3 JSON",
                "recommendation": "PASS",
                "data_conflicts": [],
            }

            # Persist the FMP block and TA block so /debate/{asset_id} can show what
            # ground-truth fundamentals and timing signals Llama-3 actually saw.
            input_blob = {
                "phi3": phi3_data,
                "fmp": fmp_data,
                "technical_analysis": ta_data,
                "mistral_summary": mistral_verdict[:500],
                "ticker": ticker,
            }

            return DebateStep(
                slm=SLMMeta.LLAMA3,
                timestamp=self._get_timestamp(),
                input_data=input_blob,
                output_data=result,
                reasoning=result.get("reasoning", ""),
                confidence=int(result.get("confidence", 50)),
            )
        except Exception as e:
            logger.error(f"Llama-3 risk check error: {e}")
            raise
    
    def _calculate_consensus(
        self,
        mistral_result: DebateStep,
        llama3_result: DebateStep
    ) -> Dict[str, Any]:
        """
        Step 5: Calculate consensus between Expert and Risk Manager
        """
        logger.info("Step 5: Calculating consensus")
        
        mistral_conf = mistral_result.confidence
        llama3_conf = llama3_result.confidence
        
        # Calculate agreement (0-1)
        diff = abs(mistral_conf - llama3_conf)
        consensus_score = max(0, 1 - (diff / 100))
        
        # Weighted confidence (lower if they disagree)
        final_confidence = int((mistral_conf + llama3_conf) / 2 * consensus_score)
        
        # Determine signal
        if final_confidence >= 85:
            signal = "BUY"
            reasoning = f"Strong consensus ({consensus_score:.2f}) between geologist and risk manager"
        elif final_confidence >= 70:
            signal = "HOLD"
            reasoning = f"Moderate consensus ({consensus_score:.2f}), requires more analysis"
        else:
            signal = "HOLD"
            reasoning = f"Low consensus ({consensus_score:.2f}), high risk detected"
        
        return {
            "signal": signal,
            "confidence": final_confidence,
            "reasoning": reasoning,
            "consensus_score": consensus_score
        }
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from LLM response"""
        try:
            # Find JSON between ```json and ``` or { and }
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return text[start:end]
            return None
        except Exception:
            return None
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
