#!/usr/bin/env python3
"""
Unified System Demo
Demonstrates the unified configuration, integration, and API gateway
"""

import asyncio
import logging
from unified_config import UnifiedConfig, init_config
from unified_integration import UnifiedIntegrationLayer, SystemType
from unified_api_gateway import UnifiedAPIGateway
from monitoring import get_monitoring

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_configuration():
    """Demonstrate unified configuration"""
    print("\n" + "="*60)
    print("1. UNIFIED CONFIGURATION DEMO")
    print("="*60)
    
    # Load configuration
    config = init_config()
    
    print(f"\n✓ Configuration loaded")
    print(f"  LLM Provider: {config.llm.provider.value}")
    print(f"  LLM Model: {config.llm.model}")
    print(f"  Memory Backend: {config.memory.backend.value}")
    print(f"  Memory Path: {config.memory.path}")
    print(f"  Agent Name: {config.agent.name}")
    print(f"  Base Path: {config.base_path}")
    
    # Validate
    is_valid, errors = config.validate()
    if is_valid:
        print("\n✓ Configuration is valid")
    else:
        print(f"\n⚠ Configuration has errors: {errors}")
    
    # Save config
    config_path = "~/.ghostgoat/config.json"
    config.save(config_path)
    print(f"\n✓ Configuration saved to {config_path}")


async def demo_integration():
    """Demonstrate unified integration"""
    print("\n" + "="*60)
    print("2. UNIFIED INTEGRATION DEMO")
    print("="*60)
    
    config = init_config()
    integration = UnifiedIntegrationLayer(config)
    
    # Initialize systems (use mock/available systems)
    print("\nInitializing systems...")
    await integration.initialize([
        SystemType.ORCHESTRATOR,  # Most likely to work
    ])
    
    # Get status
    status = await integration.get_all_status()
    print(f"\n✓ System Status:")
    for system, sys_status in status.items():
        print(f"  {system}: {sys_status.get('status', 'unknown')}")
    
    # Execute a simple task
    print("\nExecuting test task...")
    result = await integration.execute_task(
        description="List available systems",
        system=SystemType.ORCHESTRATOR,
        priority=5
    )
    
    print(f"\n✓ Task Result:")
    print(f"  Success: {result.success}")
    print(f"  Execution Time: {result.execution_time:.2f}s")
    if result.error:
        print(f"  Error: {result.error}")


async def demo_memory():
    """Demonstrate unified memory"""
    print("\n" + "="*60)
    print("3. UNIFIED MEMORY DEMO")
    print("="*60)
    
    from unified_memory import create_memory
    from unified_config import get_config
    
    config = get_config()
    memory = create_memory(config.memory)
    
    # Store memory
    print("\nStoring memories...")
    id1 = await memory.store("Python is a programming language", {"type": "fact"})
    id2 = await memory.store("GhostGoat is an AI orchestrator", {"type": "system"})
    print(f"✓ Stored 2 memories")
    
    # Retrieve memory
    print("\nRetrieving memories...")
    results = await memory.retrieve("AI system", top_k=2)
    print(f"✓ Retrieved {len(results)} memories")
    for item in results:
        print(f"  - {item.content[:50]}...")
    
    # Get stats
    stats = await memory.get_stats()
    print(f"\n✓ Memory Stats: {stats}")


async def demo_monitoring():
    """Demonstrate monitoring"""
    print("\n" + "="*60)
    print("4. MONITORING DEMO")
    print("="*60)
    
    monitoring = get_monitoring()
    
    # Record some metrics
    print("\nRecording metrics...")
    monitoring.metrics.increment("tasks_started")
    monitoring.metrics.gauge("active_agents", 3)
    monitoring.metrics.timer("task_duration", 1.5)
    print("✓ Recorded metrics")
    
    # Get summary
    summary = monitoring.metrics.get_summary()
    print(f"\n✓ Metrics Summary:")
    print(f"  Total Metrics: {summary['total_metrics']}")
    print(f"  Counters: {summary['counters']}")
    print(f"  Gauges: {summary['gauges']}")
    
    # Health checks
    print("\nRunning health checks...")
    async def dummy_check():
        return {"status": "healthy", "message": "System OK"}
    
    monitoring.health.register_check("test_component", dummy_check)
    health = await monitoring.health.check("test_component")
    print(f"✓ Health Check: {health.status} - {health.message}")


async def demo_api_gateway():
    """Demonstrate API gateway"""
    print("\n" + "="*60)
    print("5. API GATEWAY DEMO")
    print("="*60)
    
    config = init_config()
    gateway = UnifiedAPIGateway(config)
    await gateway.initialize()
    
    # Get status
    print("\nGetting system status...")
    status = await gateway.get_status()
    print(f"✓ Status retrieved")
    print(f"  Systems: {len(status.get('systems', {}))}")
    print(f"  Health Checks: {len(status.get('health', {}))}")
    
    # Get metrics
    print("\nGetting metrics...")
    metrics = await gateway.get_metrics()
    print(f"✓ Metrics retrieved")
    print(f"  Available metrics: {list(metrics.get('metrics', {}).keys())}")


async def main():
    """Run all demos"""
    print("\n" + "="*60)
    print("GHOSTGOAT UNIFIED SYSTEM DEMO")
    print("="*60)
    
    try:
        await demo_configuration()
        await demo_integration()
        await demo_memory()
        await demo_monitoring()
        await demo_api_gateway()
        
        print("\n" + "="*60)
        print("✓ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\n❌ Demo failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
