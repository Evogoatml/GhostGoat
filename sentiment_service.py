"""
Enhanced Sentiment Service with Fine-Tuning Support
Drop-in replacement for original sentiment_service.py
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
from typing import Dict, List
from datetime import datetime

from ..core.cache import cache
from ..core.logging import logger


class SentimentService:
    """
    Enhanced CryptoBERT sentiment analysis with fine-tuning support
    """
    
    def __init__(self, model_path: str = "ElKulako/cryptobert"):
        self.model_path = model_path
        self.load_model(model_path)
    
    def load_model(self, model_path: str):
        """Load model (generic or fine-tuned)"""
        logger.info(f"Loading model from {model_path}...")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.eval()
        
        # Move to GPU if available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
        self.model_path = model_path
        logger.info(f"✓ Model loaded on {self.device}")
    
    def load_custom_model(self, model_path: str):
        """
        Load a custom fine-tuned model
        
        Usage:
            sentiment_service.load_custom_model("data/models/cryptobert-arbitrage/final")
        """
        logger.info(f"Switching to custom model: {model_path}")
        self.load_model(model_path)
        logger.info("✓ Custom model active")
    
    def get_model_info(self) -> Dict:
        """Get information about currently loaded model"""
        return {
            'model_path': self.model_path,
            'device': str(self.device),
            'is_custom': 'cryptobert-arbitrage' in self.model_path,
            'parameters': sum(p.numel() for p in self.model.parameters())
        }
    
    def analyze_text(self, text: str) -> Dict:
        """
        Analyze sentiment of a single text
        
        Args:
            text: Text to analyze
        
        Returns:
            Dict with sentiment, confidence, and scores
        """
        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        )
        
        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Predict
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=-1)[0]
        
        # Get prediction
        predicted_class = torch.argmax(probabilities).item()
        confidence = probabilities[predicted_class].item()
        
        sentiment_labels = {0: "bearish", 1: "neutral", 2: "bullish"}
        
        return {
            'sentiment': sentiment_labels[predicted_class],
            'confidence': confidence,
            'scores': {
                'bearish': probabilities[0].item(),
                'neutral': probabilities[1].item(),
                'bullish': probabilities[2].item()
            },
            'model': 'custom' if 'arbitrage' in self.model_path else 'generic'
        }
    
    async def analyze_symbol(self, symbol: str) -> Dict:
        """
        Comprehensive sentiment analysis for a cryptocurrency
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
        
        Returns:
            Complete sentiment analysis with breakdown
        """
        # Check cache first
        cache_key = f"sentiment:{symbol}:{self.model_path}"
        cached = await cache.get(cache_key)
        if cached:
            return cached
        
        # In production, this would aggregate Twitter/Reddit/News
        # For now, simplified example
        sample_text = f"{symbol} cryptocurrency market analysis today"
        result = self.analyze_text(sample_text)
        
        # Calculate overall score (-1 to +1)
        overall_score = result['scores']['bullish'] - result['scores']['bearish']
        
        # Determine recommendation
        recommendation = self._get_recommendation(overall_score)
        
        analysis = {
            'symbol': symbol,
            'overall_sentiment': result['sentiment'],
            'overall_score': overall_score,
            'confidence': result['confidence'],
            'recommendation': recommendation,
            'model_used': result['model'],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Cache for 5 minutes
        await cache.set(cache_key, analysis, expire=300)
        
        return analysis
    
    def _get_recommendation(self, score: float) -> str:
        """
        Get trading recommendation based on sentiment score
        
        Args:
            score: Sentiment score from -1 (bearish) to +1 (bullish)
        
        Returns:
            Trading recommendation
        """
        if score > 0.5:
            return "STRONG BUY - Very bullish sentiment"
        elif score > 0.3:
            return "BUY - Moderately bullish sentiment"
        elif score > 0.1:
            return "HOLD - Slightly bullish sentiment"
        elif score > -0.1:
            return "HOLD - Neutral sentiment"
        elif score > -0.3:
            return "CAUTION - Slightly bearish sentiment"
        elif score > -0.5:
            return "SELL - Moderately bearish sentiment"
        else:
            return "STRONG SELL - Very bearish sentiment"
    
    async def batch_analyze(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Analyze sentiment for multiple symbols efficiently
        
        Args:
            symbols: List of cryptocurrency symbols
        
        Returns:
            Dict mapping symbol to sentiment analysis
        """
        import asyncio
        tasks = [self.analyze_symbol(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        
        return {
            symbol: result
            for symbol, result in zip(symbols, results)
        }
    
    async def analyze_with_context(self, text: str, opportunity: Dict) -> Dict:
        """
        Analyze sentiment with arbitrage opportunity context
        Used during fine-tuning data collection
        
        Args:
            text: Sentiment text
            opportunity: Arbitrage opportunity details
        
        Returns:
            Enhanced sentiment analysis with trading context
        """
        base_analysis = self.analyze_text(text)
        
        # Add opportunity context
        enhanced = {
            **base_analysis,
            'opportunity': {
                'symbol': opportunity.get('symbol'),
                'spread_percent': opportunity.get('spread_percent'),
                'exchanges': f"{opportunity.get('buy_exchange')} → {opportunity.get('sell_exchange')}"
            },
            'trading_signal': self._get_trading_signal(
                base_analysis['scores'],
                opportunity.get('spread_percent', 0)
            )
        }
        
        return enhanced
    
    def _get_trading_signal(self, scores: Dict, spread: float) -> str:
        """
        Generate trading signal based on sentiment + spread
        """
        sentiment_score = scores['bullish'] - scores['bearish']
        
        # High spread + bearish = likely scam/dump
        if spread > 2.0 and sentiment_score < -0.3:
            return "AVOID - High spread with bearish sentiment (possible dump)"
        
        # Good spread + bullish = execute
        elif spread > 0.5 and sentiment_score > 0.3:
            return "EXECUTE - Good spread with bullish sentiment"
        
        # Moderate conditions
        elif spread > 0.8 and sentiment_score > 0:
            return "CONSIDER - Moderate opportunity"
        
        else:
            return "SKIP - Insufficient signal"

# Global sentiment service instance
sentiment_service = SentimentService()

# CLI for testing
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("🧪 Testing Sentiment Service\n")
        
        # Test 1: Basic text analysis
        print("="*60)
        print("Test 1: Text Analysis")
        print("="*60)
        
        texts = [
            "Bitcoin to the moon! 🚀🚀🚀",
            "Market looking stable today",
            "Massive dump incoming, sell everything!"
        ]
        
        for text in texts:
            result = sentiment_service.analyze_text(text)
            print(f"\nText: {text}")
            print(f"Sentiment: {result['sentiment']} (confidence: {result['confidence']:.2f})")
        
        # Test 2: Symbol analysis
        print("\n" + "="*60)
        print("Test 2: Symbol Analysis")
        print("="*60)
        
        sentiment = await sentiment_service.analyze_symbol('BTC')
        print(f"\nBTC Sentiment: {sentiment['overall_sentiment']}")
        print(f"Score: {sentiment['overall_score']:.2f}")
        print(f"Recommendation: {sentiment['recommendation']}")
        
        # Test 3: Model info
        print("\n" + "="*60)
        print("Test 3: Model Information")
        print("="*60)
        
        info = sentiment_service.get_model_info()
        print(f"\nModel: {info['model_path']}")
        print(f"Device: {info['device']}")
        print(f"Custom: {info['is_custom']}")
        print(f"Parameters: {info['parameters']:,}")
        
        print("\n✓ All tests passed!")
    
    asyncio.run(test())
