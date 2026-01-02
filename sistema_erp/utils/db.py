import os
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# --- CONFIGURAÇÃO DO BANCO DE DADOS (ATUALIZADA) ---
# Se não houver variável de ambiente, usa estes valores padrão (Produção)
DB_HOST = os.getenv('DB_HOST', 'market-db.clsgwcgyufqp.us-east-2.rds.amazonaws.com')
DB_USER = os.getenv('DB_USER', 'admin')
DB_PASS_RAW = os.getenv('DB_PASS', 'Sigmacomjp25')
DB_NAME = os.getenv('DB_NAME', 'marketmanager')

# Tratamento de segurança para senha (caso tenha @, /, etc)
encoded_pass = quote_plus(DB_PASS_RAW)

# String de Conexão SQLAlchemy
DB_CONN = f'mysql+pymysql://{DB_USER}:{encoded_pass}@{DB_HOST}:3306/{DB_NAME}?connect_timeout=60'

def get_engine():
    """Cria e retorna o motor de conexão."""
    return create_engine(DB_CONN)

def run_query(query, params=None):
    """
    Executa comandos SELECT e retorna um DataFrame do Pandas.
    Uso: df = run_query("SELECT * FROM produtos")
    """
    if params is None: params = {}
    try:
        engine = get_engine()
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn, params=params)
    except Exception as e:
        print(f"❌ Erro na Query: {e}")
        return pd.DataFrame() # Retorna vazio para não quebrar o site

def run_command(sql, params=None):
    """
    Executa comandos de ação (INSERT, UPDATE, DELETE).
    Uso: run_command("UPDATE produtos SET ...")
    """
    if params is None: params = {}
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text(sql), params)
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Erro no Comando: {e}")
        return False