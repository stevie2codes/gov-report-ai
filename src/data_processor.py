#!/usr/bin/env python3
"""
Data processing module for CSV/XLSX files.
Handles file parsing, column type inference, and data profiling.
"""

import pandas as pd
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re
from io import StringIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ColumnProfile:
    """Profile information for a single column."""
    
    def __init__(self, name: str, data_type: str, sample_values: List[str], 
                 null_count: int = 0, unique_count: int = 0):
        self.name = name
        self.type = data_type
        self.sample_values = sample_values
        self.null_count = null_count
        self.unique_count = unique_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation with JSON-serializable types."""
        return {
            'name': self.name,
            'type': self.type,
            'sample_values': self.sample_values,
            'null_count': int(self.null_count),  # Convert numpy types to Python types
            'unique_count': int(self.unique_count)
        }

class DataProfile:
    """Profile information for an entire dataset."""
    
    def __init__(self, columns: List[ColumnProfile], total_rows: int = 0, 
                 file_size_mb: float = 0.0, processing_time: float = 0.0):
        self.columns = columns
        self.total_rows = total_rows
        self.file_size_mb = file_size_mb
        self.processing_time = processing_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation with JSON-serializable types."""
        return {
            'columns': [col.to_dict() for col in self.columns],
            'total_rows': int(self.total_rows),  # Convert numpy types to Python types
            'file_size_mb': float(self.file_size_mb),
            'processing_time': float(self.processing_time)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataProfile':
        columns = [ColumnProfile(**col_data) for col_data in data['columns']]
        return cls(
            columns=columns,
            total_rows=data.get('total_rows', 0),
            file_size_mb=data.get('file_size_mb', 0.0),
            processing_time=data.get('processing_time', 0.0)
        )
    
    def get_columns_by_type(self, data_type: str) -> List[str]:
        """Get column names of a specific type."""
        return [col.name for col in self.columns if col.type == data_type]
    
    def get_sample_for_ai(self, max_rows: int = 500) -> 'DataProfile':
        """Create a sampled profile for AI planning to reduce token usage."""
        if self.total_rows <= max_rows:
            return self
        
        # Create sampled profile with representative data
        sampled_columns = []
        for col in self.columns:
            # Take first, middle, and last samples for better representation
            if self.total_rows > max_rows:
                sample_size = min(max_rows, len(col.sample_values))
                if sample_size < len(col.sample_values):
                    # Take samples from different parts of the data
                    first_samples = col.sample_values[:sample_size//2]
                    last_samples = col.sample_values[-(sample_size//2):]
                    sampled_values = first_samples + last_samples
                else:
                    sampled_values = col.sample_values
            else:
                sampled_values = col.sample_values
            
            sampled_col = ColumnProfile(
                name=col.name,
                data_type=col.type,
                sample_values=sampled_values,
                null_count=col.null_count,
                unique_count=col.unique_count
            )
            sampled_columns.append(sampled_col)
        
        return DataProfile(
            columns=sampled_columns,
            total_rows=min(self.total_rows, max_rows),
            file_size_mb=self.file_size_mb,
            processing_time=self.processing_time
        )
    
    def get_processing_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for processing large datasets."""
        recommendations = {
            'ai_planning_sample_size': 500,
            'chunk_size': 1000,
            'estimated_ai_tokens': 0,
            'processing_strategy': 'standard'
        }
        
        if self.total_rows > 10000:
            recommendations['processing_strategy'] = 'chunked'
            recommendations['chunk_size'] = 5000
            recommendations['ai_planning_sample_size'] = 1000
        elif self.total_rows > 5000:
            recommendations['processing_strategy'] = 'sampled'
            recommendations['ai_planning_sample_size'] = 750
        
        # Estimate AI token usage (rough calculation)
        total_chars = sum(len(str(val)) for col in self.columns for val in col.sample_values)
        recommendations['estimated_ai_tokens'] = total_chars // 4  # Rough token estimate
        
        return recommendations

class DataProcessor:
    """Process and analyze data files."""
    
    def __init__(self, max_sample_rows: int = 500, max_ai_tokens: int = 10000):
        self.max_sample_rows = max_sample_rows
        self.max_ai_tokens = max_ai_tokens
    
    def process_data_from_string(self, data_string: str, file_type: str = 'csv') -> DataProfile:
        """Process data from a string and return a profile."""
        start_time = datetime.now()
        
        try:
            if file_type.lower() == 'csv':
                df = pd.read_csv(StringIO(data_string))
            elif file_type.lower() in ['xlsx', 'xls']:
                df = pd.read_excel(StringIO(data_string))
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # Calculate file size (rough estimate)
            file_size_mb = len(data_string.encode('utf-8')) / (1024 * 1024)
            
            # Create column profiles
            columns = []
            for col_name in df.columns:
                col_data = df[col_name]
                data_type = self._infer_column_type(col_data)
                sample_values = self._get_sample_values(col_data)
                null_count = col_data.isnull().sum()
                unique_count = col_data.nunique()
                
                column_profile = ColumnProfile(
                    name=col_name,
                    data_type=data_type,
                    sample_values=sample_values,
                    null_count=null_count,
                    unique_count=unique_count
                )
                columns.append(column_profile)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            profile = DataProfile(
                columns=columns,
                total_rows=len(df),
                file_size_mb=file_size_mb,
                processing_time=processing_time
            )
            
            # Log processing info
            logger.info(f"Processed {len(df)} rows in {processing_time:.2f}s, "
                       f"file size: {file_size_mb:.2f}MB")
            
            return profile
            
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            raise
    
    def _infer_column_type(self, column_data: pd.Series) -> str:
        """Infer the data type of a column."""
        # Remove null values for type inference
        clean_data = column_data.dropna()
        
        if len(clean_data) == 0:
            return 'string'
        
        # Check if it's a date column
        if self._is_date_column(clean_data):
            return 'date'
        
        # Check if it's numeric
        if pd.api.types.is_numeric_dtype(clean_data):
            # Check if it's currency
            if self._is_currency_column(clean_data):
                return 'currency'
            # Check if it's percentage
            elif self._is_percentage_column(clean_data):
                return 'percent'
            else:
                return 'number'
        
        # Check if it's boolean
        if pd.api.types.is_bool_dtype(clean_data):
            return 'boolean'
        
        # Default to string
        return 'string'
    
    def _is_date_column(self, column_data: pd.Series) -> bool:
        """Check if a column contains date-like data."""
        # Try to parse as datetime
        try:
            pd.to_datetime(column_data, errors='raise')
            return True
        except:
            return False
    
    def _is_currency_column(self, column_data: pd.Series) -> bool:
        """Check if a column contains currency data."""
        # Look for currency symbols or patterns
        sample_str = str(column_data.iloc[0]) if len(column_data) > 0 else ""
        currency_patterns = [r'\$', r'USD', r'EUR', r'GBP', r'CAD']
        return any(re.search(pattern, sample_str) for pattern in currency_patterns)
    
    def _is_percentage_column(self, column_data: pd.Series) -> bool:
        """Check if a column contains percentage data."""
        # Look for percentage signs or values between 0-1
        sample_str = str(column_data.iloc[0]) if len(column_data) > 0 else ""
        if '%' in sample_str:
            return True
        
        # Check if values are typically between 0-1 (common for percentages)
        numeric_data = pd.to_numeric(column_data, errors='coerce').dropna()
        if len(numeric_data) > 0:
            return (numeric_data >= 0).all() and (numeric_data <= 1).all()
        
        return False
    
    def _get_sample_values(self, column_data: pd.Series) -> List[str]:
        """Get sample values from a column for profiling."""
        # Get non-null values
        clean_data = column_data.dropna()
        
        if len(clean_data) == 0:
            return []
        
        # Take a sample of values (first few + some random ones)
        sample_size = min(self.max_sample_rows, len(clean_data))
        
        if len(clean_data) <= sample_size:
            sample_values = clean_data.tolist()
        else:
            # Take first few and some from middle/end for better representation
            first_values = clean_data.head(sample_size // 2).tolist()
            remaining_values = clean_data.tail(sample_size // 2).tolist()
            sample_values = first_values + remaining_values
        
        # Convert to strings and limit length to prevent token explosion
        string_values = []
        for val in sample_values:
            str_val = str(val)
            if len(str_val) > 100:  # Limit very long values
                str_val = str_val[:100] + "..."
            string_values.append(str_val)
        
        return string_values
    
    def get_ai_planning_profile(self, full_profile: DataProfile) -> Tuple[DataProfile, Dict[str, Any]]:
        """Get an AI-optimized profile for planning while preserving full data."""
        recommendations = full_profile.get_processing_recommendations()
        
        # Create sampled profile for AI planning
        ai_profile = full_profile.get_sample_for_ai(recommendations['ai_planning_sample_size'])
        
        # Check if we're within token limits
        if recommendations['estimated_ai_tokens'] > self.max_ai_tokens:
            logger.warning(f"Estimated AI tokens ({recommendations['estimated_ai_tokens']}) "
                          f"exceeds limit ({self.max_ai_tokens}). Using aggressive sampling.")
            ai_profile = full_profile.get_sample_for_ai(200)  # Very aggressive sampling
        
        return ai_profile, recommendations

def create_sample_data_profile() -> DataProfile:
    """Create a sample data profile for testing."""
    columns = [
        ColumnProfile("Department", "string", ["Finance", "Public Works", "Health", "Police"]),
        ColumnProfile("Budget", "currency", ["$1,200,000", "$850,000", "$650,000", "$1,100,000"]),
        ColumnProfile("Actual", "currency", ["$1,180,000", "$870,000", "$640,000", "$1,050,000"]),
        ColumnProfile("Variance", "percent", ["-1.7%", "2.4%", "-1.5%", "-4.5%"]),
        ColumnProfile("Date", "date", ["2024-01-01", "2024-01-01", "2024-01-01", "2024-01-01"])
    ]
    
    return DataProfile(columns=columns, total_rows=4, file_size_mb=0.001, processing_time=0.1)
