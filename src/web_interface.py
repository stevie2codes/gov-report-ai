#!/usr/bin/env python3
"""
Web interface for the Gov-Report-AI application.
Provides a modern, responsive UI for file upload, AI planning, and report generation.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
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
    from .data_processor import DataProcessor, create_sample_data_profile
    from .ai_planner import AIReportPlanner
    from .report_spec import create_government_report_templates
except ImportError:
    from data_processor import DataProcessor, create_sample_data_profile
    from ai_planner import AIReportPlanner
    from report_spec import create_government_report_templates


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
        """Handle file upload and data processing."""
        try:
            if 'file' not in request.files:
                flash('No file selected', 'error')
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
                    
                    # Store in session for next step
                    session_data = {
                        'csv_content': content,
                        'data_profile': data_profile.to_dict()
                    }
                    
                    # Encode for session storage
                    session_data_encoded = base64.b64encode(json.dumps(session_data).encode()).decode()
                    
                    flash(f'File processed successfully! Found {data_profile.column_count} columns with {data_profile.row_count} rows.', 'success')
                    return redirect(url_for('plan_report', data=session_data_encoded))
                    
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
        data_param = request.args.get('data')
        if not data_param:
            flash('No data provided. Please upload a file first.', 'error')
            return redirect(url_for('index'))
        
        try:
            # Decode session data
            session_data = json.loads(base64.b64decode(data_param.encode()).decode())
            data_profile = session_data['data_profile']
            csv_content = session_data['csv_content']
            
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
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            user_description = data.get('user_description')
            csv_data = data.get('data')
            template_hint = data.get('template_hint')
            
            if not user_description or not csv_data:
                return jsonify({'error': 'Missing required fields'}), 400
            
            # Process the data
            try:
                data_profile = data_processor.process_data_from_string(csv_data, 'csv')
            except Exception as e:
                return jsonify({'error': f'Data processing failed: {str(e)}'}), 400
            
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
                        'data_profile': data_profile.to_dict(),
                        'message': 'Report plan generated successfully using AI',
                        'ai_generated': True
                    }
                    
                    return jsonify(response_data), 200
                    
                except Exception as e:
                    logger.error(f"AI planning error: {e}")
                    # Fall back to template-based planning
                    pass
            
            # Fallback to template-based planning
            try:
                fallback_planner = AIReportPlanner.__new__(AIReportPlanner)
                report_spec = fallback_planner._generate_fallback_spec(
                    user_description, data_profile, template_hint
                )
                
                response_data = {
                    'success': True,
                    'report_spec': report_spec.to_dict(),
                    'data_profile': data_profile.to_dict(),
                    'message': 'Report plan generated using template-based planning',
                    'ai_generated': False
                }
                
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
                'templates': template_list,
                'count': len(template_list)
            }), 200
        
        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return jsonify({'error': 'Failed to retrieve templates'}), 500
    
    @app.route('/api/sample-data')
    def api_sample_data():
        """API endpoint for getting sample data."""
        try:
            sample_profile = create_sample_data_profile()
            
            return jsonify({
                'success': True,
                'data_profile': sample_profile.to_dict(),
                'message': 'Sample data profile generated'
            }), 200
        
        except Exception as e:
            logger.error(f"Error generating sample data: {e}")
            return jsonify({'error': 'Failed to generate sample data'}), 500
    
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
    # Create and run the app
    app = create_app()
    
    # Run the development server
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
