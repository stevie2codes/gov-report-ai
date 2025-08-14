#!/usr/bin/env python3
"""
AI Planning module for converting natural language descriptions to ReportSpec objects.
Uses OpenAI API to intelligently plan government reports based on data profiles.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import asdict
import openai
from dotenv import load_dotenv

# Try relative imports first, fall back to absolute for standalone testing
try:
    from .report_spec import (
        ReportSpec, KPI, ChartSpec, ChartSeries, TableSpec,
        MetricType, FormatType, ChartType, SortOrder
    )
    from .data_processor import DataProfile
except ImportError:
    from report_spec import (
        ReportSpec, KPI, ChartSpec, ChartSeries, TableSpec,
        MetricType, FormatType, ChartType, SortOrder
    )
    from data_processor import DataProfile

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIReportPlanner:
    """AI-powered report planning system."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI planner with OpenAI API key."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def plan_report(
        self, 
        user_description: str, 
        data_profile: DataProfile,
        template_hint: Optional[str] = None
    ) -> ReportSpec:
        """
        Generate a report specification from natural language description.
        
        Args:
            user_description: Natural language description of desired report
            data_profile: Profile of the available data
            template_hint: Optional hint about report template type
            
        Returns:
            ReportSpec object with structured report plan
        """
        try:
            # Create the AI prompt
            prompt = self._create_planning_prompt(user_description, data_profile, template_hint)
            
            # Call OpenAI API
            response = self._call_openai_api(prompt)
            
            # Parse and validate the response
            report_spec = self._parse_ai_response(response, data_profile)
            
            # Validate the generated specification
            validation_errors = report_spec.validate_against_profile(data_profile)
            if validation_errors:
                logger.warning(f"AI generated spec has validation errors: {validation_errors}")
                # Try to fix common issues
                report_spec = self._fix_validation_errors(report_spec, data_profile, validation_errors)
            
            return report_spec
            
        except Exception as e:
            logger.error(f"Error in AI planning: {e}")
            # Fallback to template-based generation
            return self._generate_fallback_spec(user_description, data_profile, template_hint)
    
    def _create_planning_prompt(
        self, 
        user_description: str, 
        data_profile: DataProfile,
        template_hint: Optional[str] = None
    ) -> str:
        """Create the AI prompt for report planning."""
        
        # Convert data profile to JSON for context
        profile_json = json.dumps(data_profile.to_dict(), indent=2)
        
        prompt = f"""
You are an expert government report planner. Your task is to convert a natural language description into a structured report specification.

AVAILABLE DATA:
{profile_json}

USER REQUEST:
{user_description}

TEMPLATE HINT:
{template_hint or 'No specific template requested'}

TASK:
Generate a JSON response that matches this exact schema:

{{
  "title": "Report title",
  "description": "Brief description of the report",
  "kpis": [
    {{
      "label": "KPI label",
      "metric": "sum|avg|min|max|count|formula",
      "column": "column_name",
      "filter": {{"optional": "filtering"}},
      "format": "currency|percent|number|date|string",
      "description": "What this KPI measures"
    }}
  ],
  "charts": [
    {{
      "type": "bar|line|pie",
      "title": "Chart title",
      "x": {{"column": "x_axis_column", "granularity": "optional_time_granularity"}},
      "series": [
        {{
          "label": "Series label",
          "metric": "sum|avg|min|max|count",
          "column": "data_column",
          "filter": {{"optional": "filtering"}},
          "color": "optional_color"
        }}
      ],
      "sort": {{"by": "column_name", "order": "asc|desc"}},
      "limit": 10,
      "description": "What this chart shows"
    }}
  ],
  "tables": [
    {{
      "title": "Table title",
      "columns": ["col1", "col2", "col3"],
      "sort": {{"by": "column_name", "order": "asc|desc"}},
      "limit": 20,
      "zebra_rows": true,
      "description": "What this table shows"
    }}
  ],
  "narrative_goals": [
    "Goal 1: What insights should this report provide",
    "Goal 2: What actions should it enable"
  ],
  "template": "suggested_template_name"
}}

IMPORTANT RULES:
1. Only use columns that exist in the available data
2. Choose appropriate chart types: bar for comparisons, line for trends, pie for distributions
3. KPIs should be meaningful for government decision-making
4. Tables should show detailed breakdowns
5. Narrative goals should be actionable insights
6. Use appropriate formatting (currency for money, percent for ratios, etc.)
7. Keep charts and tables focused and not overwhelming

RESPOND WITH ONLY THE JSON, no other text.
"""
        return prompt
    
    def _call_openai_api(self, prompt: str) -> str:
        """Call OpenAI API to generate the report plan."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert government report planner. Always respond with valid JSON matching the exact schema provided."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent output
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _parse_ai_response(self, response: str, data_profile: DataProfile) -> ReportSpec:
        """Parse the AI response into a ReportSpec object."""
        try:
            # Parse JSON response
            if isinstance(response, str):
                data = json.loads(response)
            else:
                data = response
            
            # Extract KPIs
            kpis = []
            for kpi_data in data.get("kpis", []):
                kpi = KPI(
                    label=kpi_data["label"],
                    metric=MetricType(kpi_data["metric"]),
                    column=kpi_data.get("column"),
                    filter=kpi_data.get("filter"),
                    format=FormatType(kpi_data["format"]) if kpi_data.get("format") else None,
                    description=kpi_data.get("description")
                )
                kpis.append(kpi)
            
            # Extract charts
            charts = []
            for chart_data in data.get("charts", []):
                series = []
                for series_data in chart_data.get("series", []):
                    series_obj = ChartSeries(
                        label=series_data["label"],
                        metric=series_data["metric"],
                        column=series_data["column"],
                        filter=series_data.get("filter"),
                        color=series_data.get("color")
                    )
                    series.append(series_obj)
                
                chart = ChartSpec(
                    type=ChartType(chart_data["type"]),
                    title=chart_data["title"],
                    x=chart_data["x"],
                    series=series,
                    sort=chart_data.get("sort"),
                    limit=chart_data.get("limit"),
                    description=chart_data.get("description")
                )
                charts.append(chart)
            
            # Extract tables
            tables = []
            for table_data in data.get("tables", []):
                table = TableSpec(
                    title=table_data["title"],
                    columns=table_data["columns"],
                    sort=table_data.get("sort"),
                    limit=table_data.get("limit"),
                    zebra_rows=table_data.get("zebra_rows", False),
                    description=table_data.get("description")
                )
                tables.append(table)
            
            # Create ReportSpec
            report_spec = ReportSpec(
                title=data["title"],
                kpis=kpis,
                charts=charts,
                tables=tables,
                narrative_goals=data.get("narrative_goals", []),
                template=data.get("template"),
                description=data.get("description")
            )
            
            return report_spec
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            raise ValueError(f"Failed to parse AI response: {e}")
    
    def _fix_validation_errors(
        self, 
        report_spec: ReportSpec, 
        data_profile: DataProfile, 
        errors: List[str]
    ) -> ReportSpec:
        """Attempt to fix common validation errors in the AI-generated spec."""
        logger.info("Attempting to fix validation errors...")
        
        # Get available column names
        available_columns = {col.name for col in data_profile.columns}
        
        # Fix KPI column references
        for kpi in report_spec.kpis:
            if kpi.column and kpi.column not in available_columns:
                # Try to find a similar column
                similar_col = self._find_similar_column(kpi.column, available_columns)
                if similar_col:
                    kpi.column = similar_col
                    logger.info(f"Fixed KPI column reference: {kpi.column} -> {similar_col}")
        
        # Fix chart column references
        for chart in report_spec.charts:
            if chart.x.get("column") and chart.x["column"] not in available_columns:
                similar_col = self._find_similar_column(chart.x["column"], available_columns)
                if similar_col:
                    chart.x["column"] = similar_col
            
            for series in chart.series:
                if series.column not in available_columns:
                    similar_col = self._find_similar_column(series.column, available_columns)
                    if similar_col:
                        series.column = similar_col
        
        # Fix table column references
        for table in report_spec.tables:
            fixed_columns = []
            for col in table.columns:
                if col not in available_columns:
                    similar_col = self._find_similar_column(col, available_columns)
                    if similar_col:
                        fixed_columns.append(similar_col)
                    else:
                        fixed_columns.append(col)  # Keep original if no match found
                else:
                    fixed_columns.append(col)
            table.columns = fixed_columns
        
        return report_spec
    
    def _find_similar_column(self, target: str, available: set) -> Optional[str]:
        """Find a similar column name in the available columns."""
        target_lower = target.lower()
        
        # Exact match
        if target in available:
            return target
        
        # Case-insensitive match
        for col in available:
            if col.lower() == target_lower:
                return col
        
        # Partial match
        for col in available:
            if target_lower in col.lower() or col.lower() in target_lower:
                return col
        
        # Fuzzy match (simple)
        for col in available:
            if any(word in col.lower() for word in target_lower.split()):
                return col
        
        return None
    
    def _generate_fallback_spec(
        self, 
        user_description: str, 
        data_profile: DataProfile,
        template_hint: Optional[str] = None
    ) -> ReportSpec:
        """Generate a fallback report specification when AI planning fails."""
        logger.info("Generating fallback report specification...")
        
        # Create a simple fallback based on available data
        numeric_columns = data_profile.get_columns_by_type("number")
        string_columns = data_profile.get_columns_by_type("string")
        date_columns = data_profile.get_columns_by_type("date")
        
        # Basic KPI
        kpis = []
        if numeric_columns:
            kpis.append(KPI(
                label=f"Total {numeric_columns[0].name}",
                metric=MetricType.SUM,
                column=numeric_columns[0].name,
                format=FormatType.NUMBER,
                description=f"Sum of {numeric_columns[0].name}"
            ))
        
        # Basic chart
        charts = []
        if string_columns and numeric_columns:
            charts.append(ChartSpec(
                type=ChartType.BAR,
                title=f"{numeric_columns[0].name} by {string_columns[0].name}",
                x={"column": string_columns[0].name},
                series=[
                    ChartSeries(
                        label=numeric_columns[0].name,
                        metric="sum",
                        column=numeric_columns[0].name
                    )
                ],
                description=f"Distribution of {numeric_columns[0].name} across {string_columns[0].name}"
            ))
        
        # Basic table
        tables = []
        if data_profile.columns:
            table_columns = [col.name for col in data_profile.columns[:5]]  # First 5 columns
            tables.append(TableSpec(
                title="Data Summary",
                columns=table_columns,
                limit=20,
                zebra_rows=True,
                description="Summary of the dataset"
            ))
        
        return ReportSpec(
            title=f"Report: {user_description[:50]}...",
            kpis=kpis,
            charts=charts,
            tables=tables,
            narrative_goals=[
                "Provide overview of the available data",
                "Identify key patterns and trends"
            ],
            description="Fallback report generated due to AI planning error"
        )


def create_sample_ai_plan() -> Dict[str, Any]:
    """Create a sample AI plan for testing purposes."""
    return {
        "title": "Budget Performance Analysis",
        "description": "Analysis of budget vs actual spending across departments",
        "kpis": [
            {
                "label": "Total Budget",
                "metric": "sum",
                "column": "Budget",
                "format": "currency",
                "description": "Total budget allocation across all departments"
            },
            {
                "label": "Total Variance",
                "metric": "avg",
                "column": "Variance",
                "format": "percent",
                "description": "Average variance from budget"
            }
        ],
        "charts": [
            {
                "type": "bar",
                "title": "Budget vs Actual by Department",
                "x": {"column": "Department"},
                "series": [
                    {
                        "label": "Budget",
                        "metric": "sum",
                        "column": "Budget"
                    },
                    {
                        "label": "Actual",
                        "metric": "sum",
                        "column": "Actual"
                    }
                ],
                "description": "Comparison of budgeted vs actual spending"
            }
        ],
        "tables": [
            {
                "title": "Department Performance",
                "columns": ["Department", "Budget", "Actual", "Variance"],
                "sort": {"by": "Variance", "order": "desc"},
                "limit": 10,
                "zebra_rows": True,
                "description": "Detailed breakdown by department"
            }
        ],
        "narrative_goals": [
            "Identify departments with significant budget variances",
            "Highlight areas requiring budget adjustments"
        ],
        "template": "budget_vs_actual"
    }
