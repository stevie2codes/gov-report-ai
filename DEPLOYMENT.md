# 🚀 Deployment Guide

This guide covers deploying GovReport AI to various platforms, including GitHub Pages for the frontend and cloud services for the backend.

## 📋 Table of Contents

1. [GitHub Pages Deployment](#github-pages-deployment)
2. [Backend Deployment Options](#backend-deployment-options)
3. [Full Stack Deployment](#full-stack-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Custom Domain Setup](#custom-domain-setup)
6. [Monitoring & Maintenance](#monitoring--maintenance)

## 🌐 GitHub Pages Deployment

### Quick Start (Frontend Only)

1. **Enable GitHub Pages**
   - Go to your repository settings
   - Navigate to "Pages" section
   - Select "Deploy from a branch"
   - Choose `main` branch and `/docs` folder
   - Click "Save"

2. **Automatic Deployment**
   - The GitHub Actions workflow will automatically deploy on every push to main
   - Your site will be available at: `https://yourusername.github.io/Gov-report-ai/`

3. **Manual Deployment**
   ```bash
   # Push your changes
   git add .
   git commit -m "Update GitHub Pages site"
   git push origin main
   ```

### Customization

- **Update URLs**: Edit `docs/_config.yml` with your actual GitHub username
- **Branding**: Modify `docs/index.html` for your organization
- **Content**: Update the README and documentation in the `docs/` folder

## 🔧 Backend Deployment Options

### Option 1: Render (Recommended for Free Tier)

1. **Create Render Account**
   - Visit [render.com](https://render.com)
   - Sign up with GitHub

2. **Deploy Backend**
   ```bash
   # Create render.yaml in your repo
   services:
     - type: web
       name: govreport-ai-backend
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: python src/web_interface.py
       envVars:
         - key: OPENAI_API_KEY
           sync: false
         - key: PORT
           value: 8000
   ```

3. **Environment Variables**
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `PORT`: 8000 (Render will override this)

### Option 2: Railway

1. **Setup Railway**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli
   
   # Login and deploy
   railway login
   railway init
   railway up
   ```

2. **Environment Variables**
   - Set `OPENAI_API_KEY` in Railway dashboard
   - Railway automatically sets `PORT`

### Option 3: Heroku

1. **Create Heroku App**
   ```bash
   # Install Heroku CLI
   heroku create govreport-ai
   
   # Deploy
   git push heroku main
   ```

2. **Environment Variables**
   ```bash
   heroku config:set OPENAI_API_KEY=your_key_here
   ```

### Option 4: DigitalOcean App Platform

1. **Create App**
   - Visit [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
   - Connect your GitHub repository
   - Select Python environment

2. **Configuration**
   - Build command: `pip install -r requirements.txt`
   - Run command: `python src/web_interface.py`
   - Set environment variables in dashboard

## 🌍 Full Stack Deployment

### Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub Pages  │    │  Cloud Backend  │    │   OpenAI API    │
│   (Frontend)    │◄──►│   (Flask App)   │◄──►│   (GPT-4o)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Frontend-Backend Integration

1. **Update Frontend URLs**
   ```javascript
   // In docs/index.html, update API endpoints
   const API_BASE_URL = 'https://your-backend-url.com';
   
   // Example API call
   fetch(`${API_BASE_URL}/api/plan-report`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify(data)
   });
   ```

2. **CORS Configuration**
   ```python
   # In src/web_interface.py
   from flask_cors import CORS
   
   app = Flask(__name__)
   CORS(app, origins=['https://yourusername.github.io'])
   ```

3. **Environment Variables**
   ```bash
   # Backend environment
   ALLOWED_ORIGINS=https://yourusername.github.io,http://localhost:3000
   ```

## ⚙️ Environment Configuration

### Required Variables

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-your-key-here

# Server Configuration
PORT=8000
HOST=0.0.0.0

# Security
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=https://yourdomain.com

# Optional: Database (if adding persistence)
DATABASE_URL=postgresql://user:pass@host:port/db
```

### Production Settings

```python
# In src/web_interface.py
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Production settings
    app.run(
        host=host,
        port=port,
        debug=False,  # Always False in production
        threaded=True
    )
```

## 🌐 Custom Domain Setup

### GitHub Pages Custom Domain

1. **Add Custom Domain**
   - Go to repository settings → Pages
   - Enter your custom domain (e.g., `govreport.ai`)
   - Click "Save"

2. **DNS Configuration**
   ```
   # Add these DNS records
   CNAME: govreport.ai → yourusername.github.io
   A: @ → 185.199.108.153
   A: @ → 185.199.109.153
   A: @ → 185.199.110.153
   A: @ → 185.199.111.153
   ```

3. **SSL Certificate**
   - GitHub automatically provides SSL
   - Wait 24-48 hours for propagation

### Backend Custom Domain

1. **Domain Provider**
   - Point your subdomain (e.g., `api.govreport.ai`) to your backend
   - Use CNAME for cloud services, A records for VPS

2. **SSL Certificate**
   - Use Let's Encrypt for free SSL
   - Cloud providers usually handle this automatically

## 📊 Monitoring & Maintenance

### Health Checks

1. **Add Health Endpoint**
   ```python
   @app.route('/health')
   def health_check():
       return jsonify({
           'status': 'healthy',
           'timestamp': datetime.utcnow().isoformat(),
           'version': '1.0.0'
       })
   ```

2. **Monitoring Services**
   - **UptimeRobot**: Free uptime monitoring
   - **StatusCake**: Advanced monitoring
   - **Pingdom**: Professional monitoring

### Logging

```python
import logging
from logging.handlers import RotatingFileHandler

# Production logging
if not app.debug:
    file_handler = RotatingFileHandler('govreport.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('GovReport AI startup')
```

### Backup Strategy

1. **Code Backup**
   - GitHub provides automatic backup
   - Consider mirroring to GitLab or Bitbucket

2. **Data Backup**
   - If adding database: automated daily backups
   - Environment variables: store securely (1Password, LastPass)

3. **Configuration Backup**
   - Version control all configuration files
   - Document deployment procedures

## 🚨 Troubleshooting

### Common Issues

1. **CORS Errors**
   ```bash
   # Check browser console for CORS errors
   # Ensure ALLOWED_ORIGINS includes your frontend domain
   ```

2. **API Key Issues**
   ```bash
   # Verify OpenAI API key is valid
   # Check API usage and billing
   # Ensure model access (GPT-4o)
   ```

3. **Port Conflicts**
   ```bash
   # Check if port is already in use
   lsof -i :8000
   # Use different port if needed
   ```

4. **Memory Issues**
   ```bash
   # Monitor memory usage
   # Consider upgrading instance size
   # Optimize data processing for large files
   ```

### Performance Optimization

1. **File Upload Limits**
   ```python
   # Increase file size limits
   app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
   ```

2. **Caching**
   ```python
   # Add Redis caching for repeated requests
   # Cache AI responses for similar queries
   ```

3. **Async Processing**
   ```python
   # Use Celery for background tasks
   # Process large files asynchronously
   ```

## 📚 Additional Resources

- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Render Documentation](https://render.com/docs)
- [Railway Documentation](https://docs.railway.app/)

## 🆘 Support

If you encounter issues:

1. **Check the logs** in your deployment platform
2. **Verify environment variables** are set correctly
3. **Test locally** before deploying
4. **Check GitHub Issues** for known problems
5. **Contact support** at contact@govreport.ai

---

**Happy Deploying! 🚀**

*Your government AI reporting platform is just a few clicks away from going live.*
