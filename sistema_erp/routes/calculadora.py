from flask import Blueprint, render_template, request, jsonify
from utils.db import run_query, run_command
from utils.calculos import calcular_cenario, calcular_custo_aquisicao, str_to_float
from datetime import datetime

calculadora_bp = Blueprint('calculadora', __name__)

@calculadora_bp.route('/calculadora')
def index():
    # 1. Busca produtos para o dropdown
    produtos = run_query("SELECT id, sku, nome, origem FROM produtos ORDER BY nome")
    lista_produtos = produtos.to_dict('records') if not produtos.empty else []

    # 2. Busca histórico de preços salvos (Para a Nova Aba)
    # Traz os últimos 50 cálculos salvos
    sql_hist = """
        SELECT 
            ps.id,
            ps.data_registro,
            p.sku,
            p.nome,
            ps.canal,
            ps.custo_base,
            ps.preco_venda,
            ps.margem_real,
            ps.lucro_liquido,
            ps.queima
        FROM precificacao_salva ps
        JOIN produtos p ON p.id = ps.produto_id
        ORDER BY ps.data_registro DESC
        LIMIT 50
    """
    try:
        hist_df = run_query(sql_hist)
        
        # Formata datas para exibir bonito (dd/mm/aaaa HH:MM)
        def fmt_data(d):
            try: return d.strftime('%d/%m/%Y %H:%M')
            except: return str(d)
        
        if not hist_df.empty:
            hist_df['data_registro'] = hist_df['data_registro'].apply(fmt_data)
            # Garante que 'queima' seja booleano
            hist_df['queima'] = hist_df['queima'].apply(lambda x: bool(x) if x else False)
            lista_historico = hist_df.to_dict('records')
        else:
            lista_historico = []
    except Exception as e:
        print(f"Erro ao buscar histórico salvo: {e}")
        lista_historico = []

    return render_template('calculadora.html', produtos=lista_produtos, historico_precos=lista_historico)


# --- API 1: Busca dados do Produto ---
@calculadora_bp.route('/api/produto/<int:prod_id>')
def get_produto_info(prod_id):
    sql = """
        SELECT preco_final as custo, 
               COALESCE(peso, 0.500) as peso,
               origem
        FROM produtos WHERE id = :id
    """
    df = run_query(sql, {'id': prod_id})
    
    if df.empty:
        return jsonify({'error': 'Produto não encontrado'}), 404
    
    prod = df.iloc[0]
    
    return jsonify({
        'custo': float(prod['custo']),
        'peso': float(prod['peso']),
        'origem': str(prod['origem']) if prod['origem'] is not None else "0"
    })


# --- API 2: Simula Custo ---
@calculadora_bp.route('/api/simular_custo', methods=['POST'])
def simular_custo_api():
    data = request.json
    resultado = calcular_custo_aquisicao(
        pc=data.get('preco_nota', 0),
        frete=data.get('frete', 0),
        ipi=data.get('ipi', 0),
        outros=0, st_val=0, icms_frete=0,
        icms_prod=data.get('icms', 0),
        pis=data.get('pis', 0),
        cofins=data.get('cofins', 0),
        regime=data.get('regime', 'Lucro Real')
    )
    return jsonify(resultado)


# --- API 3: Calcula Venda ---
@calculadora_bp.route('/api/calcular', methods=['POST'])
def calcular_ajax():
    data = request.json
    impostos = {
        'icms': data.get('icms', 0),
        'difal': data.get('difal', 0),
        'simples_aliquota': data.get('icms', 0)
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
        is_full=False,
        regime=data.get('regime', 'Lucro Real'),
        logistica_pct=data.get('logistica_pct', 0),
        origem_produto=data.get('origem_produto', '0')
    )
    return jsonify(resultado)


# --- API 4: SALVAR CÁLCULO (NOVA) ---
@calculadora_bp.route('/api/salvar_calculo', methods=['POST'])
def salvar_calculo():
    data = request.json
    
    # Validação básica
    if not data.get('produto_id'):
        return jsonify({'success': False, 'message': 'Selecione um produto existente para salvar.'})

    sql = """
        INSERT INTO precificacao_salva 
        (produto_id, canal, custo_base, preco_venda, margem_real, lucro_liquido, queima)
        VALUES (:pid, :canal, :custo, :preco, :margem, :lucro, :queima)
    """
    
    params = {
        'pid': data.get('produto_id'),
        'canal': data.get('canal'),
        'custo': data.get('custo'),
        'preco': data.get('preco'),
        'margem': data.get('margem'),
        'lucro': data.get('lucro'),
        'queima': 1 if data.get('queima') else 0 # Converte true/false para 1/0
    }
    
    if run_command(sql, params):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Erro ao salvar no banco de dados.'})


# --- API 5: HISTÓRICO DE COMPRAS (Essencial para o Modal) ---
@calculadora_bp.route('/api/historico_compras_calc/<int:prod_id>')
def get_historico_compras_calc(prod_id):
    # SQL Completa para garantir que o modal não trave
    sql = """
        SELECT 
            e.data_emissao, 
            e.numero_nf as nro_nf,
            e.lucro_real,
            COALESCE(f.nome_fantasia, 'Fornecedor N/D') as fornecedor, 
            i.quantidade, 
            i.valor_unitario as preco_partida,
            COALESCE(i.frete_rateio, 0) as frete,
            COALESCE(i.icms_percentual, 0) as icms,
            COALESCE(i.pis_percentual, 0) as pis,
            COALESCE(i.cofins_percentual, 0) as cofins,
            COALESCE(i.custo_final, i.valor_unitario) as custo_final
        FROM entrada_itens i
        JOIN entradas e ON e.id = i.entrada_id
        LEFT JOIN fornecedores f ON f.id = e.fornecedor_id
        WHERE i.produto_id = :id
        ORDER BY e.data_emissao DESC
        LIMIT 5
    """
    try:
        df = run_query(sql, {'id': prod_id})
        if df.empty: return jsonify([])
        
        def fmt_data(d):
            if not d: return '-'
            try: return d.strftime('%d/%m/%Y')
            except: return str(d)[:10]

        df['data_emissao'] = df['data_emissao'].apply(fmt_data)
        
        # Converte decimais para float
        cols_float = ['preco_partida', 'frete', 'icms', 'pis', 'cofins', 'custo_final']
        for col in cols_float:
            if col in df.columns:
                df[col] = df[col].astype(float)

        return jsonify(df.to_dict('records'))
    except Exception as e:
        print(f"Erro Historico Calc: {e}")
        return jsonify({'error': str(e)}), 500