"""
Mineral AI Tracker - Technical Analysis Engine (PRD v8.8 Phase 10)
Version: 8.8
Description: Calculates technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands)
using pandas-ta to provide timing signals for Llama-3 risk analysis.

This engine transforms raw OHLCV data into structured "Technical Timing Data"
that Llama-3 can use to adjust position sizing and entry timing.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from loguru import logger

try:
    import pandas_ta as ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    logger.warning("pandas-ta not installed - technical analysis will be disabled")


class TechnicalAnalyzer:
    """
    Technical Analysis Engine using pandas-ta

    Calculates standard technical indicators and provides structured
    interpretations for AI decision-making.
    """

    def __init__(self, min_periods: int = 50):
        """
        Initialize the technical analyzer

        Args:
            min_periods: Minimum number of periods required for calculations
        """
        self.min_periods = min_periods

    def analyze_ticker(self, ohlcv_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze ticker using technical indicators

        Args:
            ohlcv_data: List of OHLCV dictionaries with keys:
                        - date: str (ISO format)
                        - open: float
                        - high: float
                        - low: float
                        - close: float
                        - volume: float (optional)

        Returns:
            Dictionary with technical indicators and structured interpretation
        """
        if not TA_AVAILABLE:
            return self._empty_result("pandas-ta not installed")

        if len(ohlcv_data) < self.min_periods:
            return self._empty_result(f"Insufficient data (need {self.min_periods} periods, got {len(ohlcv_data)})")

        try:
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')

            # Ensure numeric types
            for col in ['open', 'high', 'low', 'close']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            if df['close'].isna().all():
                return self._empty_result("No valid price data")

            # Calculate indicators
            result = self._calculate_indicators(df)

            # Add interpretation
            result['interpretation'] = self._interpret_indicators(result)

            return result

        except Exception as e:
            logger.error(f"Technical analysis failed: {e}")
            return self._empty_result(f"Error: {str(e)}")

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all technical indicators"""
        result = {}

        # SMA (Simple Moving Average)
        result['sma_50'] = ta.sma(df['close'], length=50).iloc[-1] if len(df) >= 50 else None
        result['sma_200'] = ta.sma(df['close'], length=200).iloc[-1] if len(df) >= 200 else None

        # EMA (Exponential Moving Average)
        result['ema_12'] = ta.ema(df['close'], length=12).iloc[-1] if len(df) >= 12 else None
        result['ema_26'] = ta.ema(df['close'], length=26).iloc[-1] if len(df) >= 26 else None

        # RSI (Relative Strength Index)
        rsi_series = ta.rsi(df['close'], length=14)
        result['rsi'] = rsi_series.iloc[-1] if rsi_series is not None and len(rsi_series) > 0 else None

        # MACD (Moving Average Convergence Divergence)
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        if macd is not None:
            result['macd'] = macd['MACD_12_26_9'].iloc[-1] if 'MACD_12_26_9' in macd else None
            result['macd_signal'] = macd['MACDs_12_26_9'].iloc[-1] if 'MACDs_12_26_9' in macd else None
            result['macd_histogram'] = macd['MACDh_12_26_9'].iloc[-1] if 'MACDh_12_26_9' in macd else None
        else:
            result['macd'] = None
            result['macd_signal'] = None
            result['macd_histogram'] = None

        # Bollinger Bands
        bb = ta.bbands(df['close'], length=20, std=2)
        if bb is not None:
            result['bb_upper'] = bb['BBU_20_2.0'].iloc[-1] if 'BBU_20_2.0' in bb else None
            result['bb_middle'] = bb['BBM_20_2.0'].iloc[-1] if 'BBM_20_2.0' in bb else None
            result['bb_lower'] = bb['BBL_20_2.0'].iloc[-1] if 'BBL_20_2.0' in bb else None
        else:
            result['bb_upper'] = None
            result['bb_middle'] = None
            result['bb_lower'] = None

        # Current price
        result['current_price'] = df['close'].iloc[-1]

        return result

    def _interpret_indicators(self, indicators: Dict[str, Any]) -> str:
        """Generate human-readable interpretation of indicators"""
        interpretations = []

        # RSI interpretation
        rsi = indicators.get('rsi')
        if rsi is not None:
            if rsi > 70:
                interpretations.append(f"RSI is {rsi:.1f} (OVERBOUGHT - consider waiting for pullback)")
            elif rsi < 30:
                interpretations.append(f"RSI is {rsi:.1f} (OVERSOLD - potential entry opportunity)")
            else:
                interpretations.append(f"RSI is {rsi:.1f} (neutral)")

        # MACD interpretation
        macd = indicators.get('macd')
        macd_signal = indicators.get('macd_signal')
        if macd is not None and macd_signal is not None:
            if macd > macd_signal:
                interpretations.append("MACD is BULLISH (above signal line)")
            else:
                interpretations.append("MACD is BEARISH (below signal line)")

            if indicators.get('macd_histogram') is not None:
                hist = indicators['macd_histogram']
                if hist > 0:
                    interpretations.append("MACD histogram is positive (momentum strengthening)")
                else:
                    interpretations.append("MACD histogram is negative (momentum weakening)")

        # SMA Golden Cross / Death Cross
        sma_50 = indicators.get('sma_50')
        sma_200 = indicators.get('sma_200')
        if sma_50 is not None and sma_200 is not None:
            if sma_50 > sma_200:
                interpretations.append("SMA 50 > SMA 200 (GOLDEN CROSS - bullish trend)")
            else:
                interpretations.append("SMA 50 < SMA 200 (DEATH CROSS - bearish trend)")

        # Bollinger Bands interpretation
        price = indicators.get('current_price')
        bb_upper = indicators.get('bb_upper')
        bb_lower = indicators.get('bb_lower')
        if price is not None and bb_upper is not None and bb_lower is not None:
            if price >= bb_upper:
                interpretations.append("Price is at/above upper Bollinger Band (overextended)")
            elif price <= bb_lower:
                interpretations.append("Price is at/below lower Bollinger Band (oversold)")
            else:
                interpretations.append("Price is within Bollinger Bands (normal range)")

        return "\n".join(interpretations) if interpretations else "Insufficient data for interpretation"

    def _empty_result(self, reason: str) -> Dict[str, Any]:
        """Return empty result with reason"""
        return {
            'sma_50': None,
            'sma_200': None,
            'ema_12': None,
            'ema_26': None,
            'rsi': None,
            'macd': None,
            'macd_signal': None,
            'macd_histogram': None,
            'bb_upper': None,
            'bb_middle': None,
            'bb_lower': None,
            'current_price': None,
            'interpretation': f"[TECHNICAL ANALYSIS UNAVAILABLE: {reason}]"
        }


# Singleton instance
default_technical_analyzer = TechnicalAnalyzer()


__all__ = [
    "TechnicalAnalyzer",
    "default_technical_analyzer",
]
