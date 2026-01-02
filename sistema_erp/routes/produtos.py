from flask import Blueprint, render_template, request
from utils.db import run_query

produtos_bp = Blueprint('produtos', __name__)

@produtos_bp.route('/produtos')
def index():
    query_search = request.args.get('q', '')
    
    # --- AQUI ESTÁ A MÁGICA ---
    # Usamos uma SUB-CONSULTA (SELECT ... LIMIT 1) para pegar a quantidade
    # da última entrada no histórico. Se não tiver histórico, mostra 0.
    sql = """
        SELECT 
            p.id, 
            p.sku, 
            p.nome, 
            p.fornecedor, 
            p.preco_final,
            COALESCE(
                (SELECT quantidade 
                 FROM historico_compras 
                 WHERE produto_id = p.id 
                 ORDER BY id DESC 
                 LIMIT 1), 
            0) as quantidade
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