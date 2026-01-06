from flask import Blueprint, render_template, request, jsonify # Adicionado jsonify
from utils.db import run_query, run_command
from datetime import datetime

compras_bp = Blueprint('compras', __name__)

# --- ROTA DA TELA DE NOVA ENTRADA ---
@compras_bp.route('/nova_entrada')
def nova_entrada():
    produtos = run_query("SELECT id, sku, nome FROM produtos ORDER BY nome")
    lista_produtos = produtos.to_dict('records') if not produtos.empty else []
    
    sql_forn = "SELECT DISTINCT fornecedor FROM produtos WHERE fornecedor IS NOT NULL ORDER BY fornecedor"
    df_forn = run_query(sql_forn)
    lista_fornecedores = df_forn['fornecedor'].tolist() if not df_forn.empty else []

    return render_template('nova_entrada.html', produtos=lista_produtos, fornecedores=lista_fornecedores)

# --- ROTA QUE PROCESSA O FORMULÁRIO (AGORA RETORNA JSON) ---
@compras_bp.route('/salvar_entrada', methods=['POST'])
def salvar_entrada():
    # 1. Captura dados
    produto_id_raw = request.form.get('produto_id')
    # Verifica checkbox novo (Alguns browsers mandam 'on', outros não mandam nada)
    check_novo = request.form.get('check_novo_produto')
    
    nome_novo = request.form.get('nome_novo')
    sku_novo = request.form.get('sku_novo')
    
    fornecedor = request.form.get('fornecedor')
    nro_nf = request.form.get('nro_nf')
    data_hoje = datetime.now().strftime('%Y-%m-%d')

    def get_float(name):
        try: return float(request.form.get(name, '0').replace(',', '.'))
        except: return 0.0
    
    def get_int(name):
        try: return int(request.form.get(name, '0'))
        except: return 0

    qtd = get_int('quantidade')
    preco_unit = get_float('preco_partida')
    frete_unit = get_float('frete')
    
    icms_rate = get_float('icms')
    ipi_rate = get_float('ipi')
    pis_rate = get_float('pis')
    cofins_rate = get_float('cofins')
    
    lucro_real = 1 if request.form.get('lucro_real') == 'on' else 0
    importacao = 1 if request.form.get('importacao_propria') == 'on' else 0

    # --- CÁLCULO FINANCEIRO ---
    val_ipi = preco_unit * (ipi_rate / 100)
    val_icms = preco_unit * (icms_rate / 100)
    
    base_pis_cofins = preco_unit - val_icms
    if base_pis_cofins < 0: base_pis_cofins = 0
    
    val_pis = base_pis_cofins * (pis_rate / 100)
    val_cofins = base_pis_cofins * (cofins_rate / 100)

    custo_bruto = preco_unit + frete_unit + val_ipi
    
    creditos = 0.0
    if lucro_real:
        creditos = val_icms + val_pis + val_cofins
    
    custo_final = custo_bruto - creditos

    # 2. Lógica de Produto
    produto_id = None
    
    # Se checkbox marcado OU nome preenchido
    if check_novo == 'on' or (nome_novo and nome_novo.strip() != ''):
        if not nome_novo:
            return jsonify({'success': False, 'message': 'Nome do produto obrigatório para novo cadastro.'})

        if not sku_novo:
            sku_novo = f"NEW-{int(datetime.now().timestamp())}"

        sql_new = """
            INSERT INTO produtos (nome, sku, fornecedor, quantidade, preco_final) 
            VALUES (:nome, :sku, :forn, :qtd, :custo)
        """
        if run_command(sql_new, {'nome': nome_novo, 'sku': sku_novo, 'forn': fornecedor, 'qtd': 0, 'custo': 0.0}):
            df_id = run_query("SELECT id FROM produtos WHERE sku = :sku", {'sku': sku_novo})
            if not df_id.empty:
                produto_id = int(df_id.iloc[0]['id'])
        else:
            return jsonify({'success': False, 'message': 'Erro ao criar novo produto.'})
            
    else:
        try:
            produto_id = int(produto_id_raw)
        except:
            return jsonify({'success': False, 'message': 'Selecione um produto válido.'})

    # 3. Inserir no Histórico
    sql_hist = """
        INSERT INTO historico_compras (
            produto_id, data_compra, nro_nf, fornecedor, quantidade,
            preco_partida, frete, custo_final,
            icms, ipi, pis, cofins, lucro_real, importacao_propria
        ) VALUES (
            :pid, :data, :nf, :forn, :qtd,
            :preco, :frete, :final,
            :icms, :ipi, :pis, :cofins, :l_real, :imp
        )
    """
    params_hist = {
        'pid': produto_id, 'data': data_hoje, 'nf': nro_nf, 'forn': fornecedor, 'qtd': qtd,
        'preco': preco_unit, 'frete': frete_unit, 'final': custo_final,
        'icms': icms_rate, 'ipi': ipi_rate, 'pis': pis_rate, 'cofins': cofins_rate,
        'l_real': lucro_real, 'imp': importacao
    }
    
    if not run_command(sql_hist, params_hist):
        return jsonify({'success': False, 'message': 'Erro ao salvar histórico.'})

    # 4. Atualizar Produto Principal
    sql_update = """
        UPDATE produtos 
        SET quantidade = quantidade + :qtd,
            preco_final = :novo_custo,
            fornecedor = :forn
        WHERE id = :id
    """
    run_command(sql_update, {
        'qtd': qtd, 'novo_custo': custo_final, 'forn': fornecedor, 'id': produto_id
    })

    # RETORNA JSON DE SUCESSO
    return jsonify({
        'success': True, 
        'message': f'Entrada confirmada! Custo atualizado: R$ {custo_final:.2f}'
    })