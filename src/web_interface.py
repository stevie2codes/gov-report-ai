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
from flask_session import Session
from dotenv import load_dotenv
import base64
import numpy as np
from datetime import timedelta

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_json_serializable(obj):
    """Convert numpy types and other non-JSON-serializable objects to standard Python types."""
    try:
        if isinstance(obj, dict):
            return {key: ensure_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [ensure_json_serializable(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif hasattr(obj, 'dtype'):  # Catch any other numpy-like objects
            logger.warning(f"Found numpy-like object with dtype: {obj.dtype}, converting to Python type")
            return obj.item() if hasattr(obj, 'item') else str(obj)
        else:
            return obj
    except Exception as e:
        logger.error(f"Error in ensure_json_serializable for {type(obj)}: {e}")
        return str(obj)  # Fallback to string representation

# Test the serialization function
def test_serialization():
    """Test the ensure_json_serializable function."""
    try:
        test_data = {
            'int64': np.int64(42),
            'float64': np.float64(3.14),
            'array': np.array([1, 2, 3]),
            'normal': 'string',
            'number': 123
        }
        result = ensure_json_serializable(test_data)
        logger.info("Serialization test passed")
        return True
    except Exception as e:
        logger.error(f"Serialization test failed: {e}")
        return False

# Run the test
test_serialization()

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
    
    # Configure session settings to handle larger data
    app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem instead of cookies for large data
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    
    # Enable CORS
    CORS(app)
    
    # Initialize Flask-Session
    Session(app)
    
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
        """Handle file upload and redirect to planning page."""
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
                file_content = file.read().decode('utf-8')
                
                # Determine file type
                file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'csv'
                
                # Process the data with smart handling
                try:
                    logger.info(f"Starting data processing for file: {file.filename}")
                    
                    local_processor = DataProcessor(max_sample_rows=1000, max_ai_tokens=15000)
                    logger.info("DataProcessor initialized successfully")
                    
                    full_profile = local_processor.process_data_from_string(file_content, file_extension)
                    logger.info(f"Full profile created: {full_profile.total_rows} rows, {len(full_profile.columns)} columns")
                    
                    # Get AI-optimized profile and recommendations
                    ai_profile, recommendations = local_processor.get_ai_planning_profile(full_profile)
                    logger.info(f"AI profile created: {ai_profile.total_rows} rows, strategy: {recommendations.get('processing_strategy', 'unknown')}")
                    
                    # Store both profiles in session
                    session['csv_content'] = file_content
                    
                    # Debug: Log the types before serialization
                    full_profile_dict = full_profile.to_dict()
                    ai_profile_dict = ai_profile.to_dict()
                    
                    logger.info(f"Full profile dict types: {type(full_profile_dict)}")
                    logger.info(f"AI profile dict types: {type(ai_profile_dict)}")
                    logger.info(f"Recommendations types: {type(recommendations)}")
                    
                    # Store only essential data in session to avoid cookie size limits
                    # Store minimal AI profile for planning
                    session['ai_data_profile'] = ensure_json_serializable(ai_profile_dict)
                    session['data_profile'] = ensure_json_serializable(ai_profile_dict)  # Keep for backward compatibility
                    session['processing_recommendations'] = ensure_json_serializable(recommendations)
                    
                    # Store full profile separately (not in session) - will be processed on-demand
                    # This prevents the 4KB cookie limit issue
                    session['has_full_data'] = True
                    session['file_metadata'] = {
                        'filename': file.filename,
                        'total_rows': full_profile.total_rows,
                        'file_size_mb': full_profile.file_size_mb,
                        'columns_count': len(full_profile.columns)
                    }
                    
                    # Debug: Log the types after serialization
                    logger.info(f"Session data types after serialization:")
                    for key, value in session.items():
                        if key != 'csv_content':  # Skip the large CSV content
                            logger.info(f"  {key}: {type(value)}")
                    
                    logger.info("All data stored in session successfully")
                    
                    # Log processing info
                    logger.info(f"File uploaded: {file.filename}, "
                               f"Size: {full_profile.file_size_mb:.2f}MB, "
                               f"Rows: {full_profile.total_rows}, "
                               f"AI sample: {ai_profile.total_rows}, "
                               f"Estimated tokens: {recommendations['estimated_ai_tokens']}")
                    
                    # Show appropriate message based on data size
                    if full_profile.total_rows > 10000:
                        flash(f'Large dataset detected ({full_profile.total_rows:,} rows). '
                              f'Using AI-optimized sample for planning. Full data available for processing.', 'info')
                    elif full_profile.total_rows > 5000:
                        flash(f'Medium dataset detected ({full_profile.total_rows:,} rows). '
                              f'AI planning optimized for efficiency.', 'info')
                    else:
                        flash(f'Dataset processed successfully ({full_profile.total_rows:,} rows).', 'success')
                    
                    logger.info("Redirecting to plan_report page")
                    return redirect(url_for('plan_report'))
                    
                except Exception as e:
                    logger.error(f"Error processing file: {e}", exc_info=True)
                    flash(f'Error processing file: {str(e)}', 'error')
                    return redirect(url_for('index'))
            
        except Exception as e:
            logger.error(f"Unexpected error in upload: {e}")
            flash('An unexpected error occurred during upload', 'error')
            return redirect(url_for('index'))
    
    @app.route('/plan-report')
    def plan_report():
        """Report planning interface."""
        try:
            logger.info("Plan report route accessed")
            
            # Check if data is in session
            if 'csv_content' not in session or ('data_profile' not in session and 'ai_data_profile' not in session):
                logger.warning("No data found in session for plan_report")
                flash('No data found. Please upload a file first.', 'error')
                return redirect(url_for('index'))
            
            # Use ai_data_profile if available, otherwise fall back to data_profile
            data_profile = session.get('ai_data_profile') or session.get('data_profile')
            csv_content = session['csv_content']
            
            # Get file metadata for display
            file_metadata = session.get('file_metadata', {})
            
            logger.info(f"Data profile loaded: {data_profile.get('total_rows', 'unknown')} rows, {len(data_profile.get('columns', []))} columns")
            logger.info(f"File metadata: {file_metadata}")
            
            # Get available templates
            templates = create_government_report_templates()
            logger.info(f"Templates loaded: {len(templates)} available")
            
            return render_template('plan_report.html', 
                                data_profile=data_profile,
                                csv_content=csv_content,
                                templates=templates,
                                file_metadata=file_metadata,
                                ai_available=ai_planner is not None)
        
        except Exception as e:
            logger.error(f"Error in plan_report: {e}", exc_info=True)
            flash('Error loading data for planning', 'error')
            return redirect(url_for('index'))
    
    @app.route('/api/plan-report', methods=['POST'])
    def api_plan_report():
        """API endpoint for AI report planning."""
        try:
            # Check if data is in session
            if 'csv_content' not in session or 'ai_data_profile' not in session:
                return jsonify({'error': 'No data found in session. Please upload a file first.'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            user_description = data.get('description', '')
            template_hint = data.get('template', '')
            
            if not user_description:
                return jsonify({'error': 'No description provided'}), 400
            
            try:
                # Use AI-optimized profile for planning (reduces token usage)
                ai_data_profile = DataProfile.from_dict(session['ai_data_profile'])
                full_data_profile = DataProfile.from_dict(session['full_data_profile'])
                recommendations = session.get('processing_recommendations', {})
                
                # Log planning attempt with token estimates
                logger.info(f"AI planning requested for {full_data_profile.total_rows} rows, "
                           f"using {ai_data_profile.total_rows} row sample, "
                           f"estimated tokens: {recommendations.get('estimated_ai_tokens', 0)}")
                
                # Initialize AI planner
                planner = AIReportPlanner()
                
                # Plan the report using AI-optimized profile
                report_spec = planner.plan_report(user_description, ai_data_profile, template_hint)
                
                # Store the report specification in session for preview
                session['report_spec'] = ensure_json_serializable(report_spec.to_dict())
                
                response_data = {
                    'success': True,
                    'report_spec': ensure_json_serializable(report_spec.to_dict()),
                    'data_profile': ensure_json_serializable(ai_data_profile.to_dict()),
                    'full_data_info': {
                        'total_rows': full_data_profile.total_rows,
                        'file_size_mb': full_data_profile.file_size_mb,
                        'ai_sample_rows': ai_data_profile.total_rows,
                        'estimated_tokens': recommendations.get('estimated_ai_tokens', 0),
                        'processing_strategy': recommendations.get('processing_strategy', 'standard')
                    },
                    'message': 'Report plan generated successfully using AI',
                    'ai_generated': True
                }
                
                return jsonify(response_data), 200
                
            except Exception as e:
                logger.error(f"Error in AI planning: {e}")
                
                # Try fallback planning
                try:
                    logger.info("Generating fallback report specification...")
                    
                    # Use the AI-optimized profile for fallback as well
                    ai_data_profile = DataProfile.from_dict(session['ai_data_profile'])
                    
                    # Generate fallback report
                    fallback_planner = AIReportPlanner.__new__(AIReportPlanner)
                    report_spec = fallback_planner._generate_fallback_report(
                        ai_data_profile, user_description, template_hint
                    )
                    
                    # Store the report specification in session for preview
                    session['report_spec'] = ensure_json_serializable(report_spec.to_dict())
                    
                    response_data = {
                        'success': True,
                        'report_spec': ensure_json_serializable(report_spec.to_dict()),
                        'data_profile': ensure_json_serializable(ai_data_profile.to_dict()),
                        'full_data_info': {
                            'total_rows': DataProfile.from_dict(session['full_data_profile']).total_rows,
                            'file_size_mb': DataProfile.from_dict(session['full_data_profile']).file_size_mb,
                            'ai_sample_rows': ai_data_profile.total_rows,
                            'estimated_tokens': session.get('processing_recommendations', {}).get('estimated_ai_tokens', 0),
                            'processing_strategy': session.get('processing_recommendations', {}).get('processing_strategy', 'standard')
                        },
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
    host = os.environ.get('HOST', '0.0.0.0')  # Default to 0.0.0.0 for production
    
    # Create and run the app
    app = create_app()
    
    # Production settings for Render
    app.run(
        host=host,
        port=port,
        debug=False,  # Always False in production
        threaded=True
    )
