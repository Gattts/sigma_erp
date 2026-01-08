from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from utils.db import run_query, run_command
from sqlalchemy import create_engine, text
import requests
import base64
import os
from datetime import datetime

produtos_bp = Blueprint('produtos', __name__)

# ==============================================================================
# 1. LISTAGEM DE PRODUTOS (COM FILTROS)
# ==============================================================================
@produtos_bp.route('/produtos')
def index():
    q_busca = request.args.get('q', '')
    q_fornecedor = request.args.get('filtro_fornecedor', '')
    q_nf = request.args.get('filtro_nf', '')
    q_origem = request.args.get('filtro_origem', '')

    sql = """
        SELECT DISTINCT
            p.id, p.sku, p.nome, p.fornecedor, p.preco_final, p.origem,
            COALESCE(
                (SELECT quantidade FROM historico_compras 
                 WHERE produto_id = p.id ORDER BY id DESC LIMIT 1), 
            p.quantidade) as quantidade
        FROM produtos p
        LEFT JOIN historico_compras h ON p.id = h.produto_id
        WHERE 1=1
    """
    
    params = {}
    if q_busca:
        sql += " AND (p.nome LIKE :q OR p.sku LIKE :q)"
        params['q'] = f"%{q_busca}%"
    if q_fornecedor:
        sql += " AND p.fornecedor LIKE :forn"
        params['forn'] = f"%{q_fornecedor}%"
    if q_origem:
        sql += " AND p.origem = :orig"
        params['orig'] = q_origem
    if q_nf:
        sql += " AND h.nro_nf LIKE :nf"
        params['nf'] = f"%{q_nf}%"
    
    sql += " ORDER BY p.nome"
    
    df = run_query(sql, params)
    produtos_lista = df.to_dict('records') if not df.empty else []
    
    df_forn = run_query("SELECT DISTINCT fornecedor FROM produtos WHERE fornecedor IS NOT NULL ORDER BY fornecedor")
    lista_fornecedores = df_forn['fornecedor'].tolist() if not df_forn.empty else []
    
    return render_template('produtos.html', produtos=produtos_lista, fornecedores=lista_fornecedores)

# ==============================================================================
# 2. TELAS E AÇÕES DE CADASTRO (CRUD)
# ==============================================================================
@produtos_bp.route('/produtos/novo')
def novo():
    return render_template('nova_entrada.html') 

@produtos_bp.route('/produtos/salvar', methods=['POST'])
def salvar():
    sku = request.form.get('sku')
    nome = request.form.get('nome')
    fornecedor = request.form.get('fornecedor')
    origem = request.form.get('origem', '0')
    
    def get_float(name):
        try: return float(request.form.get(name, 0).replace(',', '.'))
        except: return 0.0
    def get_int(name):
        try: return int(request.form.get(name, 0))
        except: return 0

    params = {
        'sku': sku, 'nome': nome, 'fornecedor': fornecedor, 'origem': origem,
        'peso': get_float('peso'), 'altura': get_float('altura'), 
        'largura': get_float('largura'), 'comprimento': get_float('comprimento'),
        'qtd_cx_master': get_int('qtd_cx_master'), 'altura_master': get_float('altura_master'), 
        'largura_master': get_float('largura_master'), 'comprimento_master': get_float('comprimento_master')
    }

    sql = """
        INSERT INTO produtos (
            sku, nome, fornecedor, origem, preco_final, quantidade,
            peso, altura, largura, comprimento,
            qtd_cx_master, altura_master, largura_master, comprimento_master
        )
        VALUES (
            :sku, :nome, :fornecedor, :origem, 0.00, 0,
            :peso, :altura, :largura, :comprimento,
            :qtd_cx_master, :altura_master, :largura_master, :comprimento_master
        )
    """
    if run_command(sql, params):
        flash('Produto cadastrado com sucesso!', 'success')
    else:
        flash('Erro ao cadastrar produto.', 'danger')
        
    return redirect(url_for('produtos.index'))

@produtos_bp.route('/produtos/editar', methods=['POST'])
def editar():
    id_prod = request.form.get('id')
    
    def get_float(name):
        try: return float(request.form.get(name, 0).replace(',', '.'))
        except: return 0.0
    def get_int(name):
        try: return int(request.form.get(name, 0))
        except: return 0

    params = {
        'id': id_prod, 'nome': request.form.get('nome'), 'sku': request.form.get('sku'), 
        'fornecedor': request.form.get('fornecedor'), 'origem': request.form.get('origem'),
        'peso': get_float('peso'), 'altura': get_float('altura'),
        'largura': get_float('largura'), 'comprimento': get_float('comprimento'),
        'qtd_cx_master': get_int('qtd_cx_master'), 'altura_master': get_float('altura_master'),
        'largura_master': get_float('largura_master'), 'comprimento_master': get_float('comprimento_master')
    }

    sql = """
        UPDATE produtos SET
            nome = :nome, sku = :sku, fornecedor = :fornecedor, origem = :origem,
            peso = :peso, altura = :altura, largura = :largura, comprimento = :comprimento,
            qtd_cx_master = :qtd_cx_master, altura_master = :altura_master,
            largura_master = :largura_master, comprimento_master = :comprimento_master
        WHERE id = :id
    """
    if run_command(sql, params):
        return jsonify({'success': True, 'message': 'Produto atualizado!'})
    else:
        return jsonify({'success': False, 'message': 'Erro no banco de dados.'}), 500

@produtos_bp.route('/produtos/excluir', methods=['POST'])
def excluir():
    id_prod = request.form.get('id')
    if run_command("DELETE FROM produtos WHERE id = :id", {'id': id_prod}):
        return jsonify({'success': True, 'message': 'Produto excluído!'})
    else:
        return jsonify({'success': False, 'message': 'Erro ao excluir.'}), 500

# ==============================================================================
# 3. APIS DE DETALHES E HISTÓRICO
# ==============================================================================
@produtos_bp.route('/api/produto/detalhes/<int:id>', methods=['GET'])
def get_produto_detalhes(id):
    df = run_query("""
        SELECT 
            id, sku, nome, fornecedor, quantidade, preco_final, origem,
            peso, altura, largura, comprimento,
            qtd_cx_master, altura_master, largura_master, comprimento_master
        FROM produtos WHERE id = :id
    """, {'id': id})
    
    if df.empty: return jsonify({'error': 'Não encontrado'}), 404
        
    p = df.iloc[0].to_dict()
    def safe_float(val): return float(val) if val else 0.0
    def safe_int(val): return int(val) if val else 0

    p['peso'] = safe_float(p.get('peso'))
    p['altura'] = safe_float(p.get('altura'))
    p['largura'] = safe_float(p.get('largura'))
    p['comprimento'] = safe_float(p.get('comprimento'))
    p['qtd_cx_master'] = safe_int(p.get('qtd_cx_master'))
    p['altura_master'] = safe_float(p.get('altura_master'))
    p['largura_master'] = safe_float(p.get('largura_master'))
    p['comprimento_master'] = safe_float(p.get('comprimento_master'))
    if not p.get('origem'): p['origem'] = '0'

    return jsonify(p)

@produtos_bp.route('/api/historico/<int:prod_id>')
def get_historico(prod_id):
    sql = """
        SELECT 
            id, data_compra, nro_nf, fornecedor, quantidade, 
            preco_partida, frete, custo_final,
            icms, ipi, pis, cofins, lucro_real, importacao_propria
        FROM historico_compras
        WHERE produto_id = :id ORDER BY data_compra DESC, id DESC
    """
    df = run_query(sql, {'id': prod_id})
    if df.empty: return jsonify([])
    
    historico = df.to_dict('records')
    for item in historico:
        try:
            if item['data_compra']:
                val = str(item['data_compra'])
                if '-' in val: 
                    p = val.split('-')
                    if len(p)==3: item['data_compra'] = f"{p[2]}/{p[1]}/{p[0]}"
        except: pass
        item['lucro_real'] = bool(item['lucro_real'])
        item['importacao_propria'] = bool(item['importacao_propria'])

    return jsonify(historico)

@produtos_bp.route('/api/historico/excluir', methods=['POST'])
def excluir_historico_item():
    id_hist = request.form.get('id')
    if run_command("DELETE FROM historico_compras WHERE id = :id", {'id': id_hist}):
        return jsonify({'success': True, 'message': 'Registro excluído!'})
    else:
        return jsonify({'success': False, 'message': 'Erro ao excluir.'}), 500

# ==============================================================================
# 4. INTEGRAÇÃO BLING (Token Renovável no Banco ETL)
# ==============================================================================
@produtos_bp.route('/api/integracao/bling/importar', methods=['POST'])
def importar_do_bling():
    # 1. Configuração do Banco ETL
    etl_db_url = os.getenv('ETL_DB_URL')
    if not etl_db_url:
        return jsonify({'success': False, 'message': 'Configuração ETL_DB_URL não encontrada no Render.'})

    creds = None
    engine_etl = None

    try:
        engine_etl = create_engine(etl_db_url)
        with engine_etl.connect() as conn:
            # Busca empresa ATIVA
            query = text("SELECT id, client_id, client_secret, refresh_token FROM empresas_bling WHERE ativo = 1 LIMIT 1")
            res = conn.execute(query).mappings().first()
            if not res:
                return jsonify({'success': False, 'message': 'Nenhuma empresa ativa encontrada no banco de credenciais.'})
            creds = dict(res)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro conexão Banco ETL: {str(e)}'})

    # 2. Renovação do Token
    auth_str = f"{creds['client_id']}:{creds['client_secret']}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    headers_auth = {'Authorization': f'Basic {b64_auth}', 'Content-Type': 'application/x-www-form-urlencoded'}
    
    access_token = None
    try:
        resp = requests.post('https://www.bling.com.br/Api/v3/oauth/token', headers=headers_auth, 
                             data={'grant_type': 'refresh_token', 'refresh_token': creds['refresh_token']}, timeout=15)
        
        if resp.status_code == 200:
            data_token = resp.json()
            access_token = data_token['access_token']
            new_refresh = data_token['refresh_token']
            
            # Salva novo token no banco ETL para não quebrar outros scripts
            try:
                with engine_etl.begin() as conn:
                    conn.execute(text("UPDATE empresas_bling SET refresh_token = :rt, access_token = :at, updated_at = NOW() WHERE id = :id"), 
                                {'rt': new_refresh, 'at': access_token, 'id': creds['id']})
            except Exception as db_err:
                return jsonify({'success': False, 'message': f'Falha ao salvar token renovado: {str(db_err)}'})
        else:
            return jsonify({'success': False, 'message': f'Bling recusou autenticação: {resp.text}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro comunicação Bling: {str(e)}'})

    # 3. Importação dos Produtos
    headers_api = {'Authorization': f'Bearer {access_token}'}
    url_produtos = 'https://www.bling.com.br/Api/v3/produtos?limit=100&criterio=1&tipo=P'
    
    try:
        r = requests.get(url_produtos, headers=headers_api, timeout=20)
        dados = r.json().get('data', [])
        
        if not dados:
            return jsonify({'success': True, 'message': 'Conexão OK, nenhum produto encontrado.'})

        count_novos = 0
        count_up = 0

        for p in dados:
            sku = str(p.get('codigo', '')).strip()
            nome = str(p.get('nome', '')).strip()
            preco = float(p.get('preco', 0))
            origem = str(p.get('origem', '0'))
            
            if not sku or not nome: continue

            existe = run_query("SELECT id FROM produtos WHERE sku = :sku", {'sku': sku})
            
            if existe.empty:
                sql_ins = """
                    INSERT INTO produtos (sku, nome, fornecedor, origem, preco_final, quantidade)
                    VALUES (:sku, :nome, 'Bling Import', :origem, :preco, 0)
                """
                run_command(sql_ins, {'sku': sku, 'nome': nome, 'origem': origem, 'preco': preco})
                count_novos += 1
            else:
                sql_up = "UPDATE produtos SET nome = :nome, preco_final = :preco, origem = :origem WHERE sku = :sku"
                run_command(sql_up, {'sku': sku, 'nome': nome, 'preco': preco, 'origem': origem})
                count_up += 1

        return jsonify({'success': True, 'message': f'Sincronização OK! Novos: {count_novos}, Atualizados: {count_up}'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro na importação: {str(e)}'})