"""
Configuration settings for GovReport AI system.
Centralizes all configurable parameters for easy customization.
"""

import os
from typing import Dict, Any

class Config:
    """Configuration class for the application."""
    
    # Data Processing Limits
    MAX_SAMPLE_ROWS = int(os.environ.get('MAX_SAMPLE_ROWS', 1000))
    MAX_AI_TOKENS = int(os.environ.get('MAX_AI_TOKENS', 15000))
    MAX_FILE_SIZE_MB = float(os.environ.get('MAX_FILE_SIZE_MB', 100.0))
    
    # AI Planning Sample Sizes
    AI_SAMPLE_SIZES = {
        'small': 500,      # 0-5000 rows
        'medium': 750,     # 5000-10000 rows
        'large': 1000,     # 10000+ rows
        'extreme': 200     # Very large datasets (fallback)
    }
    
    # Chunk Processing
    CHUNK_SIZES = {
        'small': 1000,     # Standard chunk size
        'medium': 5000,    # Medium datasets
        'large': 10000     # Large datasets
    }
    
    # Processing Strategies
    PROCESSING_STRATEGIES = {
        'standard': {
            'description': 'Standard processing for datasets under 5000 rows',
            'ai_sample_size': 500,
            'chunk_size': 1000
        },
        'sampled': {
            'description': 'Sampled processing for datasets 5000-10000 rows',
            'ai_sample_size': 750,
            'chunk_size': 2000
        },
        'chunked': {
            'description': 'Chunked processing for datasets over 10000 rows',
            'ai_sample_size': 1000,
            'chunk_size': 5000
        }
    }
    
    # OpenAI Configuration
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o')
    OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS', 4000))
    OPENAI_TEMPERATURE = float(os.environ.get('OPENAI_TEMPERATURE', 0.7))
    
    # Cost Control
    COST_WARNINGS = {
        'token_threshold': 10000,
        'file_size_threshold_mb': 50.0,
        'row_count_threshold': 10000
    }
    
    # Performance Settings
    MAX_PROCESSING_TIME_SECONDS = int(os.environ.get('MAX_PROCESSING_TIME_SECONDS', 300))
    MEMORY_LIMIT_MB = int(os.environ.get('MEMORY_LIMIT_MB', 512))
    
    @classmethod
    def get_ai_sample_size(cls, row_count: int) -> int:
        """Get appropriate AI sample size based on row count."""
        if row_count <= 5000:
            return cls.AI_SAMPLE_SIZES['small']
        elif row_count <= 10000:
            return cls.AI_SAMPLE_SIZES['medium']
        elif row_count <= 50000:
            return cls.AI_SAMPLE_SIZES['large']
        else:
            return cls.AI_SAMPLE_SIZES['extreme']
    
    @classmethod
    def get_chunk_size(cls, row_count: int) -> int:
        """Get appropriate chunk size based on row count."""
        if row_count <= 10000:
            return cls.CHUNK_SIZES['small']
        elif row_count <= 50000:
            return cls.CHUNK_SIZES['medium']
        else:
            return cls.CHUNK_SIZES['large']
    
    @classmethod
    def get_processing_strategy(cls, row_count: int) -> str:
        """Get processing strategy based on row count."""
        if row_count <= 5000:
            return 'standard'
        elif row_count <= 10000:
            return 'sampled'
        else:
            return 'chunked'
    
    @classmethod
    def get_cost_warning(cls, row_count: int, file_size_mb: float, estimated_tokens: int) -> Dict[str, Any]:
        """Get cost warnings based on dataset characteristics."""
        warnings = []
        
        if row_count > cls.COST_WARNINGS['row_count_threshold']:
            warnings.append(f"Large dataset detected ({row_count:,} rows). Consider using a smaller sample for initial planning.")
        
        if file_size_mb > cls.COST_WARNINGS['file_size_threshold_mb']:
            warnings.append(f"Large file size ({file_size_mb:.1f} MB). Processing may take longer.")
        
        if estimated_tokens > cls.COST_WARNINGS['token_threshold']:
            warnings.append(f"High token usage estimated ({estimated_tokens:,} tokens). Using aggressive sampling to reduce costs.")
        
        return {
            'has_warnings': len(warnings) > 0,
            'warnings': warnings,
            'recommendations': cls._get_cost_recommendations(row_count, file_size_mb, estimated_tokens)
        }
    
    @classmethod
    def _get_cost_recommendations(cls, row_count: int, file_size_mb: float, estimated_tokens: int) -> list:
        """Get cost-saving recommendations."""
        recommendations = []
        
        if row_count > 10000:
            recommendations.append("Use AI-optimized sampling for planning (reduces tokens by 80%)")
            recommendations.append("Process data in chunks for better performance")
        
        if estimated_tokens > 10000:
            recommendations.append("Consider breaking large reports into smaller sections")
            recommendations.append("Use template-based planning for cost-sensitive operations")
        
        if file_size_mb > 50:
            recommendations.append("Large files may take longer to process")
            recommendations.append("Consider compressing data or using more efficient formats")
        
        return recommendations

# Environment-specific configurations
class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    MAX_SAMPLE_ROWS = 500
    MAX_AI_TOKENS = 10000

class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    MAX_SAMPLE_ROWS = 1000
    MAX_AI_TOKENS = 15000

class TestingConfig(Config):
    """Testing environment configuration."""
    DEBUG = True
    MAX_SAMPLE_ROWS = 100
    MAX_AI_TOKENS = 5000

# Configuration factory
def get_config(environment: str = None) -> Config:
    """Get configuration based on environment."""
    if environment is None:
        environment = os.environ.get('FLASK_ENV', 'development')
    
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    return configs.get(environment, DevelopmentConfig)
