#!/usr/bin/env python3
"""
Report specification types and structures.
Defines the data models for KPIs, charts, tables, and report specifications.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class MetricType(Enum):
    """Types of metrics that can be calculated."""
    SUM = "sum"
    AVERAGE = "avg"
    MINIMUM = "min"
    MAXIMUM = "max"
    COUNT = "count"
    FORMULA = "formula"


class FormatType(Enum):
    """Format types for displaying values."""
    CURRENCY = "currency"
    PERCENT = "percent"
    NUMBER = "number"
    DATE = "date"
    STRING = "string"


class ChartType(Enum):
    """Types of charts supported."""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"


class SortOrder(Enum):
    """Sort order for data."""
    ASCENDING = "asc"
    DESCENDING = "desc"


@dataclass
class KPI:
    """Key Performance Indicator specification."""
    label: str
    metric: MetricType
    column: Optional[str] = None
    filter: Optional[Dict[str, Any]] = None
    format: Optional[FormatType] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'label': self.label,
            'metric': self.metric.value,
            'column': self.column,
            'filter': self.filter,
            'format': self.format.value if self.format else None,
            'description': self.description
        }


@dataclass
class ChartSeries:
    """Series specification for charts."""
    label: str
    metric: str
    column: str
    filter: Optional[Dict[str, Any]] = None
    color: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'label': self.label,
            'metric': self.metric,
            'column': self.column,
            'filter': self.filter,
            'color': self.color
        }


@dataclass
class ChartSpec:
    """Chart specification."""
    type: ChartType
    title: str
    x: Dict[str, Any]  # { column: string; granularity?: string }
    series: List[ChartSeries]
    sort: Optional[Dict[str, Any]] = None  # { by: string; order: 'asc' | 'desc' }
    limit: Optional[int] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'type': self.type.value,
            'title': self.title,
            'x': self.x,
            'series': [s.to_dict() for s in self.series],
            'sort': self.sort,
            'limit': self.limit,
            'description': self.description
        }


@dataclass
class TableSpec:
    """Table specification."""
    title: str
    columns: List[str]
    sort: Optional[Dict[str, Any]] = None  # { by: string; order: 'asc' | 'desc' }
    limit: Optional[int] = None
    zebra_rows: bool = False
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'title': self.title,
            'columns': self.columns,
            'sort': self.sort,
            'limit': self.limit,
            'zebra_rows': self.zebra_rows,
            'description': self.description
        }


@dataclass
class ReportSpec:
    """Complete report specification."""
    title: str
    kpis: List[KPI] = field(default_factory=list)
    charts: List[ChartSpec] = field(default_factory=list)
    tables: List[TableSpec] = field(default_factory=list)
    narrative_goals: List[str] = field(default_factory=list)
    template: Optional[str] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'title': self.title,
            'kpis': [k.to_dict() for k in self.kpis],
            'charts': [c.to_dict() for c in self.charts],
            'tables': [t.to_dict() for t in self.tables],
            'narrative_goals': self.narrative_goals,
            'template': self.template,
            'description': self.description
        }
    
    def validate_against_profile(self, data_profile) -> List[str]:
        """Validate the report spec against a data profile."""
        errors = []
        
        # Check if all referenced columns exist
        all_columns = {col.name for col in data_profile.columns}
        
        # Validate KPI columns
        for kpi in self.kpis:
            if kpi.column and kpi.column not in all_columns:
                errors.append(f"KPI '{kpi.label}' references non-existent column '{kpi.column}'")
        
        # Validate chart columns
        for chart in self.charts:
            if chart.x.get('column') and chart.x['column'] not in all_columns:
                errors.append(f"Chart '{chart.title}' references non-existent x-axis column '{chart.x['column']}'")
            
            for series in chart.series:
                if series.column not in all_columns:
                    errors.append(f"Chart '{chart.title}' series '{series.label}' references non-existent column '{series.column}'")
        
        # Validate table columns
        for table in self.tables:
            for col in table.columns:
                if col not in all_columns:
                    errors.append(f"Table '{table.title}' references non-existent column '{col}'")
        
        return errors


def create_sample_report_spec() -> ReportSpec:
    """Create a sample report specification for testing."""
    return ReportSpec(
        title="Budget vs Actual Report - Q1 2024",
        kpis=[
            KPI(
                label="Total Budget",
                metric=MetricType.SUM,
                column="Budget",
                format=FormatType.CURRENCY,
                description="Sum of all budget allocations"
            ),
            KPI(
                label="Total Actual",
                metric=MetricType.SUM,
                column="Actual",
                format=FormatType.CURRENCY,
                description="Sum of all actual spending"
            ),
            KPI(
                label="Average Variance",
                metric=MetricType.AVERAGE,
                column="Variance",
                format=FormatType.PERCENT,
                description="Average variance across departments"
            )
        ],
        charts=[
            ChartSpec(
                type=ChartType.BAR,
                title="Budget vs Actual by Department",
                x={"column": "Department"},
                series=[
                    ChartSeries(
                        label="Budget",
                        metric="sum",
                        column="Budget"
                    ),
                    ChartSeries(
                        label="Actual",
                        metric="sum",
                        column="Actual"
                    )
                ],
                description="Comparison of budgeted vs actual spending by department"
            ),
            ChartSpec(
                type=ChartType.PIE,
                title="Budget Distribution",
                x={"column": "Department"},
                series=[
                    ChartSeries(
                        label="Budget Share",
                        metric="sum",
                        column="Budget"
                    )
                ],
                description="Distribution of total budget across departments"
            )
        ],
        tables=[
            TableSpec(
                title="Department Summary",
                columns=["Department", "Budget", "Actual", "Variance"],
                sort={"by": "Budget", "order": "desc"},
                limit=10,
                zebra_rows=True,
                description="Detailed breakdown by department"
            )
        ],
        narrative_goals=[
            "Identify departments with significant budget variances",
            "Highlight areas of over/under spending",
            "Provide recommendations for budget adjustments"
        ],
        template="budget_vs_actual",
        description="Quarterly budget performance report for city departments"
    )


def create_government_report_templates() -> Dict[str, ReportSpec]:
    """Create predefined government report templates."""
    templates = {}
    
    # Budget vs Actual Template
    templates["budget_vs_actual"] = create_sample_report_spec()
    
    # Balance Sheet Template
    templates["balance_sheet"] = ReportSpec(
        title="Balance Sheet Report",
        kpis=[
            KPI(label="Total Assets", metric=MetricType.SUM, column="Assets", format=FormatType.CURRENCY),
            KPI(label="Total Liabilities", metric=MetricType.SUM, column="Liabilities", format=FormatType.CURRENCY),
            KPI(label="Net Position", metric=MetricType.FORMULA, column="NetPosition", format=FormatType.CURRENCY)
        ],
        charts=[
            ChartSpec(
                type=ChartType.PIE,
                title="Asset Distribution",
                x={"column": "AssetCategory"},
                series=[ChartSeries(label="Value", metric="sum", column="Value")]
            )
        ],
        tables=[
            TableSpec(
                title="Asset Breakdown",
                columns=["AssetCategory", "Value", "Percentage"],
                sort={"by": "Value", "order": "desc"}
            )
        ],
        narrative_goals=[
            "Assess financial position and stability",
            "Identify major asset categories",
            "Evaluate debt levels and obligations"
        ],
        template="balance_sheet"
    )
    
    # 311 Response Times Template
    templates["response_times"] = ReportSpec(
        title="311 Response Times Report",
        kpis=[
            KPI(label="Average Response Time", metric=MetricType.AVERAGE, column="ResponseTime", format=FormatType.NUMBER),
            KPI(label="Total Requests", metric=MetricType.COUNT, column="RequestID"),
            KPI(label="On-Time Rate", metric=MetricType.FORMULA, column="OnTimeRate", format=FormatType.PERCENT)
        ],
        charts=[
            ChartSpec(
                type=ChartType.LINE,
                title="Response Times Over Time",
                x={"column": "Date", "granularity": "week"},
                series=[ChartSeries(label="Response Time", metric="avg", column="ResponseTime")]
            )
        ],
        tables=[
            TableSpec(
                title="Response Times by Category",
                columns=["Category", "AvgResponseTime", "TotalRequests", "OnTimeRate"],
                sort={"by": "AvgResponseTime", "order": "asc"}
            )
        ],
        narrative_goals=[
            "Monitor service performance trends",
            "Identify categories with slow response times",
            "Track improvement initiatives"
        ],
        template="response_times"
    )
    
    return templates
