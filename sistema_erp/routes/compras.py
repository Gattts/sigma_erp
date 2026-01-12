from flask import Blueprint, render_template, request, jsonify
from utils.db import run_query, run_command
from utils.calculos import calcular_custo_aquisicao, str_to_float
from datetime import datetime

compras_bp = Blueprint('compras', __name__)

@compras_bp.route('/nova_entrada')
def nova_entrada():
    # 1. Busca Produtos (SELECT * evita erro de coluna inexistente)
    produtos = run_query("SELECT * FROM produtos ORDER BY nome")
    lista_produtos = produtos.to_dict('records') if not produtos.empty else []
    
    # 2. Busca Fornecedores (Tenta pegar da tabela produtos se não tiver tabela de fornecedores)
    try:
        df_forn = run_query("SELECT DISTINCT fornecedor FROM produtos WHERE fornecedor IS NOT NULL ORDER BY fornecedor")
        lista_fornecedores = df_forn['fornecedor'].tolist() if not df_forn.empty else []
    except:
        lista_fornecedores = []

    return render_template('nova_entrada.html', produtos=lista_produtos, fornecedores=lista_fornecedores)

@compras_bp.route('/api/simular_custo', methods=['POST'])
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
        l_real=(data.get('regime') == 'Lucro Real')
    )
    return jsonify(resultado)

@compras_bp.route('/salvar_entrada', methods=['POST'])
def salvar_entrada():
    try:
        # --- 1. CAPTURA DE DADOS ---
        prod_id_raw = request.form.get('produto_id')
        check_novo = request.form.get('check_novo_produto')
        
        nome_novo = request.form.get('nome_novo')
        sku_novo = request.form.get('sku_novo')
        origem_novo = request.form.get('origem_novo', '0')
        
        fornecedor = request.form.get('fornecedor')
        nro_nf = request.form.get('nro_nf')
        data_hoje = datetime.now().strftime('%Y-%m-%d')

        # Helpers
        def get_float(name):
            val = request.form.get(name, '0')
            if not val: return 0.0
            # Trata 1.000,00 ou 1000.00
            clean_val = val.replace('.', '').replace(',', '.') if ',' in val and '.' in val else val.replace(',', '.')
            try: return float(clean_val)
            except: return 0.0

        qtd = int(request.form.get('quantidade', 1))
        preco_unit = get_float('preco_partida')
        frete_unit = get_float('frete')
        
        # Impostos para salvar no histórico
        icms_rate = get_float('icms')
        ipi_rate = get_float('ipi')
        pis_rate = get_float('pis')
        cofins_rate = get_float('cofins')
        
        lucro_real = 1 if request.form.get('lucro_real') == 'on' else 0
        importacao = 1 if request.form.get('importacao_propria') == 'on' else 0

        # --- 2. TRAVA DE SEGURANÇA DO CUSTO (RESOLUÇÃO DO PROBLEMA) ---
        # Lê o valor que o JavaScript calculou e colocou no input hidden
        custo_frontend = request.form.get('custo_final_calculado')
        
        if custo_frontend and get_float('custo_final_calculado') > 0:
            # USA O VALOR DA TELA (R$ 35,94)
            custo_final = get_float('custo_final_calculado')
        else:
            # Fallback: Calcula no backend se der erro
            calc = calcular_custo_aquisicao(
                pc=preco_unit, frete=frete_unit, ipi=ipi_rate, outros=0, st_val=0, 
                icms_frete=0, icms_prod=icms_rate, l_real=(lucro_real==1), pis=pis_rate, cofins=cofins_rate
            )
            custo_final = calc['custo_final']

        # --- 3. LÓGICA DE PRODUTO ---
        produto_id = None
        
        if check_novo == 'on':
            if not nome_novo: return jsonify({'success': False, 'message': 'Nome obrigatório.'})
            if not sku_novo: sku_novo = f"NEW-{int(datetime.now().timestamp())}"

            # Cria Produto Novo
            sql_new = """
                INSERT INTO produtos (nome, sku, fornecedor, origem, quantidade, preco_final) 
                VALUES (:nome, :sku, :forn, :orig, :qtd, :custo)
            """
            if run_command(sql_new, {'nome': nome_novo, 'sku': sku_novo, 'forn': fornecedor, 'orig': origem_novo, 'qtd': 0, 'custo': 0.0}):
                df_id = run_query("SELECT id FROM produtos WHERE sku = :sku", {'sku': sku_novo})
                if not df_id.empty: produto_id = int(df_id.iloc[0]['id'])
            else:
                return jsonify({'success': False, 'message': 'Erro ao criar produto.'})
        else:
            try: produto_id = int(prod_id_raw)
            except: return jsonify({'success': False, 'message': 'Selecione um produto.'})

        # --- 4. SALVAR HISTÓRICO (Baseado na sua imagem da tabela) ---
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
            'pid': produto_id, 
            'data': data_hoje, 
            'nf': nro_nf, 
            'forn': fornecedor, 
            'qtd': qtd,
            'preco': preco_unit, 
            'frete': frete_unit, 
            'final': custo_final, # Aqui vai o R$ 35,94 exato
            'icms': icms_rate, 
            'ipi': ipi_rate, 
            'pis': pis_rate, 
            'cofins': cofins_rate,
            'l_real': lucro_real, 
            'imp': importacao
        }
        
        if not run_command(sql_hist, params_hist):
            return jsonify({'success': False, 'message': 'Erro ao salvar no banco.'})

        # --- 5. ATUALIZA ESTOQUE E CUSTO DO PRODUTO ---
        sql_update = """
            UPDATE produtos 
            SET quantidade = quantidade + :qtd,
                preco_final = :novo_custo,
                fornecedor = :forn
            WHERE id = :id
        """
        run_command(sql_update, {'qtd': qtd, 'novo_custo': custo_final, 'forn': fornecedor, 'id': produto_id})

        custo_fmt = f"{custo_final:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return jsonify({'success': True, 'message': f'Entrada confirmada! Custo: R$ {custo_fmt}'})

    except Exception as e:
        print(f"Erro CRÍTICO: {e}")
        return jsonify({'success': False, 'message': f"Erro interno: {str(e)}"})