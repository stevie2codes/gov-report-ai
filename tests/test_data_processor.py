"""
Tests for the data processing module.
"""

import pytest
import pandas as pd
import tempfile
import os
from pathlib import Path
import sys

# Add the src directory to the Python path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_processor import DataProcessor, ColumnProfile, DataProfile, create_sample_data_profile


class TestColumnProfile:
    """Test the ColumnProfile class."""
    
    def test_string_column(self):
        """Test string column type inference."""
        values = ["Finance", "Public Works", "Health", "Police"]
        profile = ColumnProfile("Department", values)
        
        assert profile.name == "Department"
        assert profile.type == "string"
        assert len(profile.sample_values) <= 5
        assert profile.stats["total_count"] == 4
        assert profile.stats["null_count"] == 0
        assert profile.stats["unique_count"] == 4
    
    def test_currency_column(self):
        """Test currency column type inference."""
        values = ["$1,200,000", "$850,000", "$650,000", "$1,100,000"]
        profile = ColumnProfile("Budget", values)
        
        assert profile.type == "currency"
        assert profile.stats["total_count"] == 4
    
    def test_percentage_column(self):
        """Test percentage column type inference."""
        values = ["-1.67%", "2.35%", "-4.62%", "6.67%"]
        profile = ColumnProfile("Variance", values)
        
        assert profile.type == "percent"
        assert profile.stats["total_count"] == 4
    
    def test_date_column(self):
        """Test date column type inference."""
        values = ["2024-01-01", "2024-01-01", "2024-01-01", "2024-01-01"]
        profile = ColumnProfile("Date", values)
        
        assert profile.type == "date"
        assert profile.stats["total_count"] == 4
    
    def test_numeric_column(self):
        """Test numeric column type inference."""
        values = ["1200000", "850000", "650000", "1100000"]
        profile = ColumnProfile("Value", values)
        
        assert profile.type == "number"
        assert profile.stats["total_count"] == 4
        assert "min" in profile.stats
        assert "max" in profile.stats
        assert "mean" in profile.stats


class TestDataProfile:
    """Test the DataProfile class."""
    
    def test_data_profile_creation(self):
        """Test creating a DataProfile from columns."""
        columns = [
            ColumnProfile("Department", ["Finance", "Public Works"]),
            ColumnProfile("Budget", ["$1,200,000", "$850,000"])
        ]
        
        profile = DataProfile(columns)
        
        assert profile.column_count == 2
        assert profile.row_count == 2
        assert len(profile.columns) == 2
    
    def test_get_column_by_name(self):
        """Test getting a column by name."""
        columns = [
            ColumnProfile("Department", ["Finance", "Public Works"]),
            ColumnProfile("Budget", ["$1,200,000", "$850,000"])
        ]
        
        profile = DataProfile(columns)
        
        dept_col = profile.get_column_by_name("Department")
        assert dept_col is not None
        assert dept_col.name == "Department"
        
        missing_col = profile.get_column_by_name("Missing")
        assert missing_col is None
    
    def test_get_columns_by_type(self):
        """Test getting columns by type."""
        columns = [
            ColumnProfile("Department", ["Finance", "Public Works"]),
            ColumnProfile("Budget", ["$1,200,000", "$850,000"]),
            ColumnProfile("Variance", ["-1.67%", "2.35%"])
        ]
        
        profile = DataProfile(columns)
        
        string_cols = profile.get_columns_by_type("string")
        assert len(string_cols) == 1
        assert string_cols[0].name == "Department"
        
        currency_cols = profile.get_columns_by_type("currency")
        assert len(currency_cols) == 1
        assert currency_cols[0].name == "Budget"


class TestDataProcessor:
    """Test the DataProcessor class."""
    
    def test_csv_processing(self):
        """Test processing a CSV file."""
        # Create a temporary CSV file with proper CSV formatting
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Department,Budget,Actual\n")
            f.write("Finance,\"$1,200,000\",\"$1,180,000\"\n")
            f.write("Public Works,\"$850,000\",\"$870,000\"\n")
            f.write("Health,\"$650,000\",\"$620,000\"\n")
            temp_file = f.name
        
        try:
            processor = DataProcessor(max_sample_rows=10)
            profile = processor.process_file(temp_file)
            
            assert profile.column_count == 3
            assert profile.row_count == 3
            
            # Check column types
            dept_col = profile.get_column_by_name("Department")
            assert dept_col.type == "string"
            
            budget_col = profile.get_column_by_name("Budget")
            assert budget_col.type == "currency"
            
            actual_col = profile.get_column_by_name("Actual")
            assert actual_col.type == "currency"
            
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_excel_processing(self):
        """Test processing an Excel file."""
        # Create a temporary Excel file
        df = pd.DataFrame({
            'Department': ['Finance', 'Public Works', 'Health'],
            'Budget': ['$1,200,000', '$850,000', '$650,000'],
            'Actual': ['$1,180,000', '$870,000', '$620,000']
        })
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            df.to_excel(f.name, index=False)
            temp_file = f.name
        
        try:
            processor = DataProcessor(max_sample_rows=10)
            profile = processor.process_file(temp_file)
            
            assert profile.column_count == 3
            assert profile.row_count == 3
            
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_data_from_string(self):
        """Test processing data from a string."""
        csv_data = "Department,Budget\nFinance,\"$1,200,000\"\nPublic Works,\"$850,000\""
        
        processor = DataProcessor(max_sample_rows=10)
        profile = processor.process_data_from_string(csv_data, 'csv')
        
        assert profile.column_count == 2
        assert profile.row_count == 2
        
        dept_col = profile.get_column_by_name("Department")
        assert dept_col.type == "string"
        
        budget_col = profile.get_column_by_name("Budget")
        assert budget_col.type == "currency"


class TestSampleData:
    """Test sample data creation."""
    
    def test_sample_data_profile(self):
        """Test creating a sample data profile."""
        profile = create_sample_data_profile()
        
        assert profile.column_count == 5
        assert profile.row_count == 5
        
        # Check specific columns
        dept_col = profile.get_column_by_name("Department")
        assert dept_col.type == "string"
        
        budget_col = profile.get_column_by_name("Budget")
        assert budget_col.type == "currency"
        
        variance_col = profile.get_column_by_name("Variance")
        assert variance_col.type == "percent"
        
        date_col = profile.get_column_by_name("Date")
        assert date_col.type == "date"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__])
