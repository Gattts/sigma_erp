from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from utils.db import run_query, run_command
from sqlalchemy import create_engine, text
import requests
import base64
import os
from datetime import datetime

produtos_bp = Blueprint('produtos', __name__)

# ... (MANTENHA AS ROTAS EXISTENTES: index, novo, salvar, editar, excluir, get_produto_detalhes, get_historico, excluir_historico_item) ...
# ... Copie e cole suas rotas anteriores aqui para economizar espaço, o foco é a rota nova abaixo ...

# --- MANTENHA AS ROTAS DE CRUD AQUI ---
# (Vou omitir as rotas padrão para focar na integração, mas você deve mantê-las no arquivo)

# ==============================================================================
# 🚀 ROTA DE INTEGRAÇÃO BLING (Atualizada para Banco ETL)
# ==============================================================================
@produtos_bp.route('/api/integracao/bling/importar', methods=['POST'])
def importar_do_bling():
    # 1. Configuração do Banco ETL (Onde estão as credenciais)
    etl_db_url = os.getenv('ETL_DB_URL')
    if not etl_db_url:
        return jsonify({'success': False, 'message': 'Configuração ETL_DB_URL não encontrada no Render.'})

    creds = None
    engine_etl = None

    try:
        # Conecta no banco externo para buscar credenciais
        engine_etl = create_engine(etl_db_url)
        with engine_etl.connect() as conn:
            # Busca apenas empresa ATIVA (ativo = 1)
            query = text("""
                SELECT id, client_id, client_secret, refresh_token 
                FROM empresas_bling 
                WHERE ativo = 1 
                LIMIT 1
            """)
            res = conn.execute(query).mappings().first()
            
            if not res:
                return jsonify({'success': False, 'message': 'Nenhuma empresa ativa encontrada no banco de credenciais.'})
            
            creds = dict(res)

    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro conexão Banco ETL: {str(e)}'})

    # 2. Autenticação e Renovação de Token (Bling V3)
    # Codifica Basic Auth
    auth_str = f"{creds['client_id']}:{creds['client_secret']}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    
    headers_auth = {
        'Authorization': f'Basic {b64_auth}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    payload_auth = {
        'grant_type': 'refresh_token',
        'refresh_token': creds['refresh_token']
    }

    access_token = None

    try:
        # Tenta renovar o token
        resp = requests.post('https://www.bling.com.br/Api/v3/oauth/token', headers=headers_auth, data=payload_auth, timeout=15)
        
        if resp.status_code == 200:
            data_token = resp.json()
            access_token = data_token['access_token']
            new_refresh = data_token['refresh_token']
            
            # --- CRÍTICO: SALVAR NOVO TOKEN NO BANCO ETL ---
            # Isso garante que seus scripts de extração continuem funcionando
            try:
                with engine_etl.begin() as conn:
                    update_sql = text("""
                        UPDATE empresas_bling 
                        SET refresh_token = :rt, 
                            access_token = :at, 
                            updated_at = NOW() 
                        WHERE id = :id
                    """)
                    conn.execute(update_sql, {
                        'rt': new_refresh, 
                        'at': access_token, 
                        'id': creds['id']
                    })
            except Exception as db_err:
                return jsonify({'success': False, 'message': f'Token renovado, mas falha ao salvar no banco: {str(db_err)}'})
                
        else:
            erro_msg = resp.json().get('error', {}).get('description', resp.text)
            return jsonify({'success': False, 'message': f'Bling recusou autenticação: {erro_msg}'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro na comunicação com Bling: {str(e)}'})

    # 3. Busca Produtos na API do Bling
    headers_api = {'Authorization': f'Bearer {access_token}'}
    # Filtros: criterio=1 (Ativos), tipo=P (Produto Simples/Composição)
    url_produtos = 'https://www.bling.com.br/Api/v3/produtos?limit=100&criterio=1&tipo=P'
    
    try:
        r = requests.get(url_produtos, headers=headers_api, timeout=20)
        if r.status_code != 200:
            return jsonify({'success': False, 'message': f'Erro ao baixar produtos: {r.text}'})

        dados = r.json().get('data', [])
        if not dados:
            return jsonify({'success': True, 'message': 'Conexão OK, mas nenhum produto encontrado no Bling.'})

        count_novos = 0
        count_up = 0

        # 4. Salva/Atualiza no Banco ERP (Local)
        for p in dados:
            sku = str(p.get('codigo', '')).strip()
            nome = str(p.get('nome', '')).strip()
            # Bling manda preço como float ou string, garantimos float
            preco = float(p.get('preco', 0))
            # Bling manda origem como 0, 1, 2... igual nosso padrão
            origem = str(p.get('origem', '0')) 
            
            if not sku or not nome: continue

            # Verifica se produto já existe no ERP pelo SKU
            existe = run_query("SELECT id FROM produtos WHERE sku = :sku", {'sku': sku})
            
            if existe.empty:
                # INSERE NOVO
                sql_ins = """
                    INSERT INTO produtos (sku, nome, fornecedor, origem, preco_final, quantidade)
                    VALUES (:sku, :nome, 'Bling Import', :origem, :preco, 0)
                """
                run_command(sql_ins, {'sku': sku, 'nome': nome, 'origem': origem, 'preco': preco})
                count_novos += 1
            else:
                # ATUALIZA EXISTENTE (Nome, Preço e Origem)
                # Não mexemos no estoque pois o ERP controla o estoque fisicamente
                sql_up = """
                    UPDATE produtos 
                    SET nome = :nome, 
                        preco_final = :preco, 
                        origem = :origem 
                    WHERE sku = :sku
                """
                run_command(sql_up, {'sku': sku, 'nome': nome, 'preco': preco, 'origem': origem})
                count_up += 1

        return jsonify({
            'success': True, 
            'message': f'Sincronização concluída! {count_novos} novos cadastrados, {count_up} atualizados.'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro fatal na importação: {str(e)}'})