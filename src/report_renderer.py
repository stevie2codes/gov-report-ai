#!/usr/bin/env python3
"""
Report rendering module for generating visual reports from ReportSpec objects.
Handles charts, tables, and formatted content generation.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReportRenderer:
    """Renders ReportSpec objects into visual reports."""
    
    def __init__(self):
        self.chart_colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]
    
    def render_report(self, report_spec: Dict[str, Any], data_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Render a complete report from specification and data profile."""
        try:
            rendered_report = {
                'title': report_spec.get('title', 'Generated Report'),
                'description': report_spec.get('description', ''),
                'generated_at': datetime.now().isoformat(),
                'sections': []
            }
            
            # Render KPIs section
            if report_spec.get('kpis'):
                rendered_report['sections'].append(
                    self._render_kpis_section(report_spec['kpis'], data_profile)
                )
            
            # Render charts section
            if report_spec.get('charts'):
                rendered_report['sections'].append(
                    self._render_charts_section(report_spec['charts'], data_profile)
                )
            
            # Render tables section
            if report_spec.get('tables'):
                rendered_report['sections'].append(
                    self._render_tables_section(report_spec['tables'], data_profile)
                )
            
            # Render narrative section
            if report_spec.get('narrativeGoals'):
                rendered_report['sections'].append(
                    self._render_narrative_section(report_spec['narrativeGoals'])
                )
            
            return rendered_report
            
        except Exception as e:
            logger.error(f"Error rendering report: {e}")
            return {
                'error': f'Failed to render report: {str(e)}',
                'title': 'Report Generation Failed'
            }
    
    def _render_kpis_section(self, kpis: List[Dict[str, Any]], data_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Render the KPIs section with calculated metrics."""
        section = {
            'type': 'kpis',
            'title': 'Key Performance Indicators',
            'description': 'Summary metrics and key insights',
            'content': []
        }
        
        for i, kpi in enumerate(kpis):
            try:
                # Calculate the actual metric value based on data profile
                calculated_value = self._calculate_kpi_value(kpi, data_profile)
                
                kpi_content = {
                    'label': kpi.get('label', f'KPI {i+1}'),
                    'value': calculated_value,
                    'metric_type': kpi.get('metric', 'unknown'),
                    'format': kpi.get('format', 'number'),
                    'column': kpi.get('column', ''),
                    'color': self.chart_colors[i % len(self.chart_colors)]
                }
                
                section['content'].append(kpi_content)
                
            except Exception as e:
                logger.warning(f"Error rendering KPI {i}: {e}")
                section['content'].append({
                    'label': kpi.get('label', f'KPI {i+1}'),
                    'value': 'Error calculating',
                    'error': str(e)
                })
        
        return section
    
    def _render_charts_section(self, charts: List[Dict[str, Any]], data_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Render the charts section with chart specifications."""
        section = {
            'type': 'charts',
            'title': 'Data Visualizations',
            'description': 'Charts and graphs for data analysis',
            'content': []
        }
        
        for i, chart in enumerate(charts):
            try:
                chart_content = {
                    'type': chart.get('type', 'bar'),
                    'title': chart.get('title', f'Chart {i+1}'),
                    'x_axis': chart.get('x', {}),
                    'series': chart.get('series', []),
                    'chart_data': self._generate_chart_data(chart, data_profile),
                    'color_scheme': self.chart_colors[:len(chart.get('series', []))],
                    'chart_options': self._get_chart_options(chart)
                }
                
                section['content'].append(chart_content)
                
            except Exception as e:
                logger.warning(f"Error rendering chart {i}: {e}")
                section['content'].append({
                    'title': chart.get('title', f'Chart {i+1}'),
                    'error': f'Failed to render chart: {str(e)}'
                })
        
        return section
    
    def _render_tables_section(self, tables: List[Dict[str, Any]], data_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Render the tables section with formatted data tables."""
        section = {
            'type': 'tables',
            'title': 'Data Tables',
            'description': 'Structured data presentation',
            'content': []
        }
        
        for i, table in enumerate(tables):
            try:
                table_content = {
                    'title': table.get('title', f'Table {i+1}'),
                    'columns': table.get('columns', []),
                    'data': self._generate_table_data(table, data_profile),
                    'sort_options': table.get('sort', {}),
                    'limit': table.get('limit', 10)
                }
                
                section['content'].append(table_content)
                
            except Exception as e:
                logger.warning(f"Error rendering table {i}: {e}")
                section['content'].append({
                    'title': table.get('title', f'Table {i+1}'),
                    'error': f'Failed to render table: {str(e)}'
                })
        
        return section
    
    def _render_narrative_section(self, narrative_goals: List[str]) -> Dict[str, Any]:
        """Render the narrative section with AI-generated insights."""
        section = {
            'type': 'narrative',
            'title': 'Report Insights',
            'description': 'Key findings and recommendations',
            'content': []
        }
        
        for goal in narrative_goals:
            section['content'].append({
                'insight': goal,
                'type': 'recommendation'
            })
        
        return section
    
    def _calculate_kpi_value(self, kpi: Dict[str, Any], data_profile: Dict[str, Any]) -> Any:
        """Calculate the actual value for a KPI based on the data profile."""
        metric_type = kpi.get('metric', 'count')
        column_name = kpi.get('column', '')
        
        if not column_name:
            return 'No column specified'
        
        # Find the column in the data profile
        column_data = None
        for col in data_profile.get('columns', []):
            if col.get('name') == column_name:
                column_data = col
                break
        
        if not column_data:
            return f'Column "{column_name}" not found'
        
        # Calculate based on metric type
        if metric_type == 'count':
            return column_data.get('stats', {}).get('total_count', 0)
        elif metric_type == 'sum':
            # For numeric columns, try to calculate sum
            if column_data.get('type') == 'number':
                sample_values = column_data.get('sampleValues', [])
                try:
                    numeric_values = [float(str(v).replace(',', '')) for v in sample_values if v]
                    return sum(numeric_values) if numeric_values else 0
                except:
                    return 'Cannot calculate sum'
            return 'Column is not numeric'
        elif metric_type == 'avg':
            if column_data.get('type') == 'number':
                stats = column_data.get('stats', {})
                return stats.get('mean', 0)
            return 'Column is not numeric'
        elif metric_type == 'min':
            if column_data.get('type') == 'number':
                stats = column_data.get('stats', {})
                return stats.get('min', 0)
            return 'Column is not numeric'
        elif metric_type == 'max':
            if column_data.get('type') == 'number':
                stats = column_data.get('stats', {})
                return stats.get('max', 0)
            return 'Column is not numeric'
        else:
            return f'Unknown metric type: {metric_type}'
    
    def _generate_chart_data(self, chart: Dict[str, Any], data_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate sample chart data based on chart specification and data profile."""
        chart_type = chart.get('type', 'bar')
        x_column = chart.get('x', {}).get('column', '')
        
        # Find the x-axis column
        x_column_data = None
        for col in data_profile.get('columns', []):
            if col.get('name') == x_column:
                x_column_data = col
                break
        
        if not x_column_data:
            return [{'error': f'X-axis column "{x_column}" not found'}]
        
        # Generate sample data points
        sample_values = x_column_data.get('sampleValues', [])
        chart_data = []
        
        for i, value in enumerate(sample_values[:5]):  # Limit to 5 data points for preview
            data_point = {'x': value}
            
            # Add series data
            for j, series in enumerate(chart.get('series', [])[:3]):  # Limit to 3 series
                series_column = series.get('column', '')
                if series_column:
                    # Find series column data
                    for col in data_profile.get('columns', []):
                        if col.get('name') == series_column:
                            series_values = col.get('sampleValues', [])
                            if i < len(series_values):
                                data_point[f'y{j+1}'] = series_values[i]
                            else:
                                data_point[f'y{j+1}'] = 0
                            break
                    else:
                        data_point[f'y{j+1}'] = 0
                else:
                    data_point[f'y{j+1}'] = i * 10  # Fallback value
            
            chart_data.append(data_point)
        
        return chart_data
    
    def _generate_table_data(self, table: Dict[str, Any], data_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate sample table data based on table specification and data profile."""
        columns = table.get('columns', [])
        limit = table.get('limit', 10)
        
        # Find the columns in the data profile
        column_data = {}
        for col_name in columns:
            for col in data_profile.get('columns', []):
                if col.get('name') == col_name:
                    column_data[col_name] = col
                    break
        
        # Generate sample rows
        table_data = []
        max_rows = min(limit, 5)  # Limit preview to 5 rows
        
        for i in range(max_rows):
            row = {}
            for col_name in columns:
                if col_name in column_data:
                    col = column_data[col_name]
                    sample_values = col.get('sampleValues', [])
                    if i < len(sample_values):
                        row[col_name] = sample_values[i]
                    else:
                        row[col_name] = f'Sample {i+1}'
                else:
                    row[col_name] = f'Column {col_name} not found'
            
            table_data.append(row)
        
        return table_data
    
    def _get_chart_options(self, chart: Dict[str, Any]) -> Dict[str, Any]:
        """Get chart-specific rendering options."""
        chart_type = chart.get('type', 'bar')
        
        if chart_type == 'bar':
            return {
                'orientation': 'vertical',
                'show_grid': True,
                'show_labels': True
            }
        elif chart_type == 'line':
            return {
                'show_points': True,
                'show_grid': True,
                'smooth': False
            }
        elif chart_type == 'pie':
            return {
                'show_percentages': True,
                'show_labels': True,
                'donut': False
            }
        else:
            return {}
    
    def generate_html_preview(self, rendered_report: Dict[str, Any]) -> str:
        """Generate an HTML preview of the rendered report."""
        try:
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{rendered_report.get('title', 'Report Preview')}</title>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <style>
                    body {{ font-family: 'Times New Roman', serif; margin: 40px; background: #f9f9f9; }}
                    .report-container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .report-header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }}
                    .report-title {{ font-size: 28px; font-weight: bold; color: #333; margin-bottom: 10px; }}
                    .report-meta {{ color: #666; font-size: 14px; }}
                    .section {{ margin-bottom: 40px; }}
                    .section-title {{ font-size: 20px; font-weight: bold; color: #333; border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 20px; }}
                    .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }}
                    .kpi-card {{ background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; text-align: center; }}
                    .kpi-value {{ font-size: 24px; font-weight: bold; color: #007bff; margin-bottom: 5px; }}
                    .kpi-label {{ color: #666; font-size: 14px; }}
                    .chart-container {{ margin: 20px 0; height: 400px; }}
                    .table-container {{ overflow-x: auto; margin: 20px 0; }}
                    table {{ width: 100%; border-collapse: collapse; }}
                    th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                    th {{ background-color: #f8f9fa; font-weight: bold; }}
                    .narrative-item {{ background: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 10px 0; }}
                    .error {{ color: #dc3545; background: #f8d7da; padding: 10px; border-radius: 4px; }}
                </style>
            </head>
            <body>
                <div class="report-container">
                    <div class="report-header">
                        <div class="report-title">{rendered_report.get('title', 'Generated Report')}</div>
                        <div class="report-meta">Generated on {rendered_report.get('generated_at', 'Unknown date')}</div>
                        {f'<div class="report-meta">{rendered_report.get("description", "")}</div>' if rendered_report.get('description') else ''}
                    </div>
            """
            
            # Render each section
            for section in rendered_report.get('sections', []):
                html += self._render_section_html(section)
            
            html += """
                </div>
            </body>
            </html>
            """
            
            return html
            
        except Exception as e:
            logger.error(f"Error generating HTML preview: {e}")
            return f"<html><body><h1>Error generating preview</h1><p>{str(e)}</p></body></html>"
    
    def _render_section_html(self, section: Dict[str, Any]) -> str:
        """Render a single section as HTML."""
        section_type = section.get('type', 'unknown')
        title = section.get('title', 'Section')
        content = section.get('content', [])
        
        html = f'<div class="section"><div class="section-title">{title}</div>'
        
        if section_type == 'kpis':
            html += '<div class="kpi-grid">'
            for kpi in content:
                if 'error' in kpi:
                    html += f'<div class="kpi-card error">{kpi["error"]}</div>'
                else:
                    html += f'''
                    <div class="kpi-card">
                        <div class="kpi-value">{kpi.get("value", "N/A")}</div>
                        <div class="kpi-label">{kpi.get("label", "Unknown")}</div>
                    </div>
                    '''
            html += '</div>'
            
        elif section_type == 'charts':
            for i, chart in enumerate(content):
                if 'error' in chart:
                    html += f'<div class="error">{chart["error"]}</div>'
                else:
                    html += f'''
                    <div class="chart-container">
                        <h3>{chart.get("title", "Chart")}</h3>
                        <canvas id="chart{i}"></canvas>
                    </div>
                    <script>
                        const ctx{i} = document.getElementById('chart{i}').getContext('2d');
                        new Chart(ctx{i}, {{
                            type: '{chart.get("type", "bar")}',
                            data: {{
                                labels: {json.dumps([d.get("x", "") for d in chart.get("chart_data", [])])},
                                datasets: {json.dumps(self._generate_chart_datasets(chart))}
                            }},
                            options: {{
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {{
                                    title: {{
                                        display: true,
                                        text: '{chart.get("title", "Chart")}'
                                    }}
                                }}
                            }}
                        }});
                    </script>
                    '''
                    
        elif section_type == 'tables':
            for table in content:
                if 'error' in table:
                    html += f'<div class="error">{table["error"]}</div>'
                else:
                    html += f'''
                    <div class="table-container">
                        <h3>{table.get("title", "Table")}</h3>
                        <table>
                            <thead>
                                <tr>
                                    {''.join([f'<th>{col}</th>' for col in table.get("columns", [])])}
                                </tr>
                            </thead>
                            <tbody>
                                {self._generate_table_rows_html(table)}
                            </tbody>
                        </table>
                    </div>
                    '''
                    
        elif section_type == 'narrative':
            for item in content:
                html += f'''
                <div class="narrative-item">
                    <strong>Insight:</strong> {item.get("insight", "No insight provided")}
                </div>
                '''
        
        html += '</div>'
        return html
    
    def _generate_chart_datasets(self, chart: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate Chart.js datasets from chart data."""
        datasets = []
        chart_data = chart.get('chart_data', [])
        
        # Count how many y-series we have
        y_keys = [k for k in chart_data[0].keys() if k.startswith('y')] if chart_data else []
        
        for i, y_key in enumerate(y_keys):
            dataset = {
                'label': f'Series {i+1}',
                'data': [row.get(y_key, 0) for row in chart_data],
                'backgroundColor': chart.get('color_scheme', self.chart_colors)[i % len(self.chart_colors)],
                'borderColor': chart.get('color_scheme', self.chart_colors)[i % len(self.chart_colors)],
                'borderWidth': 1
            }
            
            if chart.get('type') == 'line':
                dataset['fill'] = False
                dataset['tension'] = 0.1
            elif chart.get('type') == 'pie':
                dataset['backgroundColor'] = chart.get('color_scheme', self.chart_colors)
            
            datasets.append(dataset)
        
        return datasets
    
    def _generate_table_rows_html(self, table: Dict[str, Any]) -> str:
        """Generate HTML for table rows."""
        rows_html = ""
        columns = table.get("columns", [])
        data = table.get("data", [])
        
        for row in data:
            row_html = "<tr>"
            for col in columns:
                cell_value = row.get(col, '')
                row_html += f"<td>{cell_value}</td>"
            row_html += "</tr>"
            rows_html += row_html
        
        return rows_html
