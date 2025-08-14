#!/usr/bin/env python3
"""
Data processing module for CSV/XLSX files.
Handles file parsing, column type inference, and data profiling.
"""

import csv
import io
import logging
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
import pandas as pd
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ColumnProfile:
    """Represents the profile of a single column in the dataset."""
    
    def __init__(self, name: str, values: List[Any]):
        self.name = name
        self.sample_values = self._extract_sample_values(values)
        self.type = self._infer_column_type(values)
        self.stats = self._calculate_basic_stats(values)
    
    def _extract_sample_values(self, values: List[Any]) -> List[str]:
        """Extract up to 5 sample values for display."""
        # Filter out None/NaN values and convert to strings
        valid_values = [str(v) for v in values if v is not None and pd.notna(v)]
        return valid_values[:5]
    
    def _infer_column_type(self, values: List[Any]) -> str:
        """Infer the column type based on the data."""
        if not values:
            return 'string'
        
        # Remove None/NaN values
        valid_values = [v for v in values if v is not None and pd.notna(v)]
        if not valid_values:
            return 'string'
        
        # Check if it's a date column
        if self._is_date_column(valid_values):
            return 'date'
        
        # Check if it's a percentage column
        if self._is_percentage_column(valid_values):
            return 'percent'
        
        # Check if it's a currency column
        if self._is_currency_column(valid_values):
            return 'currency'
        
        # Check if it's a numeric column
        if self._is_numeric_column(valid_values):
            return 'number'
        
        # Default to string
        return 'string'
    
    def _is_date_column(self, values: List[Any]) -> bool:
        """Check if the column contains date values."""
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # M/D/YY or M/D/YYYY
        ]
        
        date_count = 0
        for value in values[:20]:  # Check first 20 values
            str_value = str(value).strip()
            for pattern in date_patterns:
                if re.match(pattern, str_value):
                    date_count += 1
                    break
        
        # If more than 70% of values look like dates, classify as date
        return date_count / min(len(values), 20) > 0.7
    
    def _is_currency_column(self, values: List[Any]) -> bool:
        """Check if the column contains currency values."""
        currency_patterns = [
            r'^\$[\d,]+\.?\d*$',  # $1,234.56
            r'^\$[\d]+\.?\d*$',   # $1234.56
        ]
        
        currency_count = 0
        for value in values[:20]:
            str_value = str(value).strip()
            for pattern in currency_patterns:
                if re.match(pattern, str_value):
                    currency_count += 1
                    break
        
        return currency_count / min(len(values), 20) > 0.7
    
    def _is_percentage_column(self, values: List[Any]) -> bool:
        """Check if the column contains percentage values."""
        percent_patterns = [
            r'^-?\d+\.?\d*%$',      # -1.67% or 12.34%
        ]
        
        percent_count = 0
        for value in values[:20]:
            str_value = str(value).strip()
            for pattern in percent_patterns:
                if re.match(pattern, str_value):
                    percent_count += 1
                    break
        
        return percent_count / min(len(values), 20) > 0.7
    
    def _is_numeric_column(self, values: List[Any]) -> bool:
        """Check if the column contains numeric values."""
        numeric_count = 0
        text_like_count = 0
        
        for value in values[:20]:
            str_value = str(value).strip()
            
            # Check if it looks like text (contains letters)
            if re.search(r'[a-zA-Z]', str_value):
                text_like_count += 1
                continue
            
            try:
                # Remove commas and try to convert to float
                clean_value = str_value.replace(',', '').replace('$', '').replace('%', '')
                float(clean_value)
                numeric_count += 1
            except (ValueError, TypeError):
                continue
        
        # If more than 30% look like text, it's probably not numeric
        if text_like_count / min(len(values), 20) > 0.3:
            return False
        
        return numeric_count / min(len(values), 20) > 0.7
    
    def _calculate_basic_stats(self, values: List[Any]) -> Dict[str, Any]:
        """Calculate basic statistics for the column."""
        stats = {
            'total_count': len(values),
            'null_count': sum(1 for v in values if v is None or pd.isna(v)),
            'unique_count': len(set(str(v) for v in values if v is not None and not pd.isna(v)))
        }
        
        if self.type == 'number':
            try:
                numeric_values = [float(str(v).replace(',', '')) for v in values 
                                if v is not None and not pd.isna(v)]
                if numeric_values:
                    stats.update({
                        'min': min(numeric_values),
                        'max': max(numeric_values),
                        'mean': sum(numeric_values) / len(numeric_values)
                    })
            except (ValueError, TypeError):
                pass
        
        return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'type': self.type,
            'sampleValues': self.sample_values,
            'stats': self.stats
        }


class DataProfile:
    """Represents the complete profile of a dataset."""
    
    def __init__(self, columns: List[ColumnProfile]):
        self.columns = columns
        self.row_count = self._get_row_count()
        self.column_count = len(columns)
    
    def _get_row_count(self) -> int:
        """Get the total number of rows in the dataset."""
        if not self.columns:
            return 0
        return self.columns[0].stats['total_count']
    
    def get_column_by_name(self, name: str) -> Optional[ColumnProfile]:
        """Get a column profile by name."""
        for col in self.columns:
            if col.name == name:
                return col
        return None
    
    def get_columns_by_type(self, column_type: str) -> List[ColumnProfile]:
        """Get all columns of a specific type."""
        return [col for col in self.columns if col.type == column_type]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'columns': [col.to_dict() for col in self.columns],
            'row_count': self.row_count,
            'column_count': self.column_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataProfile':
        """Create a DataProfile instance from a dictionary."""
        columns = []
        for col_data in data['columns']:
            # Create a minimal ColumnProfile with required attributes
            col = cls._create_column_from_dict(col_data)
            columns.append(col)
        
        profile = cls(columns)
        profile.row_count = data.get('row_count', 0)
        profile.column_count = data.get('column_count', len(columns))
        return profile
    
    @staticmethod
    def _create_column_from_dict(col_data: Dict[str, Any]) -> 'ColumnProfile':
        """Create a ColumnProfile from dictionary data."""
        # Create a minimal ColumnProfile instance
        col = ColumnProfile.__new__(ColumnProfile)
        col.name = col_data['name']
        col.type = col_data['type']
        col.sample_values = col_data.get('sampleValues', [])
        col.stats = col_data.get('stats', {})
        return col


class DataProcessor:
    """Main class for processing CSV/XLSX files and generating data profiles."""
    
    def __init__(self, max_sample_rows: int = 50):
        self.max_sample_rows = max_sample_rows
    
    def process_file(self, file_path: Union[str, Path]) -> DataProfile:
        """Process a CSV or XLSX file and return a DataProfile."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            if file_path.suffix.lower() == '.csv':
                return self._process_csv(file_path)
            elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                return self._process_excel(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            raise
    
    def _process_csv(self, file_path: Path) -> DataProfile:
        """Process a CSV file."""
        try:
            # Read CSV with pandas for better handling of various formats
            df = pd.read_csv(file_path, nrows=self.max_sample_rows)
            return self._create_profile_from_dataframe(df)
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            raise
    
    def _process_excel(self, file_path: Path) -> DataProfile:
        """Process an Excel file."""
        try:
            # Read Excel file
            df = pd.read_excel(file_path, nrows=self.max_sample_rows)
            return self._create_profile_from_dataframe(df)
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            raise
    
    def _create_profile_from_dataframe(self, df: pd.DataFrame) -> DataProfile:
        """Create a DataProfile from a pandas DataFrame."""
        columns = []
        
        for column_name in df.columns:
            # Get the column values
            values = df[column_name].tolist()
            
            # Create column profile
            column_profile = ColumnProfile(column_name, values)
            columns.append(column_profile)
        
        return DataProfile(columns)
    
    def process_data_from_string(self, data: str, file_type: str = 'csv') -> DataProfile:
        """Process data from a string (useful for web uploads)."""
        try:
            if file_type.lower() == 'csv':
                # Use StringIO to create a file-like object
                csv_file = io.StringIO(data)
                df = pd.read_csv(csv_file, nrows=self.max_sample_rows)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            return self._create_profile_from_dataframe(df)
        except Exception as e:
            logger.error(f"Error processing data string: {e}")
            raise


def create_sample_data_profile() -> DataProfile:
    """Create a sample DataProfile for testing purposes."""
    sample_data = {
        'Department': ['Finance', 'Public Works', 'Health', 'Police', 'Permitting'],
        'Budget': ['$1,200,000', '$850,000', '$650,000', '$1,100,000', '$300,000'],
        'Actual': ['$1,180,000', '$870,000', '$620,000', '$1,050,000', '$320,000'],
        'Variance': ['-1.67%', '2.35%', '-4.62%', '-4.55%', '6.67%'],
        'Date': ['2024-01-01', '2024-01-01', '2024-01-01', '2024-01-01', '2024-01-01']
    }
    
    df = pd.DataFrame(sample_data)
    processor = DataProcessor()
    return processor._create_profile_from_dataframe(df)
