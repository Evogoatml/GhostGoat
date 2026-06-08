#!/usr/bin/env python3
"""
Test integration of all components
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from src.core.config import settings
        print("✓ Config imported")
    except Exception as e:
        print(f"✗ Config import failed: {e}")
        return False
    
    try:
        from src.core.database import engine, Base
        print("✓ Database imported")
    except Exception as e:
        print(f"✗ Database import failed: {e}")
        return False
        
    try:
        from src.core.cache import cache
        print("✓ Cache imported")
    except Exception as e:
        print(f"✗ Cache import failed: {e}")
        return False
    
    try:
        from src.services.exchange_connector import ExchangeConnector, CCXTConnector, ExchangeFactory
        print("✓ Exchange connector imported")
    except Exception as e:
        print(f"✗ Exchange connector import failed: {e}")
        return False
    
    try:
        from src.services.price_matrix import PriceMatrix, ArbitrageOpportunity
        print("✓ Price matrix imported")
    except Exception as e:
        print(f"✗ Price matrix import failed: {e}")
        return False
    
    try:
        from src.services.scanner_service import ScannerService
        print("✓ Scanner service imported")
    except Exception as e:
        print(f"✗ Scanner service import failed: {e}")
        return False
    
    try:
        from src.services.sentiment.service import CryptoBERTSentimentService
        print("✓ Sentiment service imported")
    except Exception as e:
        print(f"✗ Sentiment service import failed: {e}")
        return False
    
    try:
        from src.main import app
        print("✓ Main app imported")
    except Exception as e:
        print(f"✗ Main app import failed: {e}")
        return False
    
    try:
        from src.api.v1.sentiment import router
        print("✓ Sentiment API imported")
    except Exception as e:
        print(f"✗ Sentiment API import failed: {e}")
        return False
        
    return True

async def test_sentiment_analysis():
    """Test sentiment analysis functionality"""
    print("\nTesting sentiment analysis...")
    
    try:
        from src.services.sentiment.service import CryptoBERTSentimentService
        
        # Initialize service
        service = CryptoBERTSentimentService()
        print("✓ Sentiment service initialized")
        
        # Test text analysis (doesn't require API keys)
        result = service.analyze_text("Bitcoin is going to the moon! 🚀")
        print(f"✓ Text analysis works: {result['sentiment']} (confidence: {result['confidence']:.2f})")
        
        return True
    except Exception as e:
        print(f"✗ Sentiment analysis test failed: {e}")
        return False

async def test_price_matrix():
    """Test price matrix functionality"""
    print("\nTesting price matrix...")
    
    try:
        from src.services.price_matrix import PriceMatrix, ArbitrageOpportunity
        import numpy as np
        
        # Create price matrix
        exchanges = ['binance', 'kraken', 'coinbase']
        fees = {'binance': 0.001, 'kraken': 0.002, 'coinbase': 0.005}
        matrix = PriceMatrix(exchanges, fees)
        print("✓ Price matrix created")
        
        # Update prices
        matrix.update('binance', 43500.0, 43510.0, 1.5, 2.0, 1000000)
        matrix.update('kraken', 43520.0, 43530.0, 0.8, 1.2, 1000000)
        matrix.update('coinbase', 43490.0, 43500.0, 2.0, 1.0, 1000000)
        print("✓ Prices updated")
        
        # Check for arbitrage
        opportunity = matrix.find_arbitrage('BTC/USDT', min_spread_bps=10)
        if opportunity:
            print(f"✓ Arbitrage detected: {opportunity.buy_exchange} → {opportunity.sell_exchange} "
                  f"({opportunity.spread_bps:.2f} bps)")
        else:
            print("○ No arbitrage found (expected with these prices)")
        
        return True
    except Exception as e:
        print(f"✗ Price matrix test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("=" * 60)
    print("Arbitrage Pro Integration Test")
    print("=" * 60)
    
    # Test imports
    imports_ok = await test_imports()
    
    # Test sentiment analysis
    sentiment_ok = await test_sentiment_analysis()
    
    # Test price matrix
    matrix_ok = await test_price_matrix()
    
    print("\n" + "=" * 60)
    if imports_ok and sentiment_ok and matrix_ok:
        print("✅ All tests passed!")
        print("\nThe system is ready to run. To start:")
        print("1. Configure .env file with your API keys")
        print("2. Run: docker-compose up -d postgres redis")
        print("3. Run: make dev")
        return True
    else:
        print("❌ Some tests failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)