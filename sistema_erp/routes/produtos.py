from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from utils.db import run_query, run_command

produtos_bp = Blueprint('produtos', __name__)

# --- 1. LISTAGEM ---
@produtos_bp.route('/produtos')
def index():
    query_search = request.args.get('q', '')
    
    sql = """
        SELECT 
            p.id, p.sku, p.nome, p.fornecedor, p.preco_final,
            COALESCE(
                (SELECT quantidade FROM historico_compras 
                 WHERE produto_id = p.id ORDER BY id DESC LIMIT 1), 
            p.quantidade) as quantidade
        FROM produtos p
    """
    
    params = {}
    if query_search:
        sql += " WHERE p.nome LIKE :q OR p.sku LIKE :q"
        params['q'] = f"%{query_search}%"
    
    sql += " ORDER BY p.nome"
    
    df = run_query(sql, params)
    produtos_lista = df.to_dict('records') if not df.empty else []
    
    return render_template('produtos.html', produtos=produtos_lista)

# --- 2. TELA NOVO ---
@produtos_bp.route('/produtos/novo')
def novo():
    return render_template('nova_entrada.html') 

# --- 3. SALVAR NOVO ---
@produtos_bp.route('/produtos/salvar', methods=['POST'])
def salvar():
    sku = request.form.get('sku')
    nome = request.form.get('nome')
    fornecedor = request.form.get('fornecedor')
    
    def get_float(name):
        try: return float(request.form.get(name, 0).replace(',', '.'))
        except: return 0.0
    
    def get_int(name):
        try: return int(request.form.get(name, 0))
        except: return 0

    peso = get_float('peso')
    altura = get_float('altura')
    largura = get_float('largura')
    comprimento = get_float('comprimento')
    
    qtd_cx_master = get_int('qtd_cx_master')
    altura_master = get_float('altura_master')
    largura_master = get_float('largura_master')
    comprimento_master = get_float('comprimento_master')

    sql = """
        INSERT INTO produtos (
            sku, nome, fornecedor, preco_final, quantidade,
            peso, altura, largura, comprimento,
            qtd_cx_master, altura_master, largura_master, comprimento_master
        )
        VALUES (
            :sku, :nome, :fornecedor, 0.00, 0,
            :peso, :altura, :largura, :comprimento,
            :qtd_cx_master, :altura_master, :largura_master, :comprimento_master
        )
    """
    params = {
        'sku': sku, 'nome': nome, 'fornecedor': fornecedor,
        'peso': peso, 'altura': altura, 'largura': largura, 'comprimento': comprimento,
        'qtd_cx_master': qtd_cx_master, 'altura_master': altura_master, 
        'largura_master': largura_master, 'comprimento_master': comprimento_master
    }
    
    if run_command(sql, params):
        flash('Produto cadastrado com sucesso!', 'success')
    else:
        flash('Erro ao cadastrar produto.', 'danger')
        
    return redirect(url_for('produtos.index'))

# --- 4. ATUALIZAR PRODUTO ---
@produtos_bp.route('/produtos/editar', methods=['POST'])
def editar():
    id_prod = request.form.get('id')
    nome = request.form.get('nome')
    sku = request.form.get('sku')
    fornecedor = request.form.get('fornecedor')

    def get_float(name):
        try: return float(request.form.get(name, 0).replace(',', '.'))
        except: return 0.0
    
    def get_int(name):
        try: return int(request.form.get(name, 0))
        except: return 0

    params = {
        'id': id_prod, 'nome': nome, 'sku': sku, 'fornecedor': fornecedor,
        'peso': get_float('peso'),
        'altura': get_float('altura'),
        'largura': get_float('largura'),
        'comprimento': get_float('comprimento'),
        'qtd_cx_master': get_int('qtd_cx_master'),
        'altura_master': get_float('altura_master'),
        'largura_master': get_float('largura_master'),
        'comprimento_master': get_float('comprimento_master')
    }

    sql = """
        UPDATE produtos SET
            nome = :nome,
            sku = :sku,
            fornecedor = :fornecedor,
            peso = :peso,
            altura = :altura,
            largura = :largura,
            comprimento = :comprimento,
            qtd_cx_master = :qtd_cx_master,
            altura_master = :altura_master,
            largura_master = :largura_master,
            comprimento_master = :comprimento_master
        WHERE id = :id
    """

    if run_command(sql, params):
        return jsonify({'success': True, 'message': 'Produto atualizado!'})
    else:
        return jsonify({'success': False, 'message': 'Erro no banco de dados.'}), 500

# --- 5. EXCLUIR PRODUTO ---
@produtos_bp.route('/produtos/excluir', methods=['POST'])
def excluir():
    id_prod = request.form.get('id')
    sql = "DELETE FROM produtos WHERE id = :id"
    if run_command(sql, {'id': id_prod}):
        return jsonify({'success': True, 'message': 'Produto excluído com sucesso!'})
    else:
        return jsonify({'success': False, 'message': 'Erro ao excluir produto.'}), 500

# --- 6. API DETALHES (CORRIGIDA) ---
@produtos_bp.route('/api/produto/detalhes/<int:id>', methods=['GET'])
def get_produto_detalhes(id):
    # REMOVIDO: importacao_propria (não existe na tabela produtos)
    query = """
        SELECT 
            id, sku, nome, fornecedor, quantidade, preco_final, 
            peso, altura, largura, comprimento,
            qtd_cx_master, altura_master, largura_master, comprimento_master
        FROM produtos 
        WHERE id = :id
    """
    df = run_query(query, {'id': id})
    
    if df.empty: return jsonify({'error': 'Não encontrado'}), 404
        
    p = df.iloc[0].to_dict()
    
    def safe_float(val): 
        try: return float(val) if val else 0.0
        except: return 0.0
    
    def safe_int(val):
        try: return int(val) if val else 0
        except: return 0

    p['peso'] = safe_float(p.get('peso'))
    p['altura'] = safe_float(p.get('altura'))
    p['largura'] = safe_float(p.get('largura'))
    p['comprimento'] = safe_float(p.get('comprimento'))
    
    p['qtd_cx_master'] = safe_int(p.get('qtd_cx_master'))
    p['altura_master'] = safe_float(p.get('altura_master'))
    p['largura_master'] = safe_float(p.get('largura_master'))
    p['comprimento_master'] = safe_float(p.get('comprimento_master'))
    
    return jsonify(p)

# --- 7. API HISTÓRICO ---
@produtos_bp.route('/api/historico/<int:prod_id>')
def get_historico(prod_id):
    sql = """
        SELECT 
            id,
            data_compra, nro_nf, fornecedor, quantidade, 
            preco_partida, frete, custo_final,
            icms, ipi, pis, cofins,
            lucro_real, importacao_propria
        FROM historico_compras
        WHERE produto_id = :id
        ORDER BY data_compra DESC, id DESC
    """
    
    df = run_query(sql, {'id': prod_id})
    
    if df.empty: return jsonify([])
    
    historico = df.to_dict('records')
    
    for item in historico:
        try:
            if item['data_compra']:
                item['data_compra'] = str(item['data_compra'])
                partes = item['data_compra'].split('-')
                if len(partes) == 3:
                    item['data_compra'] = f"{partes[2]}/{partes[1]}/{partes[0]}"
        except: pass
        item['lucro_real'] = bool(item['lucro_real'])
        item['importacao_propria'] = bool(item['importacao_propria'])

    return jsonify(historico)

# --- 8. EXCLUIR ITEM HISTÓRICO ---
@produtos_bp.route('/api/historico/excluir', methods=['POST'])
def excluir_historico_item():
    id_hist = request.form.get('id')
    sql = "DELETE FROM historico_compras WHERE id = :id"
    if run_command(sql, {'id': id_hist}):
        return jsonify({'success': True, 'message': 'Registro excluído!'})
    else:
        return jsonify({'success': False, 'message': 'Erro ao excluir registro.'}), 500