from flask import Blueprint, render_template

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
def index():
    # Cole o link do Power BI aqui ou pegue do .env
    powerbi_url = "https://app.powerbi.com/view?r=eyJrIjoiODIwOWIwNWMtYmQ3ZC00NGYxLTk5OWQtMzQ4MzEwNzMyYmUzIiwidCI6IjVmYWMzYWEzLWFhOTMtNGMxMS1iNDQ5LThjY2VhZjZjNjAzMiJ9" 
    
    return render_template('dashboard.html', powerbi_url=powerbi_url)