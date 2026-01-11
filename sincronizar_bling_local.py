import pymysql
import requests
import base64
import time
import calendar
from datetime import datetime

# --- CONFIGURAÇÕES ---
DB_HOST_AWS = "marketmanager.clsgwcgyufqp.us-east-2.rds.amazonaws.com"
DB_USER_AWS = "admin"
DB_PASS_AWS = "sigmacomjp25"
DB_NAME_AWS = "sigma_erp"

DB_HOST_ETL = "177.153.209.166"
DB_USER_ETL = "sigmacomti"
DB_PASS_ETL = "Sigma#com13ti2025"
DB_NAME_ETL = "sigmacomti"

# Varre desde 2018 para garantir
ANOS_PARA_PROCESSAR = list(range(2018, 2027))

def get_connection_aws():
    return pymysql.connect(host=DB_HOST_AWS, user=DB_USER_AWS, password=DB_PASS_AWS, database=DB_NAME_AWS, port=3306, cursorclass=pymysql.cursors.DictCursor)

def get_connection_etl():
    return pymysql.connect(host=DB_HOST_ETL, user=DB_USER_ETL, password=DB_PASS_ETL, database=DB_NAME_ETL, port=3306, cursorclass=pymysql.cursors.DictCursor)

def obter_token_valido():
    print("1. Autenticando com Banco ETL...")
    creds = None
    try:
        conn = get_connection_etl()
        with conn.cursor() as cur:
            cur.execute("SELECT id, client_id, client_secret, refresh_token FROM empresas_bling WHERE ativo = 1 LIMIT 1")
            creds = cur.fetchone()
        conn.close()
    except Exception as e:
        print(f"❌ Erro conexão ETL: {e}")
        return None

    if not creds:
        print("❌ Nenhuma empresa ativa encontrada.")
        return None

    url_auth = 'https://www.bling.com.br/Api/v3/oauth/token'
    b64 = base64.b64encode(f"{creds['client_id']}:{creds['client_secret']}".encode()).decode()
    headers = {'Authorization': f'Basic {b64}', 'Content-Type': 'application/x-www-form-urlencoded'}
    
    print("   Renovando token...")
    try:
        r = requests.post(url_auth, headers=headers, 
                          data={'grant_type': 'refresh_token', 'refresh_token': creds['refresh_token']}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            conn = get_connection_etl()
            with conn.cursor() as cur:
                cur.execute("UPDATE empresas_bling SET refresh_token = %s, access_token = %s, updated_at = NOW() WHERE id = %s", 
                           (data['refresh_token'], data['access_token'], creds['id']))
            conn.commit()
            conn.close()
            return data['access_token']
        else:
            print(f"❌ Erro Bling Auth: {r.text}")
    except Exception as e:
        print(f"❌ Exceção Auth: {e}")
    return None

def salvar_no_banco(cursor, p, origem_tag="Bling Import", ignorar_status=False):
    sku = str(p.get('codigo', '')).strip()
    nome = str(p.get('nome', '')).strip()
    
    if not sku or not nome: return 0

    if not ignorar_status:
        situacao = str(p.get('situacao', ''))
        if situacao != 'A': return 0 

    try: preco = float(p.get('preco', 0))
    except: preco = 0.0
    
    origem = str(p.get('origem', '0'))
    
    try: peso = float(p.get('pesoBruto', 0) or 0)
    except: peso = 0.0
    
    dims = p.get('dimensoes', {})
    try: alt = float(dims.get('altura', 0) or 0)
    except: alt = 0.0
    try: larg = float(dims.get('largura', 0) or 0)
    except: larg = 0.0
    try: comp = float(dims.get('profundidade', 0) or 0)
    except: comp = 0.0

    cursor.execute("SELECT id FROM produtos WHERE sku = %s", (sku,))
    existe = cursor.fetchone()
    
    if not existe:
        sql = """INSERT INTO produtos (sku, nome, fornecedor, origem, preco_final, quantidade, peso, altura, largura, comprimento) 
                 VALUES (%s, %s, 'Bling Import', %s, %s, 0, %s, %s, %s, %s)"""
        cursor.execute(sql, (sku, nome, origem, preco, peso, alt, larg, comp))
        return 1
    else:
        sql = """UPDATE produtos SET nome=%s, preco_final=%s, origem=%s, peso=%s, altura=%s, largura=%s, comprimento=%s WHERE sku=%s"""
        cursor.execute(sql, (nome, preco, origem, peso, alt, larg, comp, sku))
        return 2

def buscar_variacoes_forca_bruta(token, id_pai, nome_pai, cursor_aws):
    """ Busca filhos OBRIGATORIAMENTE para todo produto """
    url = f'https://www.bling.com.br/Api/v3/produtos/{id_pai}/variacoes'
    headers = {'Authorization': f'Bearer {token}'}
    novos = 0
    try:
        # Timeout curto pois vamos chamar MUITAS vezes
        r = requests.get(url, headers=headers, timeout=4) 
        if r.status_code == 200:
            filhos = r.json().get('data', [])
            for f in filhos:
                if nome_pai not in f.get('nome', ''):
                    f['nome'] = f"{nome_pai} - {f.get('nome')}"
                
                # Salva Variação
                res = salvar_no_banco(cursor_aws, f, "Bling Var", ignorar_status=True)
                if res == 1: 
                    # print(f"      + Filho encontrado: {f.get('codigo')}")
                    novos += 1
    except: pass
    return novos

def processar_por_mes(token, ano, mes):
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    dt_ini = f"{ano}-{mes:02d}-01"
    dt_fim = f"{ano}-{mes:02d}-{ultimo_dia}"
    
    conn_aws = get_connection_aws()
    cursor_aws = conn_aws.cursor()
    
    url_base = 'https://www.bling.com.br/Api/v3/produtos'
    headers = {'Authorization': f'Bearer {token}'}
    
    params = {
        'page': 1, 'limit': 100, 
        'dataInclusaoInicial': dt_ini,
        'dataInclusaoFinal': dt_fim,
        'tipo': 'P' 
    }
    
    total_novos_mes = 0
    
    try:
        r = requests.get(url_base, headers=headers, params=params, timeout=20)
        
        if r.status_code == 429: time.sleep(2); return 0
        if r.status_code != 200: return 0
            
        dados = r.json().get('data', [])
        if not dados: return 0
        
        # print(f"   📂 {mes:02d}/{ano}: Analisando {len(dados)} pais...")

        for p in dados:
            # 1. Salva Pai
            res = salvar_no_banco(cursor_aws, p)
            if res == 1: total_novos_mes += 1
            
            # 2. Busca Variações (SEMPRE, IGNORANDO FORMATO)
            # O pulo do gato: assumimos que TODO pai pode ter filhos escondidos
            nf = buscar_variacoes_forca_bruta(token, p['id'], p['nome'], cursor_aws)
            total_novos_mes += nf
        
        conn_aws.commit()
        
    except Exception as e:
        print(f"❌ Erro {mes}/{ano}: {e}")
    
    conn_aws.close()
    
    if total_novos_mes > 0:
        print(f"   ✅ {mes:02d}/{ano}: {total_novos_mes} novos (Pais + Filhos).")
        
    return total_novos_mes

if __name__ == "__main__":
    print("--- 🚀 SINCRONIZAÇÃO PENTE FINO (FORÇA BRUTA) ---")
    token = obter_token_valido()
    
    total_geral = 0
    if token:
        for ano in ANOS_PARA_PROCESSAR:
            print(f"📅 Verificando {ano} (Buscando filhos em tudo)...")
            for mes in range(1, 13):
                total_geral += processar_por_mes(token, ano, mes)
                # Sem sleep aqui para ser mais agil, o buscar_variacoes ja segura
                
    print("-" * 40)
    print(f"✅ FINALIZADO! Total Recuperado Agora: {total_geral}")