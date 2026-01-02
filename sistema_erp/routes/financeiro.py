from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from utils.db import run_query, run_command
from datetime import date
import json

# Tenta importar o script do Bling (caso exista na pasta utils)
try:
    from utils.baixa_contas import processar_baixa_em_lote
except ImportError:
    processar_baixa_em_lote = None

# AQUI ESTAVA O ERRO: Precisamos definir o "financeiro_bp"
financeiro_bp = Blueprint('financeiro', __name__)

@financeiro_bp.route('/financeiro')
def index():
    # 1. Filtros
    filtro_forn = request.args.get('fornecedor', '')
    
    # 2. Query
    sql = "SELECT * FROM contas_pagar WHERE situacao = 'Aberto' "
    params = {}
    if filtro_forn:
        sql += "AND fornecedor LIKE :forn "
        params['forn'] = f"%{filtro_forn}%"
    sql += "ORDER BY vencimento ASC"
    
    df = run_query(sql, params)
    contas = df.to_dict('records')
    total_aberto = df['valor'].sum() if not df.empty else 0.0
    
    # Passamos a data de hoje para comparar vencimentos no HTML
    return render_template('financeiro.html', contas=contas, total=total_aberto, today=date.today())

@financeiro_bp.route('/financeiro/baixa/<int:id>', methods=['POST'])
def baixa_individual(id):
    run_command("UPDATE contas_pagar SET situacao='Pago', data_pagamento=:hj WHERE id=:id", 
                {"hj": date.today(), "id": id})
    return redirect(url_for('financeiro.index'))

# --- NOVA ROTA: BAIXA EM MASSA (Recebe JSON do JavaScript) ---
@financeiro_bp.route('/financeiro/baixa_lote', methods=['POST'])
def baixa_lote():
    dados = request.get_json()
    ids = dados.get('ids', [])
    banco_id = dados.get('banco_id') # ID do Bling (ex: 12345)
    forma_id = dados.get('forma_id') # ID do Bling (ex: 54321)
    dt_pg = dados.get('data_pagamento', str(date.today()))

    if not ids:
        return jsonify({'sucesso': False, 'msg': 'Nenhum item selecionado.'})

    # Se o script de integração existir, usa ele. Se não, baixa só local.
    if processar_baixa_em_lote:
        resultado = processar_baixa_em_lote(ids, dt_pg, int(banco_id), int(forma_id))
        return jsonify(resultado)
    else:
        # Baixa Local Simples (Sem Bling)
        for id_conta in ids:
            run_command("UPDATE contas_pagar SET situacao='Pago', data_pagamento=:dt WHERE id=:id",
                        {"dt": dt_pg, "id": id_conta})
        return jsonify({'sucesso': True, 'msg': f'{len(ids)} baixados localmente (Sem Bling).'})