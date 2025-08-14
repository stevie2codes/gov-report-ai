#!/usr/bin/env python3
"""
Flask API server for the Gov-Report-AI application.
Provides the /api/plan-report endpoint for AI-powered report planning.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Try relative imports first, fall back to absolute for standalone testing
try:
    from .data_processor import DataProcessor, DataProfile
    from .ai_planner import AIReportPlanner, create_sample_ai_plan
except ImportError:
    from data_processor import DataProcessor, DataProfile
    from ai_planner import AIReportPlanner, create_sample_ai_plan

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Global instances
data_processor = DataProcessor()
ai_planner = None  # Will be initialized when API key is available


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'Gov-Report-AI API',
        'version': '1.0.0'
    })


@app.route('/api/plan-report', methods=['POST'])
def plan_report():
    """
    AI-powered report planning endpoint.
    
    Expected JSON payload:
    {
        "user_description": "Natural language description of desired report",
        "data": "CSV data as string or file path",
        "data_type": "csv or xlsx",
        "template_hint": "Optional template suggestion"
    }
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        user_description = data.get('user_description')
        csv_data = data.get('data')
        data_type = data.get('data_type', 'csv')
        template_hint = data.get('template_hint')
        
        # Validate required fields
        if not user_description:
            return jsonify({'error': 'user_description is required'}), 400
        if not csv_data:
            return jsonify({'error': 'data is required'}), 400
        
        # Initialize AI planner if not already done
        if ai_planner is None:
            try:
                ai_planner = AIReportPlanner()
                logger.info("AI planner initialized successfully")
            except ValueError as e:
                logger.warning(f"AI planner not available: {e}")
                return jsonify({
                    'error': 'AI planning not available - missing API key',
                    'fallback': 'Use /api/plan-report-fallback for template-based planning'
                }), 503
        
        # Process the data
        try:
            if data_type == 'csv':
                data_profile = data_processor.process_data_from_string(csv_data, 'csv')
            else:
                # For file paths, you'd handle file uploads here
                return jsonify({'error': 'File uploads not yet implemented'}), 501
        except Exception as e:
            logger.error(f"Data processing error: {e}")
            return jsonify({'error': f'Data processing failed: {str(e)}'}), 400
        
        # Generate AI plan
        try:
            report_spec = ai_planner.plan_report(
                user_description=user_description,
                data_profile=data_profile,
                template_hint=template_hint
            )
            
            # Convert to dictionary for JSON response
            response_data = {
                'success': True,
                'report_spec': report_spec.to_dict(),
                'data_profile': data_profile.to_dict(),
                'message': 'Report plan generated successfully'
            }
            
            return jsonify(response_data), 200
            
        except Exception as e:
            logger.error(f"AI planning error: {e}")
            return jsonify({
                'error': f'AI planning failed: {str(e)}',
                'fallback': 'Use /api/plan-report-fallback for template-based planning'
            }), 500
    
    except Exception as e:
        logger.error(f"Unexpected error in plan_report: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/plan-report-fallback', methods=['POST'])
def plan_report_fallback():
    """
    Fallback endpoint for template-based report planning when AI is not available.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        user_description = data.get('user_description', 'Government Report')
        csv_data = data.get('data')
        template_hint = data.get('template_hint')
        
        if not csv_data:
            return jsonify({'error': 'data is required'}), 400
        
        # Process the data
        try:
            data_profile = data_processor.process_data_from_string(csv_data, 'csv')
        except Exception as e:
            logger.error(f"Data processing error: {e}")
            return jsonify({'error': f'Data processing failed: {str(e)}'}), 400
        
        # Generate fallback plan
        try:
            # Use the fallback method from AI planner
            fallback_planner = AIReportPlanner.__new__(AIReportPlanner)
            report_spec = fallback_planner._generate_fallback_spec(
                user_description, data_profile, template_hint
            )
            
            response_data = {
                'success': True,
                'report_spec': report_spec.to_dict(),
                'data_profile': data_profile.to_dict(),
                'message': 'Fallback report plan generated (AI not available)',
                'fallback': True
            }
            
            return jsonify(response_data), 200
            
        except Exception as e:
            logger.error(f"Fallback planning error: {e}")
            return jsonify({'error': f'Fallback planning failed: {str(e)}'}), 500
    
    except Exception as e:
        logger.error(f"Unexpected error in plan_report_fallback: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/analyze-data', methods=['POST'])
def analyze_data():
    """
    Data analysis endpoint that returns data profile without AI planning.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        csv_data = data.get('data')
        data_type = data.get('data_type', 'csv')
        
        if not csv_data:
            return jsonify({'error': 'data is required'}), 400
        
        # Process the data
        try:
            if data_type == 'csv':
                data_profile = data_processor.process_data_from_string(csv_data, 'csv')
            else:
                return jsonify({'error': 'Only CSV data type supported currently'}), 400
        except Exception as e:
            logger.error(f"Data processing error: {e}")
            return jsonify({'error': f'Data processing failed: {str(e)}'}), 400
        
        response_data = {
            'success': True,
            'data_profile': data_profile.to_dict(),
            'message': 'Data analysis completed successfully'
        }
        
        return jsonify(response_data), 200
    
    except Exception as e:
        logger.error(f"Unexpected error in analyze_data: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Get available government report templates."""
    try:
        # Import here to avoid circular import issues
        try:
            from .report_spec import create_government_report_templates
        except ImportError:
            from report_spec import create_government_report_templates
        
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


@app.route('/api/sample-data', methods=['GET'])
def get_sample_data():
    """Get sample data for testing purposes."""
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
            'message': 'Sample data profile generated'
        }), 200
    
    except Exception as e:
        logger.error(f"Error generating sample data: {e}")
        return jsonify({'error': 'Failed to generate sample data'}), 500


def create_app():
    """Application factory for creating Flask app instances."""
    return app


if __name__ == '__main__':
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
    
    # Run the development server
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
