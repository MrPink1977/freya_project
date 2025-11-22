"""
Model Manager - Smart model loading and hot-swapping for 16GB VRAM.

Manages multiple LLM models with automatic loading/unloading based on usage.
Optimized for RTX 5060 Ti (16GB VRAM) with intelligent resource management.
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Any, List
from pathlib import Path

from freya.shared.logging.logger import get_logger
from freya.shared.logging.decorators import log_performance
from freya.domain.exceptions import ModelLoadError, ModelNotFoundError


logger = get_logger(__name__)


class ModelType(Enum):
    """Available model types."""
    PRIMARY = "primary"
    REASONING = "reasoning"
    CODE = "code"
    VISION = "vision"
    EMBEDDING = "embedding"
    STT_TINY = "stt_tiny"
    STT_SMALL = "stt_small"


@dataclass
class ModelConfig:
    """Configuration for a single model."""
    name: str
    model_id: str
    vram_mb: int
    load_priority: int  # Lower = higher priority
    cache_ttl_seconds: int = 300  # 5 minutes default
    always_loaded: bool = False


@dataclass
class ModelInfo:
    """Runtime information about a loaded model."""
    model: Any
    config: ModelConfig
    load_time: float
    last_used: float
    usage_count: int = 0


class ModelManager:
    """
    Manages multiple AI models with smart loading/unloading.
    
    Features:
    - Hot-swapping: Load models on-demand, cache for reuse
    - VRAM management: Automatic unloading based on usage and memory
    - Priority system: Critical models stay loaded
    - Performance tracking: Monitor usage and load times
    
    Optimized for 16GB VRAM:
    - Primary (5GB) always loaded
    - Reasoning (7GB) loaded on-demand
    - Vision (7GB) loaded only when needed
    - STT models (2.5GB) loaded during conversation
    """
    
    def __init__(
        self,
        max_vram_mb: int = 14000,  # Leave 2GB headroom
        cleanup_interval: int = 60,  # Check every minute
    ):
        self.max_vram_mb = max_vram_mb
        self.cleanup_interval = cleanup_interval
        
        self._models: Dict[ModelType, ModelInfo] = {}
        self._loading_locks: Dict[ModelType, asyncio.Lock] = {
            model_type: asyncio.Lock() for model_type in ModelType
        }
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Model configurations
        self._configs = self._initialize_configs()
        
        logger.info(
            f"ModelManager initialized with {max_vram_mb}MB VRAM limit",
            extra={"max_vram_mb": max_vram_mb}
        )
    
    def _initialize_configs(self) -> Dict[ModelType, ModelConfig]:
        """Initialize model configurations."""
        return {
            ModelType.PRIMARY: ModelConfig(
                name="Primary Conversation",
                model_id="llama3.1:8b",
                vram_mb=5000,
                load_priority=1,
                always_loaded=True,
                cache_ttl_seconds=0,  # Never unload
            ),
            ModelType.REASONING: ModelConfig(
                name="Reasoning",
                model_id="qwen2.5:7b",
                vram_mb=7000,
                load_priority=2,
                cache_ttl_seconds=300,  # 5 minutes
            ),
            ModelType.CODE: ModelConfig(
                name="Code Generation",
                model_id="deepseek-coder:6.7b",
                vram_mb=7000,
                load_priority=3,
                cache_ttl_seconds=300,
            ),
            ModelType.VISION: ModelConfig(
                name="Vision Understanding",
                model_id="llava:7b",
                vram_mb=7000,
                load_priority=4,
                cache_ttl_seconds=180,  # 3 minutes
            ),
            ModelType.EMBEDDING: ModelConfig(
                name="Embedding",
                model_id="nomic-embed-text",
                vram_mb=500,
                load_priority=1,
                always_loaded=True,
                cache_ttl_seconds=0,
            ),
            ModelType.STT_TINY: ModelConfig(
                name="STT Tiny",
                model_id="tiny",
                vram_mb=500,
                load_priority=2,
                cache_ttl_seconds=60,  # 1 minute
            ),
            ModelType.STT_SMALL: ModelConfig(
                name="STT Small",
                model_id="small",
                vram_mb=2000,
                load_priority=2,
                cache_ttl_seconds=60,
            ),
        }
    
    async def start(self):
        """Start the model manager and load essential models."""
        logger.info("Starting ModelManager...")
        
        # Load always-loaded models
        for model_type, config in self._configs.items():
            if config.always_loaded:
                try:
                    await self.get_model(model_type)
                    logger.info(f"Preloaded {config.name}")
                except Exception as e:
                    logger.error(
                        f"Failed to preload {config.name}: {e}",
                        extra={"model_type": model_type.value, "error": str(e)}
                    )
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("ModelManager started successfully")
    
    async def stop(self):
        """Stop the model manager and unload all models."""
        logger.info("Stopping ModelManager...")
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Unload all models
        for model_type in list(self._models.keys()):
            await self._unload_model(model_type)
        
        logger.info("ModelManager stopped")
    
    @log_performance
    async def get_model(self, model_type: ModelType) -> Any:
        """
        Get a model, loading it if necessary.
        
        Args:
            model_type: Type of model to get
            
        Returns:
            The loaded model instance
            
        Raises:
            ModelNotFoundError: If model type is not configured
            ModelLoadError: If model fails to load
        """
        if model_type not in self._configs:
            raise ModelNotFoundError(f"Model type {model_type.value} not configured")
        
        # If already loaded, update usage and return
        if model_type in self._models:
            model_info = self._models[model_type]
            model_info.last_used = time.time()
            model_info.usage_count += 1
            
            logger.debug(
                f"Using cached {model_info.config.name}",
                extra={
                    "model_type": model_type.value,
                    "usage_count": model_info.usage_count
                }
            )
            
            return model_info.model
        
        # Load the model (with lock to prevent duplicate loads)
        async with self._loading_locks[model_type]:
            # Double-check after acquiring lock
            if model_type in self._models:
                return self._models[model_type].model
            
            # Check if we have enough VRAM
            config = self._configs[model_type]
            current_vram = self._get_current_vram_usage()
            required_vram = current_vram + config.vram_mb
            
            if required_vram > self.max_vram_mb:
                # Try to free up space
                freed = await self._free_vram(config.vram_mb)
                if not freed:
                    raise ModelLoadError(
                        f"Insufficient VRAM for {config.name}. "
                        f"Need {config.vram_mb}MB, have {self.max_vram_mb - current_vram}MB"
                    )
            
            # Load the model
            logger.info(
                f"Loading {config.name}...",
                extra={"model_type": model_type.value, "model_id": config.model_id}
            )
            
            start_time = time.time()
            try:
                model = await self._load_model(config)
                load_time = time.time() - start_time
                
                # Store model info
                self._models[model_type] = ModelInfo(
                    model=model,
                    config=config,
                    load_time=load_time,
                    last_used=time.time(),
                    usage_count=1
                )
                
                logger.info(
                    f"Loaded {config.name} in {load_time:.2f}s",
                    extra={
                        "model_type": model_type.value,
                        "load_time": load_time,
                        "vram_mb": config.vram_mb
                    }
                )
                
                return model
                
            except Exception as e:
                logger.error(
                    f"Failed to load {config.name}: {e}",
                    extra={"model_type": model_type.value, "error": str(e)}
                )
                raise ModelLoadError(f"Failed to load {config.name}: {e}") from e
    
    async def _load_model(self, config: ModelConfig) -> Any:
        """
        Load a model based on its configuration.
        
        This is a placeholder - implement actual model loading logic here.
        """
        # Import model libraries here to avoid loading them if not needed
        if "llama" in config.model_id or "qwen" in config.model_id or "mistral" in config.model_id:
            # Ollama-based LLM
            from freya.infrastructure.llm.ollama_client import OllamaClient
            return OllamaClient(model=config.model_id)
        
        elif "deepseek" in config.model_id:
            # Code model
            from freya.infrastructure.llm.ollama_client import OllamaClient
            return OllamaClient(model=config.model_id)
        
        elif "llava" in config.model_id:
            # Vision model
            from freya.infrastructure.llm.ollama_client import OllamaClient
            return OllamaClient(model=config.model_id)
        
        elif "nomic-embed" in config.model_id:
            # Embedding model
            from freya.infrastructure.memory.embedding import NomicEmbedding
            return NomicEmbedding()
        
        elif config.model_id in ["tiny", "small", "base", "medium"]:
            # Whisper STT model
            from freya.infrastructure.speech.whisper_stt import WhisperSTT
            return WhisperSTT(model_size=config.model_id)
        
        else:
            raise ModelLoadError(f"Unknown model type: {config.model_id}")
    
    async def _unload_model(self, model_type: ModelType):
        """Unload a model and free resources."""
        if model_type not in self._models:
            return
        
        model_info = self._models[model_type]
        config = model_info.config
        
        # Don't unload always-loaded models
        if config.always_loaded:
            logger.debug(f"Skipping unload of always-loaded {config.name}")
            return
        
        logger.info(
            f"Unloading {config.name}",
            extra={
                "model_type": model_type.value,
                "usage_count": model_info.usage_count,
                "uptime": time.time() - model_info.load_time
            }
        )
        
        # Clean up model resources
        try:
            if hasattr(model_info.model, 'cleanup'):
                await model_info.model.cleanup()
            del model_info.model
        except Exception as e:
            logger.warning(f"Error during model cleanup: {e}")
        
        # Remove from loaded models
        del self._models[model_type]
        
        logger.info(f"Unloaded {config.name}")
    
    async def _free_vram(self, required_mb: int) -> bool:
        """
        Try to free up VRAM by unloading low-priority models.
        
        Returns:
            True if enough VRAM was freed, False otherwise
        """
        current_vram = self._get_current_vram_usage()
        target_vram = current_vram - required_mb
        
        if target_vram <= self.max_vram_mb:
            return True  # Already have enough
        
        logger.info(
            f"Attempting to free {required_mb}MB VRAM",
            extra={"current_vram": current_vram, "required": required_mb}
        )
        
        # Get unloadable models sorted by priority (lowest priority first)
        unloadable = [
            (model_type, info)
            for model_type, info in self._models.items()
            if not info.config.always_loaded
        ]
        unloadable.sort(key=lambda x: (-x[1].config.load_priority, x[1].last_used))
        
        # Unload models until we have enough space
        for model_type, info in unloadable:
            await self._unload_model(model_type)
            current_vram -= info.config.vram_mb
            
            if current_vram + required_mb <= self.max_vram_mb:
                logger.info(f"Freed enough VRAM ({info.config.vram_mb}MB)")
                return True
        
        logger.warning("Could not free enough VRAM")
        return False
    
    def _get_current_vram_usage(self) -> int:
        """Calculate current VRAM usage in MB."""
        return sum(info.config.vram_mb for info in self._models.values())
    
    async def _cleanup_loop(self):
        """Periodically clean up unused models."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_unused_models()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_unused_models(self):
        """Unload models that haven't been used recently."""
        now = time.time()
        to_unload = []
        
        for model_type, info in self._models.items():
            if info.config.always_loaded:
                continue
            
            idle_time = now - info.last_used
            if idle_time > info.config.cache_ttl_seconds:
                to_unload.append(model_type)
        
        if to_unload:
            logger.info(
                f"Cleaning up {len(to_unload)} unused models",
                extra={"models": [mt.value for mt in to_unload]}
            )
            
            for model_type in to_unload:
                await self._unload_model(model_type)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all models."""
        now = time.time()
        return {
            "vram_usage_mb": self._get_current_vram_usage(),
            "vram_limit_mb": self.max_vram_mb,
            "loaded_models": {
                model_type.value: {
                    "name": info.config.name,
                    "vram_mb": info.config.vram_mb,
                    "usage_count": info.usage_count,
                    "idle_seconds": int(now - info.last_used),
                    "uptime_seconds": int(now - info.load_time),
                }
                for model_type, info in self._models.items()
            }
        }
