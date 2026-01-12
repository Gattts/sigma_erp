from flask import Flask, render_template
from routes.financeiro import financeiro_bp
from routes.calculadora import calculadora_bp
from routes.compras import compras_bp
from routes.produtos import produtos_bp 
from routes.dashboard import dashboard_bp 

app = Flask(__name__)
app.secret_key = "sigma_secret_key_2025"

# Registra as rotas (Blueprints)
app.register_blueprint(financeiro_bp)
app.register_blueprint(calculadora_bp)
app.register_blueprint(compras_bp)
app.register_blueprint(produtos_bp)
app.register_blueprint(dashboard_bp)

# --- ROTA PRINCIPAL (ATUALIZADA COM O LINK PÚBLICO) ---
@app.route('/')
def index():
    # Link público exato que você forneceu (Não pede login)
    powerbi_url = "https://app.powerbi.com/view?r=eyJrIjoiOTZhOThlYmMtODcxNy00MjQ1LTk0Y2QtZWUxZGI3ZjJhZjU0IiwidCI6IjVmYWMzYWEzLWFhOTMtNGMxMS1iNDQ5LThjY2VhZjZjNjAzMiJ9"
    
    # Renderiza direto o dashboard ao iniciar o sistema
    return render_template('dashboard.html', powerbi_url=powerbi_url)

if __name__ == '__main__':
    app.run(debug=True, port=5000)