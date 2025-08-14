#!/usr/bin/env python3
"""
Main entry point for the Gov-Report-AI application.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from data_processor import DataProcessor, create_sample_data_profile
from report_spec import create_sample_report_spec, create_government_report_templates

def main():
    """Main function to run the application."""
    print("Welcome to Gov-Report-AI!")
    print("An AI-powered tool for analyzing and generating government reports.")
    print("=" * 60)
    
    # Demonstrate data processing capabilities
    print("\n1. Creating sample data profile...")
    sample_profile = create_sample_data_profile()
    print(f"   ✓ Generated profile with {sample_profile.column_count} columns and {sample_profile.row_count} rows")
    
    # Show column information
    print("\n2. Column Analysis:")
    for col in sample_profile.columns:
        print(f"   • {col.name}: {col.type} ({col.stats['unique_count']} unique values)")
        if col.sample_values:
            print(f"     Sample: {', '.join(col.sample_values[:3])}")
    
    # Demonstrate report specification
    print("\n3. Creating sample report specification...")
    sample_report = create_sample_report_spec()
    print(f"   ✓ Generated report: {sample_report.title}")
    print(f"   ✓ KPIs: {len(sample_report.kpis)}")
    print(f"   ✓ Charts: {len(sample_report.charts)}")
    print(f"   ✓ Tables: {len(sample_report.tables)}")
    
    # Validate report against data profile
    print("\n4. Validating report specification...")
    validation_errors = sample_report.validate_against_profile(sample_profile)
    if validation_errors:
        print("   ⚠ Validation errors found:")
        for error in validation_errors:
            print(f"     - {error}")
    else:
        print("   ✓ Report specification is valid!")
    
    # Show available templates
    print("\n5. Available Government Report Templates:")
    templates = create_government_report_templates()
    for template_name, template in templates.items():
        print(f"   • {template_name}: {template.title}")
    
    print("\n" + "=" * 60)
    print("Application initialized successfully!")
    print("\nNext steps:")
    print("1. Implement AI planning API (/api/plan-report)")
    print("2. Build report renderer (charts, tables, layout)")
    print("3. Create export engine (PDF, DOCX)")
    print("4. Add web interface for file uploads")
    print("\nCheck the README.md file for setup instructions.")

def demo_data_processing():
    """Demonstrate data processing with a sample CSV."""
    print("\n" + "=" * 60)
    print("Data Processing Demo")
    print("=" * 60)
    
    # Create sample CSV data - using simple format without commas in values
    sample_csv = """Department,Budget,Actual,Variance,Date
Finance,1200000,1180000,-1.67,2024-01-01
Public Works,850000,870000,2.35,2024-01-01
Health,650000,620000,-4.62,2024-01-01
Police,1100000,1050000,-4.55,2024-01-01
Permitting,300000,320000,6.67,2024-01-01"""
    
    try:
        processor = DataProcessor(max_sample_rows=10)
        profile = processor.process_data_from_string(sample_csv, 'csv')
        
        print(f"✓ Processed CSV data: {profile.column_count} columns, {profile.row_count} rows")
        
        # Show detailed column analysis
        print("\nColumn Analysis:")
        for col in profile.columns:
            print(f"  {col.name}:")
            print(f"    Type: {col.type}")
            print(f"    Sample values: {', '.join(col.sample_values[:3])}")
            print(f"    Stats: {col.stats['total_count']} total, {col.stats['unique_count']} unique")
            print()
            
    except Exception as e:
        print(f"Error in data processing demo: {e}")

if __name__ == "__main__":
    main()
    demo_data_processing()
