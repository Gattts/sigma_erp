from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils.db import run_query, run_command
from datetime import datetime

compras_bp = Blueprint('compras', __name__)

# --- ROTA DA TELA DE NOVA ENTRADA ---
@compras_bp.route('/nova_entrada')
def nova_entrada():
    # 1. Lista de Produtos para o Select
    produtos = run_query("SELECT id, sku, nome FROM produtos ORDER BY nome")
    lista_produtos = produtos.to_dict('records') if not produtos.empty else []
    
    # 2. Lista de Fornecedores para o Datalist
    sql_forn = "SELECT DISTINCT fornecedor FROM produtos WHERE fornecedor IS NOT NULL ORDER BY fornecedor"
    df_forn = run_query(sql_forn)
    lista_fornecedores = df_forn['fornecedor'].tolist() if not df_forn.empty else []

    return render_template('nova_entrada.html', produtos=lista_produtos, fornecedores=lista_fornecedores)

# --- ROTA QUE PROCESSA O FORMULÁRIO ---
@compras_bp.route('/salvar_entrada', methods=['POST'])
def salvar_entrada():
    # 1. Captura dados do formulário
    produto_id_raw = request.form.get('produto_id') # Se vier do select existente
    novo_produto_nome = request.form.get('novo_produto_nome') # Se for criar novo
    
    fornecedor = request.form.get('fornecedor')
    nro_nf = request.form.get('nro_nf')
    data_hoje = datetime.now().strftime('%Y-%m-%d')

    # Funções auxiliares de conversão
    def get_float(name):
        try: return float(request.form.get(name, '0').replace(',', '.'))
        except: return 0.0
    
    def get_int(name):
        try: return int(request.form.get(name, '0'))
        except: return 0

    qtd = get_int('quantidade')
    preco_unit = get_float('preco_unit')
    frete_unit = get_float('frete_unit')
    
    # Impostos e Custo Final (Calculados no JS, mas salvamos o bruto aqui)
    # O ideal seria recalcular no backend para segurança, mas vamos confiar no input por enquanto ou salvar o bruto
    # Para simplificar e manter integridade, vamos salvar o que veio
    
    # Como não temos todos os campos de cálculo vindo do form HTML antigo, 
    # vamos assumir que Custo Final = (Preço + Frete) - Impostos Recuperáveis
    # Se você quiser salvar exatamente os campos do form:
    
    icms = get_float('icms_aliq')
    ipi = get_float('ipi_aliq')
    pis = get_float('pis_aliq')
    cofins = get_float('cofins_aliq')
    
    lucro_real = 1 if request.form.get('lucro_real') == 'on' else 0
    importacao = 1 if request.form.get('importacao') == 'on' else 0

    # Cálculo simples de Custo Final (Backend) para garantir consistência
    custo_final = preco_unit + frete_unit
    
    # Se for lucro real, abate impostos
    creditos = 0.0
    if lucro_real:
        # PIS/COFINS recupera
        creditos += (preco_unit * (pis/100)) + (preco_unit * (cofins/100))
        # ICMS recupera
        creditos += (preco_unit * (icms/100))
    
    custo_final = custo_final - creditos

    # 2. Lógica de Produto (Existente ou Novo)
    produto_id = None
    
    if novo_produto_nome:
        # Cria produto novo básico
        sql_new = "INSERT INTO produtos (nome, sku, fornecedor, quantidade, preco_final) VALUES (:nome, :sku, :forn, :qtd, :custo)"
        # Gera um SKU temporário
        sku_temp = f"NEW-{int(datetime.now().timestamp())}"
        run_command(sql_new, {
            'nome': novo_produto_nome, 'sku': sku_temp, 'forn': fornecedor, 
            'qtd': 0, 'custo': 0.0
        })
        # Pega o ID criado
        df_id = run_query("SELECT id FROM produtos WHERE sku = :sku", {'sku': sku_temp})
        if not df_id.empty:
            produto_id = int(df_id.iloc[0]['id'])
    else:
        try:
            produto_id = int(produto_id_raw)
        except:
            flash('Erro: Produto inválido.', 'danger')
            return redirect(url_for('compras.nova_entrada'))

    # 3. Inserir no Histórico (AGORA COM TODOS OS CAMPOS NOVOS)
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
        'icms': icms, 'ipi': ipi, 'pis': pis, 'cofins': cofins,
        'l_real': lucro_real, 'imp': importacao
    }
    
    if not run_command(sql_hist, params_hist):
        flash('Erro ao salvar no histórico.', 'danger')
        return redirect(url_for('compras.nova_entrada'))

    # 4. Atualizar Estoque e Preço no Produto Principal
    # (Poderíamos fazer média ponderada, mas aqui vamos atualizar para o custo atual)
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

    flash(f'Entrada registrada com sucesso! Custo atualizado para R$ {custo_final:.2f}', 'success')
    return redirect(url_for('produtos.index'))