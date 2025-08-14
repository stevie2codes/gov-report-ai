#!/usr/bin/env python3
"""
Report type suggestion module that analyzes data profiles and suggests appropriate report types.
"""

import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReportTypeSuggester:
    """Suggests report types based on data profile analysis."""
    
    def __init__(self):
        # Define report type patterns and their characteristics
        self.report_patterns = {
            'budget_performance': {
                'name': 'Budget Performance Report',
                'description': 'Analysis of budget vs actual spending with variance calculations',
                'keywords': ['budget', 'actual', 'spending', 'expense', 'cost', 'variance'],
                'required_columns': [
                    ['budget', 'planned', 'allocated', 'appropriated', 'authorized', 'estimated'],
                    ['actual', 'spent', 'expended', 'incurred', 'paid', 'disbursed']
                ],
                'optional_columns': ['department', 'category', 'date', 'variance', 'percentage', 'division', 'unit', 'program', 'fund'],
                'chart_types': ['bar', 'line', 'pie'],
                'kpi_types': ['sum', 'avg', 'variance'],
                'confidence_threshold': 0.6
            },
            'financial_summary': {
                'name': 'Financial Summary Report',
                'description': 'Comprehensive financial overview with key metrics and trends',
                'keywords': ['revenue', 'income', 'profit', 'loss', 'financial', 'fiscal'],
                'required_columns': [
                    ['amount', 'revenue', 'income', 'receipts', 'collections', 'funds', 'total', 'value']
                ],
                'optional_columns': ['date', 'category', 'department', 'type', 'period', 'quarter', 'year', 'fiscal'],
                'chart_types': ['line', 'bar', 'area'],
                'kpi_types': ['sum', 'avg', 'trend'],
                'confidence_threshold': 0.5
            },
            'operational_metrics': {
                'name': 'Operational Metrics Report',
                'description': 'Performance indicators and operational efficiency analysis',
                'keywords': ['performance', 'efficiency', 'metrics', 'kpi', 'target', 'goal'],
                'required_columns': [
                    ['metric', 'value', 'target', 'goal', 'performance', 'score', 'rating', 'efficiency']
                ],
                'optional_columns': ['date', 'department', 'category', 'status', 'period', 'quarter', 'month'],
                'chart_types': ['gauge', 'bar', 'line'],
                'kpi_types': ['comparison', 'percentage', 'trend'],
                'confidence_threshold': 0.5
            },
            'department_comparison': {
                'name': 'Department Comparison Report',
                'description': 'Cross-departmental analysis and benchmarking',
                'keywords': ['department', 'division', 'unit', 'compare', 'benchmark'],
                'required_columns': [
                    ['department', 'division', 'unit', 'agency', 'bureau', 'office', 'section', 'team', 'program']
                ],
                'optional_columns': ['category', 'date', 'budget', 'actual', 'performance', 'metric', 'value'],
                'chart_types': ['bar', 'radar', 'table'],
                'kpi_types': ['comparison', 'ranking', 'percentage'],
                'confidence_threshold': 0.6
            },
            'trend_analysis': {
                'name': 'Trend Analysis Report',
                'description': 'Time-series analysis showing patterns and trends over time',
                'keywords': ['date', 'time', 'trend', 'pattern', 'growth', 'decline'],
                'required_columns': [
                    ['date', 'time', 'period', 'quarter', 'month', 'year', 'fiscal', 'reporting']
                ],
                'optional_columns': ['category', 'department', 'metric', 'value', 'performance'],
                'chart_types': ['line', 'area', 'scatter'],
                'kpi_types': ['trend', 'growth_rate', 'forecast'],
                'confidence_threshold': 0.7
            },
            'compliance_summary': {
                'name': 'Compliance Summary Report',
                'description': 'Regulatory compliance status and audit findings',
                'keywords': ['compliance', 'audit', 'regulation', 'status', 'finding', 'violation'],
                'required_columns': [
                    ['status', 'compliance', 'audit', 'finding', 'violation', 'regulation', 'requirement']
                ],
                'optional_columns': ['date', 'department', 'regulation', 'finding', 'severity', 'action'],
                'chart_types': ['pie', 'bar', 'table'],
                'kpi_types': ['percentage', 'count', 'status'],
                'confidence_threshold': 0.6
            },
            'resource_allocation': {
                'name': 'Resource Allocation Report',
                'description': 'Resource distribution and utilization analysis',
                'keywords': ['resource', 'allocation', 'utilization', 'capacity', 'workload'],
                'required_columns': [
                    ['resource', 'allocation', 'utilization', 'capacity', 'workload', 'staffing', 'fte', 'hours']
                ],
                'optional_columns': ['department', 'date', 'utilization', 'capacity', 'efficiency', 'productivity'],
                'chart_types': ['pie', 'bar', 'gauge'],
                'kpi_types': ['percentage', 'efficiency', 'utilization'],
                'confidence_threshold': 0.5
            },
            'customer_service': {
                'name': 'Customer Service Report',
                'description': 'Service quality metrics and customer satisfaction analysis',
                'keywords': ['customer', 'service', 'satisfaction', 'response', 'quality'],
                'required_columns': [
                    ['satisfaction', 'response_time', 'quality', 'rating', 'score', 'feedback', 'complaint']
                ],
                'optional_columns': ['date', 'agent', 'category', 'rating', 'department', 'service_type'],
                'chart_types': ['gauge', 'bar', 'line'],
                'kpi_types': ['avg', 'percentage', 'trend'],
                'confidence_threshold': 0.5
            },
            'inventory_management': {
                'name': 'Inventory Management Report',
                'description': 'Stock levels, turnover rates, and inventory optimization',
                'keywords': ['inventory', 'stock', 'turnover', 'level', 'supply'],
                'required_columns': [
                    ['inventory', 'stock', 'turnover', 'level', 'supply', 'quantity', 'count', 'amount']
                ],
                'optional_columns': ['date', 'category', 'location', 'turnover', 'supplier', 'cost'],
                'chart_types': ['bar', 'line', 'pie'],
                'kpi_types': ['count', 'turnover_rate', 'efficiency'],
                'confidence_threshold': 0.6
            },
            'project_status': {
                'name': 'Project Status Report',
                'description': 'Project progress, milestones, and completion tracking',
                'keywords': ['project', 'status', 'progress', 'milestone', 'completion'],
                'required_columns': [
                    ['status', 'progress', 'milestone', 'completion', 'phase', 'stage', 'task']
                ],
                'optional_columns': ['date', 'project', 'milestone', 'completion', 'manager', 'budget'],
                'chart_types': ['gantt', 'bar', 'pie'],
                'kpi_types': ['percentage', 'count', 'timeline'],
                'confidence_threshold': 0.6
            }
        }
    
    def suggest_report_types(self, data_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze data profile and suggest appropriate report types."""
        try:
            suggestions = []
            columns = data_profile.get('columns', [])
            column_names = [col.get('name', '').lower() for col in columns]
            column_types = {col.get('name', '').lower(): col.get('type', '') for col in columns}
            
            # Analyze each report type pattern
            for report_key, pattern in self.report_patterns.items():
                confidence_score = self._calculate_confidence(
                    pattern, column_names, column_types, columns
                )
                
                if confidence_score >= pattern['confidence_threshold']:
                    suggestion = {
                        'type': report_key,
                        'name': pattern['name'],
                        'description': pattern['description'],
                        'confidence': confidence_score,
                        'confidence_level': self._get_confidence_level(confidence_score),
                        'recommended_charts': pattern['chart_types'],
                        'recommended_kpis': pattern['kpi_types'],
                        'data_insights': self._generate_data_insights(report_key, columns),
                        'sample_questions': self._generate_sample_questions(report_key, columns)
                    }
                    suggestions.append(suggestion)
            
            # Sort by confidence score (highest first)
            suggestions.sort(key=lambda x: x['confidence'], reverse=True)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting report types: {e}")
            return []
    
    def _calculate_confidence(self, pattern: Dict[str, Any], column_names: List[str], 
                             column_types: Dict[str, str], columns: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for a report type based on data profile."""
        score = 0.0
        total_possible = 0.0
        
        # Check required columns (now each required column can have multiple acceptable names)
        required_score = 0.0
        for required_col_patterns in pattern['required_columns']:
            total_possible += 1.0
            # Check if any column name matches any of the acceptable patterns
            if any(any(pattern.lower() in col_name.lower() for pattern in required_col_patterns) for col_name in column_names):
                required_score += 1.0
            elif any(any(self._is_similar_column(pattern, col_name) for pattern in required_col_patterns) for col_name in column_names):
                required_score += 0.8
        
        # Required columns get higher weight
        if required_score > 0:
            score += (required_score / total_possible) * 0.6
        
        # Check optional columns
        optional_score = 0.0
        optional_count = 0
        for optional_col in pattern['optional_columns']:
            if any(optional_col.lower() in col_name.lower() for col_name in column_names):
                optional_score += 1.0
                optional_count += 1
            elif any(self._is_similar_column(optional_col, col_name) for col_name in column_names):
                optional_score += 0.8
                optional_count += 1
        
        if optional_count > 0:
            score += (optional_score / optional_count) * 0.3
        
        # Check data types compatibility
        type_score = self._check_type_compatibility(pattern, column_types)
        score += type_score * 0.1
        
        return min(score, 1.0)
    
    def _is_similar_column(self, target: str, actual: str) -> bool:
        """Check if column names are similar (for fuzzy matching)."""
        target_words = set(re.findall(r'\w+', target.lower()))
        actual_words = set(re.findall(r'\w+', actual.lower()))
        
        if not target_words or not actual_words:
            return False
        
        # Calculate similarity based on word overlap
        intersection = target_words.intersection(actual_words)
        union = target_words.union(actual_words)
        
        if union:
            similarity = len(intersection) / len(union)
            return similarity >= 0.5
        
        return False
    
    def _check_type_compatibility(self, pattern: Dict[str, Any], column_types: Dict[str, str]) -> float:
        """Check if data types are compatible with the report type."""
        score = 0.0
        
        # For trend analysis, we need date columns
        if pattern.get('type') == 'trend_analysis':
            if any(col_type == 'date' for col_type in column_types.values()):
                score += 1.0
        
        # For financial reports, we need numeric columns
        if pattern.get('type') in ['budget_performance', 'financial_summary']:
            numeric_count = sum(1 for col_type in column_types.values() if col_type == 'number')
            if numeric_count >= 2:
                score += 1.0
            elif numeric_count >= 1:
                score += 0.5
        
        # For comparison reports, we need categorical columns
        if pattern.get('type') == 'department_comparison':
            if any(col_type == 'string' for col_type in column_types.values()):
                score += 1.0
        
        return score
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Convert confidence score to human-readable level."""
        if confidence >= 0.9:
            return "Excellent Match"
        elif confidence >= 0.8:
            return "Very Good Match"
        elif confidence >= 0.7:
            return "Good Match"
        elif confidence >= 0.6:
            return "Fair Match"
        else:
            return "Weak Match"
    
    def _generate_data_insights(self, report_type: str, columns: List[Dict[str, Any]]) -> List[str]:
        """Generate insights about what the data can reveal for this report type."""
        insights = []
        
        if report_type == 'budget_performance':
            insights.extend([
                "Compare budgeted vs actual spending across departments",
                "Identify areas of budget overruns or savings",
                "Calculate variance percentages and trends",
                "Highlight departments with significant budget deviations"
            ])
        elif report_type == 'trend_analysis':
            insights.extend([
                "Show patterns and trends over time",
                "Identify seasonal variations and growth rates",
                "Forecast future performance based on historical data",
                "Highlight periods of peak performance or decline"
            ])
        elif report_type == 'department_comparison':
            insights.extend([
                "Benchmark departments against each other",
                "Identify top and bottom performers",
                "Show relative performance rankings",
                "Highlight best practices from leading departments"
            ])
        elif report_type == 'operational_metrics':
            insights.extend([
                "Track key performance indicators over time",
                "Compare actual vs target performance",
                "Identify areas needing improvement",
                "Show efficiency trends and patterns"
            ])
        
        return insights[:3]  # Limit to top 3 insights
    
    def _generate_sample_questions(self, report_type: str, columns: List[Dict[str, Any]]) -> List[str]:
        """Generate sample questions users can ask for this report type."""
        questions = []
        
        if report_type == 'budget_performance':
            questions.extend([
                "Which departments are over or under budget?",
                "What is the overall budget variance percentage?",
                "How does this quarter's spending compare to last quarter?",
                "Which budget categories have the highest variances?"
            ])
        elif report_type == 'trend_analysis':
            questions.extend([
                "What are the trends in our key metrics over time?",
                "Are we showing consistent growth or decline?",
                "What seasonal patterns exist in our data?",
                "How can we forecast future performance?"
            ])
        elif report_type == 'department_comparison':
            questions.extend([
                "Which departments are performing best?",
                "How do departments rank against each other?",
                "What are the performance gaps between departments?",
                "Which departments can learn from others?"
            ])
        elif report_type == 'operational_metrics':
            questions.extend([
                "Are we meeting our performance targets?",
                "Which metrics show improvement or decline?",
                "What are our efficiency trends?",
                "Where should we focus improvement efforts?"
            ])
        
        return questions[:3]  # Limit to top 3 questions
    
    def get_report_template_suggestions(self, data_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive report suggestions including templates and examples."""
        suggestions = self.suggest_report_types(data_profile)
        
        return {
            'data_summary': {
                'total_columns': data_profile.get('column_count', 0),
                'total_rows': data_profile.get('row_count', 0),
                'column_types': self._summarize_column_types(data_profile.get('columns', [])),
                'data_quality': self._assess_data_quality(data_profile)
            },
            'report_suggestions': suggestions,
            'recommendations': self._generate_recommendations(suggestions, data_profile),
            'generated_at': datetime.now().isoformat()
        }
    
    def _summarize_column_types(self, columns: List[Dict[str, Any]]) -> Dict[str, int]:
        """Summarize the distribution of column types."""
        type_counts = {}
        for col in columns:
            col_type = col.get('type', 'unknown')
            type_counts[col_type] = type_counts.get(col_type, 0) + 1
        return type_counts
    
    def _assess_data_quality(self, data_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality and characteristics of the data."""
        columns = data_profile.get('columns', [])
        
        quality_metrics = {
            'has_dates': any(col.get('type') == 'date' for col in columns),
            'has_numbers': any(col.get('type') == 'number' for col in columns),
            'has_categories': any(col.get('type') == 'string' for col in columns),
            'data_completeness': self._calculate_completeness(columns),
            'suitable_for_trends': any(col.get('type') == 'date' for col in columns),
            'suitable_for_comparisons': len([col for col in columns if col.get('type') == 'string']) >= 2
        }
        
        return quality_metrics
    
    def _calculate_completeness(self, columns: List[Dict[str, Any]]) -> float:
        """Calculate overall data completeness score."""
        if not columns:
            return 0.0
        
        total_completeness = 0.0
        for col in columns:
            stats = col.get('stats', {})
            total_count = stats.get('total_count', 0)
            null_count = stats.get('null_count', 0)
            
            if total_count > 0:
                completeness = (total_count - null_count) / total_count
                total_completeness += completeness
        
        return total_completeness / len(columns)
    
    def _generate_recommendations(self, suggestions: List[Dict[str, Any]], 
                                 data_profile: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on data and suggestions."""
        recommendations = []
        
        if not suggestions:
            recommendations.append("Consider adding more structured data with clear categories and metrics")
            recommendations.append("Include date columns for trend analysis capabilities")
            recommendations.append("Add numeric columns for quantitative analysis")
            return recommendations
        
        # Top suggestion recommendations
        top_suggestion = suggestions[0]
        if top_suggestion['confidence'] >= 0.8:
            recommendations.append(f"'{top_suggestion['name']}' is an excellent choice for your data")
            recommendations.append(f"Focus on {', '.join(top_suggestion['recommended_charts'])} charts for best visualization")
        
        # Data quality recommendations
        quality = self._assess_data_quality(data_profile)
        if not quality['has_dates']:
            recommendations.append("Add date columns to enable trend analysis and time-based reporting")
        if not quality['has_numbers']:
            recommendations.append("Include numeric columns for quantitative analysis and KPI calculations")
        if not quality['suitable_for_comparisons']:
            recommendations.append("Add categorical columns for grouping and comparison analysis")
        
        # Specific report type recommendations
        if len(suggestions) > 1:
            recommendations.append(f"Also consider: {', '.join([s['name'] for s in suggestions[1:3]])}")
        
        return recommendations[:5]  # Limit to top 5 recommendations
