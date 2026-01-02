from flask import Flask, render_template
from routes.financeiro import financeiro_bp
from routes.calculadora import calculadora_bp
from routes.compras import compras_bp
from routes.produtos import produtos_bp  # <--- 1. ADICIONE ESSA IMPORTAÇÃO

app = Flask(__name__)
app.secret_key = "sigma_secret_key_2025"

# Registra as rotas
app.register_blueprint(financeiro_bp)
app.register_blueprint(calculadora_bp)
app.register_blueprint(compras_bp)
app.register_blueprint(produtos_bp)      # <--- 2. REGISTRE O BLUEPRINT AQUI

@app.route('/')
def index():
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)