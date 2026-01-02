from flask import Blueprint, render_template, request, jsonify
from utils.db import run_query
from utils.calculos import calcular_cenario, calcular_custo_aquisicao, str_to_float

calculadora_bp = Blueprint('calculadora', __name__)

@calculadora_bp.route('/calculadora')
def index():
    # Carrega produtos para o Select2
    produtos = run_query("SELECT id, sku, nome FROM produtos ORDER BY nome")
    lista_produtos = produtos.to_dict('records') if not produtos.empty else []
    return render_template('calculadora.html', produtos=lista_produtos)

# --- API 1: Busca dados do Produto (Modo Banco de Dados) ---
@calculadora_bp.route('/api/produto/<int:prod_id>')
def get_produto_info(prod_id):
    # Peso fixo 0.5kg por enquanto (até ter coluna peso)
    sql = """
        SELECT preco_final as custo, 0.5 as peso 
        FROM produtos WHERE id = :id
    """
    df = run_query(sql, {'id': prod_id})
    if df.empty:
        return jsonify({'error': 'Produto não encontrado'}), 404
    
    prod = df.iloc[0]
    return jsonify({
        'custo': prod['custo'],
        'peso': prod['peso']
    })

# --- API 2: Simula Custo de Compra (Modo Simulação) ---
@calculadora_bp.route('/api/simular_custo', methods=['POST'])
def simular_custo_api():
    data = request.json
    
    # Chama a mesma função que usamos na tela de Nova Entrada
    resultado = calcular_custo_aquisicao(
        pc=data.get('preco_nota', 0),
        frete=data.get('frete', 0),
        ipi=data.get('ipi', 0),
        outros=0, st_val=0, icms_frete=0,
        icms_prod=data.get('icms', 0),
        pis=data.get('pis', 0),
        cofins=data.get('cofins', 0),
        l_real=data.get('lucro_real', False)
    )
    
    return jsonify(resultado) # Retorna {custo_final: ..., creditos: ...}

# --- API 3: Calcula Venda (Cenário) ---
@calculadora_bp.route('/api/calcular', methods=['POST'])
def calcular_ajax():
    data = request.json
    
    impostos = {
        'icms': data.get('icms', 0),
        'difal': data.get('difal', 0)
    }
    
    resultado = calcular_cenario(
        margem_alvo=data.get('margem', 0),
        preco_manual=data.get('preco_manual', 0),
        comissao=data.get('comissao', 0),
        modo=data.get('modo'),
        canal=data.get('canal', 'Mercado Livre'),
        custo_base=str_to_float(data.get('custo', 0)),
        impostos=impostos,
        peso=data.get('peso', 0),
        is_full=False
    )
    
    return jsonify(resultado)