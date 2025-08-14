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
            return self._generate_fallback_report(data_profile, user_description, template_hint)
    
    def _create_planning_prompt(
        self, 
        user_description: str, 
        data_profile: DataProfile,
        template_hint: Optional[str] = None
    ) -> str:
        """Create the AI prompt for report planning with enhanced GPT-5 capabilities."""
        
        # Convert data profile to JSON for context
        profile_json = json.dumps(data_profile.to_dict(), indent=2)
        
        prompt = f"""
You are an expert government report planner with deep expertise in data analysis, government operations, and regulatory compliance. Your task is to convert a natural language description into a sophisticated, actionable report specification that leverages GPT-5's advanced capabilities.

AVAILABLE DATA:
{profile_json}

USER REQUEST:
{user_description}

TEMPLATE HINT:
{template_hint or 'No specific template requested - use your expertise to determine the best approach'}

TASK:
Generate a comprehensive JSON response that matches this exact schema, leveraging GPT-5's advanced reasoning:

{{
  "title": "Professional, government-appropriate report title",
  "description": "Detailed description explaining the report's purpose and value",
  "kpis": [
    {{
      "label": "Professional KPI label",
      "metric": "sum|avg|min|max|count|formula",
      "column": "column_name",
      "filter": {{"optional": "advanced_filtering_logic"}},
      "format": "currency|percent|number|date|string",
      "description": "Clear explanation of what this KPI measures and why it matters"
    }}
  ],
  "charts": [
    {{
      "type": "bar|line|pie|area|scatter|radar",
      "title": "Professional chart title",
      "x": {{"column": "x_axis_column", "granularity": "optional_time_granularity"}},
      "series": [
        {{
          "label": "Professional series label",
          "metric": "sum|avg|min|max|count",
          "column": "data_column",
          "filter": {{"optional": "advanced_filtering"}},
          "color": "optional_color"
        }}
      ],
      "sort": {{"by": "column_name", "order": "asc|desc"}},
      "limit": 10,
      "description": "Clear explanation of what insights this chart provides"
    }}
  ],
  "tables": [
    {{
      "title": "Professional table title",
      "columns": ["col1", "col2", "col3"],
      "sort": {{"by": "column_name", "order": "asc|desc"}},
      "limit": 20,
      "zebra_rows": true,
      "description": "Clear explanation of what this table shows and its value"
    }}
  ],
  "narrative_goals": [
    "Strategic Goal 1: What high-level insights should this report provide",
    "Operational Goal 2: What specific actions should it enable",
    "Compliance Goal 3: What regulatory or policy requirements should it address",
    "Stakeholder Goal 4: What information do different audiences need"
  ],
  "template": "suggested_template_name",
  "data_insights": [
    "Key insight 1: What patterns or anomalies should be highlighted",
    "Key insight 2: What trends or correlations should be analyzed",
    "Key insight 3: What benchmarks or comparisons would be valuable"
  ],
  "recommendations": [
    "Recommendation 1: Specific, actionable next steps",
    "Recommendation 2: Policy or process improvements",
    "Recommendation 3: Resource allocation or budget considerations"
  ]
}}

ADVANCED REQUIREMENTS (GPT-5 Capabilities):
1. **Data Intelligence**: Analyze the data profile to identify the most meaningful patterns, correlations, and insights
2. **Government Context**: Consider regulatory requirements, compliance needs, and public accountability
3. **Stakeholder Analysis**: Design reports that serve multiple audiences (executives, managers, staff, public)
4. **Actionable Insights**: Focus on metrics and visualizations that drive decision-making
5. **Risk Assessment**: Identify potential issues, anomalies, or areas requiring attention
6. **Performance Benchmarking**: Suggest appropriate comparisons and targets
7. **Trend Analysis**: Leverage temporal data for forecasting and planning
8. **Cost-Benefit Analysis**: Where applicable, include efficiency and ROI metrics

CHART SELECTION INTELLIGENCE:
- **Bar Charts**: For categorical comparisons, department performance, budget vs actual
- **Line Charts**: For time series, trends, progress over time
- **Pie Charts**: For composition analysis, budget allocation, resource distribution
- **Area Charts**: For cumulative data, stacked comparisons
- **Scatter Plots**: For correlation analysis, outlier detection
- **Radar Charts**: For multi-dimensional performance assessment

KPI INTELLIGENCE:
- **Financial KPIs**: Revenue, expenses, variance, efficiency ratios
- **Operational KPIs**: Performance metrics, response times, quality scores
- **Compliance KPIs**: Audit results, violation rates, completion percentages
- **Strategic KPIs**: Goal achievement, milestone progress, strategic alignment

IMPORTANT RULES:
1. **Data Validation**: Only use columns that exist in the available data
2. **Government Standards**: Follow government reporting best practices
3. **Accessibility**: Ensure reports are clear for diverse audiences
4. **Actionability**: Every metric should support decision-making
5. **Compliance**: Consider regulatory and policy requirements
6. **Efficiency**: Focus on high-impact, low-effort insights
7. **Innovation**: Leverage GPT-5's capabilities for creative analysis approaches

RESPOND WITH ONLY THE JSON, no other text. Make this report specification exceptional and government-ready.
"""
        return prompt
    
    def _call_openai_api(self, prompt: str) -> str:
        """Call OpenAI API to generate the report plan using GPT-5's advanced capabilities."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert government report planner with deep expertise in data analysis, government operations, and regulatory compliance. Always respond with valid JSON matching the exact schema provided. Leverage GPT-5's advanced reasoning capabilities to create exceptional, government-ready report specifications."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Lower temperature for more consistent, professional output
                max_tokens=3000,  # Increased for more comprehensive reports
                response_format={"type": "json_object"},
                top_p=0.9,  # Focus on most relevant responses
                frequency_penalty=0.1,  # Encourage diverse, creative solutions
                presence_penalty=0.1,  # Encourage comprehensive coverage
                seed=42  # Consistent results for similar inputs
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
    
    def _generate_fallback_report(
        self, 
        data_profile: DataProfile, 
        user_description: str,
        template_hint: Optional[str] = None
    ) -> ReportSpec:
        """Generate a fallback report specification when AI planning fails."""
        logger.info("Generating fallback report specification...")
        
        # Analyze the data profile to create a more intelligent fallback
        numeric_columns = data_profile.get_columns_by_type("number")
        string_columns = data_profile.get_columns_by_type("string")
        date_columns = data_profile.get_columns_by_type("date")
        currency_columns = data_profile.get_columns_by_type("currency")
        percent_columns = data_profile.get_columns_by_type("percent")
        
        # Determine report type based on data characteristics
        report_type = self._determine_report_type_from_data(data_profile)
        
        # Create KPIs based on report type
        kpis = self._create_kpis_for_report_type(report_type, data_profile)
        
        # Create charts based on report type
        charts = self._create_charts_for_report_type(report_type, data_profile)
        
        # Create tables based on report type
        tables = self._create_tables_for_report_type(report_type, data_profile)
        
        # Create narrative goals based on report type
        narrative_goals = self._create_narrative_for_report_type(report_type, data_profile)
        
        return ReportSpec(
            title=f"{report_type['title']}: {user_description[:50]}...",
            kpis=kpis,
            charts=charts,
            tables=tables,
            narrative_goals=narrative_goals,
            description=f"Intelligent fallback report for {report_type['name']} data"
        )
    
    def _determine_report_type_from_data(self, data_profile: DataProfile) -> Dict[str, Any]:
        """Determine the most appropriate report type based on data characteristics."""
        numeric_columns = data_profile.get_columns_by_type("number")
        string_columns = data_profile.get_columns_by_type("string")
        date_columns = data_profile.get_columns_by_type("date")
        currency_columns = data_profile.get_columns_by_type("currency")
        
        # Check for budget/performance patterns
        budget_keywords = ['budget', 'actual', 'planned', 'allocated', 'spent', 'expended']
        dept_keywords = ['department', 'division', 'unit', 'agency', 'bureau']
        
        has_budget_data = any(
            any(keyword in col.name.lower() for keyword in budget_keywords)
            for col in numeric_columns + currency_columns
        )
        
        has_dept_data = any(
            any(keyword in col.name.lower() for keyword in dept_keywords)
            for col in string_columns
        )
        
        if has_budget_data and has_dept_data:
            return {
                'name': 'budget_performance',
                'title': 'Budget Performance Analysis',
                'description': 'Analysis of budget vs actual spending across departments'
            }
        
        # Check for financial data
        financial_keywords = ['revenue', 'income', 'expense', 'cost', 'amount', 'total']
        has_financial_data = any(
            any(keyword in col.name.lower() for keyword in financial_keywords)
            for col in numeric_columns + currency_columns
        )
        
        if has_financial_data:
            return {
                'name': 'financial_summary',
                'title': 'Financial Summary Report',
                'description': 'Comprehensive financial overview and analysis'
            }
        
        # Check for operational metrics
        metric_keywords = ['score', 'rating', 'performance', 'efficiency', 'target']
        has_metrics = any(
            any(keyword in col.name.lower() for keyword in metric_keywords)
            for col in numeric_columns + percent_columns
        )
        
        if has_metrics:
            return {
                'name': 'operational_metrics',
                'title': 'Operational Metrics Report',
                'description': 'Performance indicators and operational analysis'
            }
        
        # Check for trend analysis
        if date_columns and numeric_columns:
            return {
                'name': 'trend_analysis',
                'title': 'Trend Analysis Report',
                'description': 'Time-series analysis and trend identification'
            }
        
        # Default to data summary
        return {
            'name': 'data_summary',
            'title': 'Data Summary Report',
            'description': 'Comprehensive overview of the dataset'
        }
    
    def _create_kpis_for_report_type(self, report_type: Dict[str, Any], data_profile: DataProfile) -> List[KPI]:
        """Create appropriate KPIs based on report type."""
        kpis = []
        numeric_columns = data_profile.get_columns_by_type("number")
        currency_columns = data_profile.get_columns_by_type("currency")
        percent_columns = data_profile.get_columns_by_type("percent")
        
        if report_type['name'] == 'budget_performance':
            # Look for budget-related columns
            budget_cols = [col for col in numeric_columns + currency_columns 
                          if any(keyword in col.name.lower() 
                                for keyword in ['budget', 'planned', 'allocated'])]
            actual_cols = [col for col in numeric_columns + currency_columns 
                          if any(keyword in col.name.lower() 
                                for keyword in ['actual', 'spent', 'expended'])]
            
            if budget_cols and actual_cols:
                kpis.extend([
                    KPI(label="Total Budget", metric=MetricType.SUM, column=budget_cols[0].name, format=FormatType.CURRENCY),
                    KPI(label="Total Actual", metric=MetricType.SUM, column=actual_cols[0].name, format=FormatType.CURRENCY),
                    KPI(label="Budget Variance", metric=MetricType.AVG, column="Variance", format=FormatType.PERCENT)
                ])
        
        elif report_type['name'] == 'financial_summary':
            # Look for financial columns
            financial_cols = [col for col in numeric_columns + currency_columns 
                            if any(keyword in col.name.lower() 
                                  for keyword in ['revenue', 'income', 'amount', 'total'])]
            
            if financial_cols:
                kpis.extend([
                    KPI(label=f"Total {financial_cols[0].name.title()}", metric=MetricType.SUM, 
                        column=financial_cols[0].name, format=FormatType.CURRENCY),
                    KPI(label=f"Average {financial_cols[0].name.title()}", metric=MetricType.AVG, 
                        column=financial_cols[0].name, format=FormatType.CURRENCY)
                ])
        
        elif report_type['name'] == 'operational_metrics':
            # Look for metric columns
            metric_cols = [col for col in numeric_columns + percent_columns 
                          if any(keyword in col.name.lower() 
                                for keyword in ['score', 'rating', 'performance'])]
            
            if metric_cols:
                kpis.extend([
                    KPI(label=f"Average {metric_cols[0].name.title()}", metric=MetricType.AVG, 
                        column=metric_cols[0].name, format=FormatType.NUMBER),
                    KPI(label=f"Best {metric_cols[0].name.title()}", metric=MetricType.MAX, 
                        column=metric_cols[0].name, format=FormatType.NUMBER)
                ])
        
        # Add a general KPI if none were created
        if not kpis and numeric_columns:
            kpis.append(KPI(
                label=f"Total {numeric_columns[0].name.title()}", 
                metric=MetricType.SUM, 
                column=numeric_columns[0].name, 
                format=FormatType.NUMBER
            ))
        
        return kpis
    
    def _create_charts_for_report_type(self, report_type: Dict[str, Any], data_profile: DataProfile) -> List[ChartSpec]:
        """Create appropriate charts based on report type."""
        charts = []
        numeric_columns = data_profile.get_columns_by_type("number")
        string_columns = data_profile.get_columns_by_type("string")
        date_columns = data_profile.get_columns_by_type("date")
        
        if report_type['name'] == 'budget_performance' and string_columns and numeric_columns:
            # Budget vs Actual bar chart
            budget_cols = [col for col in numeric_columns 
                          if any(keyword in col.name.lower() 
                                for keyword in ['budget', 'planned', 'allocated'])]
            actual_cols = [col for col in numeric_columns 
                          if any(keyword in col.name.lower() 
                                for keyword in ['actual', 'spent', 'expended'])]
            dept_cols = [col for col in string_columns 
                        if any(keyword in col.name.lower() 
                              for keyword in ['department', 'division', 'unit'])]
            
            if budget_cols and actual_cols and dept_cols:
                charts.append(ChartSpec(
                    type=ChartType.BAR,
                    title="Budget vs Actual by Department",
                    x={"column": dept_cols[0].name},
                    series=[
                        ChartSeries(label="Budget", metric="sum", column=budget_cols[0].name),
                        ChartSeries(label="Actual", metric="sum", column=actual_cols[0].name)
                    ],
                    description="Comparison of budgeted vs actual spending across departments"
                ))
        
        elif report_type['name'] == 'trend_analysis' and date_columns and numeric_columns:
            # Time series chart
            charts.append(ChartSpec(
                type=ChartType.LINE,
                title=f"{numeric_columns[0].name.title()} Over Time",
                x={"column": date_columns[0].name},
                series=[
                    ChartSeries(label=numeric_columns[0].name.title(), metric="sum", column=numeric_columns[0].name)
                ],
                description=f"Trend analysis of {numeric_columns[0].name} over time"
            ))
        
        elif string_columns and numeric_columns:
            # Generic distribution chart
            charts.append(ChartSpec(
                type=ChartType.BAR,
                title=f"{numeric_columns[0].name.title()} by {string_columns[0].name.title()}",
                x={"column": string_columns[0].name},
                series=[
                    ChartSeries(label=numeric_columns[0].name.title(), metric="sum", column=numeric_columns[0].name)
                ],
                description=f"Distribution of {numeric_columns[0].name} across {string_columns[0].name}"
            ))
        
        return charts
    
    def _create_tables_for_report_type(self, report_type: Dict[str, Any], data_profile: DataProfile) -> List[TableSpec]:
        """Create appropriate tables based on report type."""
        tables = []
        
        if data_profile.columns:
            # Create a summary table with key columns
            key_columns = [col.name for col in data_profile.columns[:5]]  # First 5 columns
            tables.append(TableSpec(
                title=f"{report_type['title']} - Data Summary",
                columns=key_columns,
                limit=20,
                zebra_rows=True,
                description=f"Summary data for {report_type['name'].replace('_', ' ').title()}"
            ))
        
        return tables
    
    def _create_narrative_for_report_type(self, report_type: Dict[str, Any], data_profile: DataProfile) -> List[str]:
        """Create narrative goals based on report type."""
        if report_type['name'] == 'budget_performance':
            return [
                "Analyze budget performance across departments",
                "Identify areas of over/under spending",
                "Provide recommendations for budget optimization"
            ]
        elif report_type['name'] == 'financial_summary':
            return [
                "Summarize key financial metrics",
                "Identify revenue and expense patterns",
                "Highlight financial performance insights"
            ]
        elif report_type['name'] == 'operational_metrics':
            return [
                "Assess operational performance indicators",
                "Identify areas for improvement",
                "Track progress against targets"
            ]
        elif report_type['name'] == 'trend_analysis':
            return [
                "Identify key trends and patterns",
                "Analyze seasonal variations",
                "Forecast future performance"
            ]
        else:
            return [
                "Provide comprehensive data overview",
                "Identify key patterns and insights",
                "Support data-driven decision making"
            ]


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
