#!/usr/bin/env python3
"""
Web interface for the Gov-Report-AI application.
Provides a modern, responsive UI for file upload, AI planning, and report generation.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try relative imports first, fall back to absolute for standalone testing
try:
    from .data_processor import DataProcessor, create_sample_data_profile, DataProfile
    from .ai_planner import AIReportPlanner
    from .report_spec import create_government_report_templates
    from .report_renderer import ReportRenderer
    from .report_suggester import ReportTypeSuggester
except ImportError:
    from data_processor import DataProcessor, create_sample_data_profile, DataProfile
    from ai_planner import AIReportPlanner
    from report_spec import create_government_report_templates
    from report_renderer import ReportRenderer
    from report_suggester import ReportTypeSuggester


def create_app():
    """Application factory for creating Flask app instances."""
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Enable CORS
    CORS(app)
    
    # Global instances
    data_processor = DataProcessor()
    ai_planner = None  # Will be initialized when API key is available
    
    # Check if OpenAI API key is available
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        try:
            ai_planner = AIReportPlanner(api_key)
            logger.info("AI planner initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize AI planner: {e}")
    else:
        logger.warning("No OpenAI API key found. AI planning will not be available.")
    
    # Register routes
    register_routes(app, data_processor, ai_planner)
    
    return app


def register_routes(app, data_processor, ai_planner):
    """Register all routes with the Flask app."""
    
    @app.route('/')
    def index():
        """Main page with file upload and AI planning interface."""
        return render_template('index.html', ai_available=ai_planner is not None)
    
    @app.route('/upload', methods=['POST'])
    def upload_file():
        """Handle file upload and processing."""
        try:
            if 'file' not in request.files:
                flash('No file part', 'error')
                return redirect(url_for('index'))
            
            file = request.files['file']
            
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(url_for('index'))
            
            if file:
                # Read file content
                content = file.read().decode('utf-8')
                
                # Process the data
                try:
                    data_profile = data_processor.process_data_from_string(content, 'csv')
                    
                    # Store in Flask session (not URL parameters)
                    session['csv_content'] = content
                    session['data_profile'] = data_profile.to_dict()
                    
                    flash(f'File processed successfully! Found {data_profile.column_count} columns with {data_profile.row_count} rows.', 'success')
                    return redirect(url_for('plan_report'))
                    
                except Exception as e:
                    flash(f'Error processing file: {str(e)}', 'error')
                    return redirect(url_for('index'))
        
        except Exception as e:
            logger.error(f"Upload error: {e}")
            flash('An error occurred during file upload', 'error')
            return redirect(url_for('index'))
    
    @app.route('/plan-report')
    def plan_report():
        """Report planning interface."""
        # Check if data is in session
        if 'csv_content' not in session or 'data_profile' not in session:
            flash('No data found. Please upload a file first.', 'error')
            return redirect(url_for('index'))
        
        try:
            data_profile = session['data_profile']
            csv_content = session['csv_content']
            
            # Get available templates
            templates = create_government_report_templates()
            
            return render_template('plan_report.html', 
                                data_profile=data_profile,
                                csv_content=csv_content,
                                templates=templates,
                                ai_available=ai_planner is not None)
        
        except Exception as e:
            logger.error(f"Error in plan_report: {e}")
            flash('Error loading data for planning', 'error')
            return redirect(url_for('index'))
    
    @app.route('/api/plan-report', methods=['POST'])
    def api_plan_report():
        """API endpoint for AI report planning."""
        try:
            # Check if data is in session
            if 'csv_content' not in session or 'data_profile' not in session:
                return jsonify({'error': 'No data found in session. Please upload a file first.'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            user_description = data.get('user_description')
            template_hint = data.get('template_hint')
            
            if not user_description:
                return jsonify({'error': 'Missing user description'}), 400
            
            # Get data from session
            csv_content = session['csv_content']
            data_profile_dict = session['data_profile']
            
            # Convert back to DataProfile object
            data_profile = DataProfile.from_dict(data_profile_dict)
            
            # Generate AI plan
            if ai_planner:
                try:
                    report_spec = ai_planner.plan_report(
                        user_description=user_description,
                        data_profile=data_profile,
                        template_hint=template_hint
                    )
                    
                    response_data = {
                        'success': True,
                        'report_spec': report_spec.to_dict(),
                        'data_profile': data_profile_dict,
                        'message': 'Report plan generated successfully using AI',
                        'ai_generated': True
                    }
                    
                    # Store the report specification in session for preview
                    session['report_spec'] = report_spec.to_dict()
                    
                    return jsonify(response_data), 200
                    
                except Exception as e:
                    logger.error(f"AI planning error: {e}")
                    # Fall back to template-based planning
                    pass
            
            # Fallback to template-based planning
            try:
                fallback_planner = AIReportPlanner.__new__(AIReportPlanner)
                report_spec = fallback_planner._generate_fallback_report(
                    data_profile, user_description, template_hint
                )
                
                response_data = {
                    'success': True,
                    'report_spec': report_spec.to_dict(),
                    'data_profile': data_profile_dict,
                    'message': 'Report plan generated using template-based planning',
                    'ai_generated': False
                }
                
                # Store the report specification in session for preview
                session['report_spec'] = report_spec.to_dict()
                
                return jsonify(response_data), 200
                
            except Exception as e:
                logger.error(f"Fallback planning error: {e}")
                return jsonify({'error': f'Planning failed: {str(e)}'}), 500
        
        except Exception as e:
            logger.error(f"Unexpected error in api_plan_report: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/analyze-data', methods=['POST'])
    def api_analyze_data():
        """API endpoint for data analysis."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            csv_data = data.get('data')
            if not csv_data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Process the data
            try:
                data_profile = data_processor.process_data_from_string(csv_data, 'csv')
            except Exception as e:
                return jsonify({'error': f'Data processing failed: {str(e)}'}), 400
            
            response_data = {
                'success': True,
                'data_profile': data_profile.to_dict(),
                'message': 'Data analysis completed successfully'
            }
            
            return jsonify(response_data), 200
        
        except Exception as e:
            logger.error(f"Unexpected error in api_analyze_data: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/templates')
    def api_templates():
        """API endpoint for getting available templates."""
        try:
            templates = create_government_report_templates()
            template_list = []
            
            for template_name, template in templates.items():
                template_list.append({
                    'name': template_name,
                    'title': template.title,
                    'description': template.description,
                    'kpi_count': len(template.kpis),
                    'chart_count': len(template.charts),
                    'table_count': len(template.tables)
                })
            
            return jsonify({
                'success': True,
                'templates': template_list
            }), 200
            
        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return jsonify({'error': f'Failed to get templates: {str(e)}'}), 500
    
    @app.route('/preview-report')
    def preview_report():
        """Preview the generated report."""
        # Check if data is in session
        if 'csv_content' not in session or 'data_profile' not in session:
            flash('No data found. Please upload a file and generate a report plan first.', 'error')
            return redirect(url_for('index'))
        
        # Check if we have a report specification
        report_spec = session.get('report_spec')
        if not report_spec:
            flash('No report specification found. Please generate a report plan first.', 'error')
            return redirect(url_for('plan_report'))
        
        try:
            data_profile = session['data_profile']
            
            # Initialize the report renderer
            renderer = ReportRenderer()
            
            # Render the report
            rendered_report = renderer.render_report(report_spec, data_profile)
            
            # Generate HTML preview
            html_preview = renderer.generate_html_preview(rendered_report)
            
            return html_preview
            
        except Exception as e:
            logger.error(f"Error in preview_report: {e}")
            flash('Error generating report preview', 'error')
            return redirect(url_for('plan_report'))
    
    @app.route('/api/preview-report', methods=['POST'])
    def api_preview_report():
        """API endpoint for generating report preview."""
        try:
            # Check if data is in session
            if 'csv_content' not in session or 'data_profile' not in session:
                return jsonify({'error': 'No data found in session. Please upload a file first.'}), 400
            
            # Check if we have a report specification
            report_spec = session.get('report_spec')
            if not report_spec:
                return jsonify({'error': 'No report specification found. Please generate a report plan first.'}), 400
            
            data_profile = session['data_profile']
            
            # Initialize the report renderer
            renderer = ReportRenderer()
            
            # Render the report
            rendered_report = renderer.render_report(report_spec, data_profile)
            
            return jsonify({
                'success': True,
                'rendered_report': rendered_report,
                'message': 'Report preview generated successfully'
            }), 200
            
        except Exception as e:
            logger.error(f"Error in api_preview_report: {e}")
            return jsonify({'error': f'Failed to generate preview: {str(e)}'}), 500
    
    @app.route('/api/sample-data')
    def api_sample_data():
        """API endpoint for getting sample data."""
        try:
            # Import here to avoid circular import issues
            try:
                from .data_processor import create_sample_data_profile
            except ImportError:
                from data_processor import create_sample_data_profile
            
            sample_profile = create_sample_data_profile()
            
            return jsonify({
                'success': True,
                'data_profile': sample_profile.to_dict(),
                'message': 'Sample data profile generated successfully'
            }), 200
            
        except Exception as e:
            logger.error(f"Error generating sample data: {e}")
            return jsonify({'error': f'Failed to generate sample data: {str(e)}'}), 500
    
    @app.route('/api/suggest-reports')
    def api_suggest_reports():
        """API endpoint for getting report type suggestions based on uploaded data."""
        try:
            # Check if data is in session
            if 'data_profile' not in session:
                return jsonify({'error': 'No data found in session. Please upload a file first.'}), 400
            
            data_profile = session['data_profile']
            
            # Initialize the report suggester
            suggester = ReportTypeSuggester()
            
            # Get report suggestions
            suggestions = suggester.get_report_template_suggestions(data_profile)
            
            return jsonify({
                'success': True,
                'suggestions': suggestions,
                'message': 'Report suggestions generated successfully'
            }), 200
            
        except Exception as e:
            logger.error(f"Error in api_suggest_reports: {e}")
            return jsonify({'error': f'Failed to generate suggestions: {str(e)}'}), 500
    
    @app.route('/preview/<template_name>')
    def preview_template(template_name):
        """Preview a specific report template."""
        try:
            templates = create_government_report_templates()
            if template_name not in templates:
                flash('Template not found', 'error')
                return redirect(url_for('index'))
            
            template = templates[template_name]
            return render_template('preview_template.html', 
                                template=template,
                                template_name=template_name)
        
        except Exception as e:
            logger.error(f"Error previewing template: {e}")
            flash('Error loading template preview', 'error')
            return redirect(url_for('index'))
    
    @app.route('/about')
    def about():
        """About page with project information."""
        return render_template('about.html')


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '127.0.0.1')
    
    # Create and run the app
    app = create_app()
    
    # Production settings for Render
    app.run(
        host=host,
        port=port,
        debug=False,  # Always False in production
        threaded=True
    )
