"""
Multi-LLM Support Abstraction Layer
Provides unified interface for multiple LLM providers
"""

import logging
from typing import Dict, List, Optional, Any, Generator
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass

from unified_config import LLMProvider, LLMConfig

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    """LLM message"""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """LLM response"""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None


class LLMInterface(ABC):
    """Abstract base class for LLM interfaces"""
    
    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Union[LLMResponse, Generator[str, None, None]]:
        """Generate completion"""
        pass
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate text embedding"""
        pass


class OpenAIInterface(LLMInterface):
    """OpenAI LLM interface"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        try:
            import openai
            self.client = openai.OpenAI(api_key=config.api_key)
            self.model = config.model
        except ImportError:
            raise ImportError("OpenAI library not installed. Install with: pip install openai")
    
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Union[LLMResponse, Generator[str, None, None]]:
        """Generate completion using OpenAI"""
        try:
            # Convert messages to OpenAI format
            openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                stream=stream
            )
            
            if stream:
                def stream_generator():
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                return stream_generator()
            else:
                return LLMResponse(
                    content=response.choices[0].message.content,
                    model=self.model,
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    } if response.usage else None,
                    finish_reason=response.choices[0].finish_reason
                )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise


class AnthropicInterface(LLMInterface):
    """Anthropic Claude LLM interface"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=config.api_key)
            self.model = config.model
        except ImportError:
            raise ImportError("Anthropic library not installed. Install with: pip install anthropic")
    
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Union[LLMResponse, Generator[str, None, None]]:
        """Generate completion using Anthropic"""
        try:
            # Convert messages to Anthropic format
            # Anthropic uses different message format
            system_message = None
            anthropic_messages = []
            
            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    anthropic_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.config.max_tokens,
                temperature=temperature or self.config.temperature,
                system=system_message,
                messages=anthropic_messages,
                stream=stream
            )
            
            if stream:
                def stream_generator():
                    for chunk in response:
                        if chunk.type == "content_block_delta":
                            if chunk.delta.text:
                                yield chunk.delta.text
                return stream_generator()
            else:
                return LLMResponse(
                    content=response.content[0].text,
                    model=self.model,
                    usage={
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens
                    } if hasattr(response, 'usage') else None
                )
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Anthropic"""
        # Anthropic doesn't have a separate embedding API
        # Use OpenAI embeddings as fallback or implement custom solution
        logger.warning("Anthropic doesn't have embedding API, using OpenAI fallback")
        try:
            import openai
            client = openai.OpenAI(api_key=self.config.api_key)
            response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise


class MockLLMInterface(LLMInterface):
    """Mock LLM interface for testing"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.model = "mock-llm"
    
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Union[LLMResponse, Generator[str, None, None]]:
        """Generate mock completion"""
        last_message = messages[-1].content if messages else ""
        
        # Simple pattern-based responses
        if "decompose" in last_message.lower() or "break down" in last_message.lower():
            content = '{"tasks": [{"description": "Task 1", "capability": "general"}]}'
        elif "select agent" in last_message.lower():
            content = '{"selected_agent": "agent_1", "reasoning": "Best match"}'
        else:
            content = f"Mock response for: {last_message[:100]}"
        
        if stream:
            def stream_generator():
                for word in content.split():
                    yield word + " "
            return stream_generator()
        else:
            return LLMResponse(
                content=content,
                model=self.model,
                usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            )
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate mock embedding"""
        # Return a simple mock embedding vector
        return [0.1] * 384  # Standard embedding size


class MultiLLM:
    """
    Multi-LLM abstraction layer
    Provides unified interface for multiple LLM providers
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.interface: Optional[LLMInterface] = None
        self._initialize_interface()
    
    def _initialize_interface(self):
        """Initialize the appropriate LLM interface"""
        if self.config.provider == LLMProvider.OPENAI:
            self.interface = OpenAIInterface(self.config)
        elif self.config.provider == LLMProvider.ANTHROPIC:
            self.interface = AnthropicInterface(self.config)
        elif self.config.provider == LLMProvider.MOCK:
            self.interface = MockLLMInterface(self.config)
        else:
            logger.warning(f"Unknown provider {self.config.provider}, using mock")
            self.interface = MockLLMInterface(self.config)
    
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Union[LLMResponse, Generator[str, None, None]]:
        """Generate completion"""
        return await self.interface.generate(messages, temperature, max_tokens, stream)
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding"""
        return await self.interface.generate_embedding(text)
    
    def format_messages(
        self,
        system_prompt: str,
        user_message: str,
        history: Optional[List[LLMMessage]] = None
    ) -> List[LLMMessage]:
        """Format messages for LLM"""
        messages = [LLMMessage(role="system", content=system_prompt)]
        
        if history:
            messages.extend(history)
        
        messages.append(LLMMessage(role="user", content=user_message))
        
        return messages
    
    def switch_provider(self, provider: LLMProvider, api_key: Optional[str] = None):
        """Switch to a different LLM provider"""
        self.config.provider = provider
        if api_key:
            self.config.api_key = api_key
        self._initialize_interface()
        logger.info(f"Switched to {provider.value} provider")


# Factory function
def create_llm(config: Optional[LLMConfig] = None) -> MultiLLM:
    """Create MultiLLM instance"""
    from unified_config import get_config
    if config is None:
        config = get_config().llm
    return MultiLLM(config)
