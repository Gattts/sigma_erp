from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from utils.db import run_query
from datetime import datetime

compras_bp = Blueprint('compras', __name__)

# --- ROTA 1: PÁGINA DE NOVA ENTRADA ---
@compras_bp.route('/nova_entrada', methods=['GET', 'POST'])
def nova_entrada():
    if request.method == 'GET':
        df = run_query("SELECT id, sku, nome, fornecedor, importacao_propria FROM produtos ORDER BY nome")
        produtos = df.to_dict('records') if not df.empty else []
        return render_template('nova_entrada.html', produtos=produtos)
    
    # --- PROCESSAMENTO DO POST (SALVAR) ---
    data = request.form
    
    produto_id = data.get('produto_id')
    sku_novo = data.get('sku_novo')
    
    # Variáveis para o Histórico
    nome_prod_hist = ""
    sku_prod_hist = ""

    try:
        qtd = float(data.get('quantidade', 1))
        custo_final = float(data.get('custo_final_calculado') or 0)
        preco_partida = float(data.get('preco_partida') or 0)
        frete = float(data.get('frete') or 0)
        ipi = float(data.get('ipi') or 0)
        icms = float(data.get('icms') or 0)
        pis = float(data.get('pis') or 0)
        cofins = float(data.get('cofins') or 0)
        
        lucro_real = 'lucro_real' in data
        importacao = 'importacao_propria' in data
        fornecedor = data.get('fornecedor')
        nro_nf = data.get('nro_nf')
        # Data apenas YYYY-MM-DD pois sua coluna é DATE
        data_hoje = datetime.now().strftime('%Y-%m-%d') 

    except ValueError:
        flash('Erro nos valores numéricos.', 'danger')
        return redirect(url_for('compras.nova_entrada'))

    # CENÁRIO A: Produto Novo (Cria antes)
    if not produto_id and sku_novo:
        nome_prod_hist = data.get('nome_novo')
        sku_prod_hist = sku_novo
        
        sql_novo = "INSERT INTO produtos (sku, nome, fornecedor, quantidade, preco_final, importacao_propria) VALUES (:sku, :nome, :forn, 0, 0, :imp)"
        run_query(sql_novo, {'sku': sku_novo, 'nome': nome_prod_hist, 'forn': fornecedor, 'imp': 1 if importacao else 0})
        
        df_id = run_query("SELECT id FROM produtos WHERE sku = :sku", {'sku': sku_novo})
        if not df_id.empty:
            produto_id = df_id.iloc[0]['id']

    # CENÁRIO B: Produto Existente (Busca Nome/SKU para o histórico)
    elif produto_id:
        df_prod = run_query("SELECT sku, nome FROM produtos WHERE id = :id", {'id': produto_id})
        if not df_prod.empty:
            sku_prod_hist = df_prod.iloc[0]['sku']
            nome_prod_hist = df_prod.iloc[0]['nome']

    if not produto_id:
        flash('Erro: Produto não identificado.', 'danger')
        return redirect(url_for('compras.nova_entrada'))

    # 1. ATUALIZA O PRODUTO (Estoque Atual)
    sql_update = """
        UPDATE produtos 
        SET quantidade = :qtd, 
            preco_final = :custo,
            fornecedor = :forn,
            importacao_propria = :imp
        WHERE id = :id
    """
    run_query(sql_update, {
        'qtd': qtd,
        'custo': custo_final,
        'forn': fornecedor,
        'imp': 1 if importacao else 0,
        'id': produto_id
    })

    # 2. INSERE NO HISTÓRICO (Com os nomes de colunas CORRETOS do seu banco)
    sql_hist = """
        INSERT INTO historico_compras (
            produto_id, sku, nome_produto, 
            data_compra, fornecedor, nro_nf, quantidade,
            preco_partida, frete_rateio, ipi_percent, icms_percent, pis_percent, cofins_percent,
            custo_final, lucro_real, importacao_propria
        ) VALUES (
            :pid, :sku, :nome,
            :data, :forn, :nf, :qtd,
            :preco, :frete, :ipi, :icms, :pis, :cofins,
            :custo, :lr, :imp
        )
    """
    run_query(sql_hist, {
        'pid': produto_id,
        'sku': sku_prod_hist,
        'nome': nome_prod_hist,
        'data': data_hoje,
        'forn': fornecedor,
        'nf': nro_nf,
        'qtd': qtd,
        'preco': preco_partida,
        'frete': frete,   # Mapeia frete -> frete_rateio
        'ipi': ipi,       # Mapeia ipi -> ipi_percent
        'icms': icms,     # Mapeia icms -> icms_percent
        'pis': pis,       # Mapeia pis -> pis_percent
        'cofins': cofins, # Mapeia cofins -> cofins_percent
        'custo': custo_final,
        'lr': 1 if lucro_real else 0,
        'imp': 1 if importacao else 0
    })

    return redirect(url_for('compras.nova_entrada', sucesso=1))


# --- ROTA 2: API PARA O MODAL ---
@compras_bp.route('/api/historico/<int:produto_id>')
def api_obter_historico(produto_id):
    # Aqui fazemos o caminho inverso: Lemos do banco com os nomes "feios" (_percent)
    # e apelidamos (AS) para os nomes "bonitos" que o Javascript espera.
    sql = """
        SELECT 
            data_compra, fornecedor, nro_nf, quantidade, 
            preco_partida, 
            frete_rateio as frete, 
            ipi_percent as ipi, 
            icms_percent as icms, 
            pis_percent as pis, 
            cofins_percent as cofins,
            custo_final, lucro_real, importacao_propria
        FROM historico_compras 
        WHERE produto_id = :pid 
        ORDER BY id DESC
    """
    df = run_query(sql, {'pid': produto_id})
    
    if df.empty:
        return jsonify([])
    
    df = df.fillna(0)
    
    return jsonify(df.to_dict('records'))