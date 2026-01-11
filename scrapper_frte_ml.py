import pandas as pd
import requests
import io
import re

def parse_peso_limite(texto_peso):
    texto = str(texto_peso).lower().strip()
    if 'até' in texto:
        numeros = re.findall(r'[\d\.,]+', texto)
        if not numeros: return 0.0
        valor = float(numeros[0].replace(',', '.'))
        if 'kg' in texto: return valor
        if 'g' in texto: return valor / 1000.0
    if ' a ' in texto:
        try:
            parte_superior = texto.split(' a ')[1]
            numeros = re.findall(r'[\d\.,]+', parte_superior)
            if not numeros: return 0.0
            valor = float(numeros[0].replace(',', '.'))
            if 'kg' in parte_superior: return valor
            if 'g' in parte_superior: return valor / 1000.0
        except: return 0.0
    return 0.0

def limpar_preco(valor_str):
    if isinstance(valor_str, (int, float)): return float(valor_str)
    limpo = re.sub(r'[^\d,]', '', str(valor_str))
    return float(limpo.replace(',', '.')) if limpo else 0.0

def gerar_dicionario_ml_multitabela():
    url = "https://www.mercadolivre.com.br/ajuda/40538"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    print("1. Baixando e analisando tabelas (Filtrando Novos)...")
    try:
        response = requests.get(url, headers=headers)
        dfs = pd.read_html(io.StringIO(response.text))
        
        # Filtra tabelas válidas
        tabelas_frete = []
        for i, df in enumerate(dfs):
            df_clean = df.dropna()
            # Critério: mais de 15 linhas (faixas de peso) e pelo menos 2 colunas
            if len(df_clean) > 15 and df_clean.shape[1] >= 2:
                tabelas_frete.append(df_clean)

        print(f"   -> Encontradas {len(tabelas_frete)} tabelas de frete no total.")

        # --- CORREÇÃO: IGNORA A PRIMEIRA (USADOS) ---
        if len(tabelas_frete) > 5:
            print("   ⚠️ Detectada tabela extra (Usados). Ignorando a Tabela 0...")
            tabelas_novos = tabelas_frete[1:] # Pula a primeira
        else:
            tabelas_novos = tabelas_frete

        chaves_ordenadas = ["79-99", "100-119", "120-149", "150-199", "200+"]
        tabela_final = {}

        for i, df in enumerate(tabelas_novos):
            if i >= len(chaves_ordenadas): break
            
            chave = chaves_ordenadas[i]
            lista_tuplas = []
            
            # Pega coluna 0 (Peso) e última coluna (Preço com desconto)
            col_peso_idx = 0
            col_preco_idx = -1 
            
            for index, row in df.iterrows():
                try:
                    peso_txt = str(row.iloc[col_peso_idx])
                    preco_txt = str(row.iloc[col_preco_idx])
                    
                    p_limite = parse_peso_limite(peso_txt)
                    p_valor = limpar_preco(preco_txt)
                    
                    if p_limite > 0 and p_valor > 0:
                        lista_tuplas.append((p_limite, p_valor))
                except: continue
            
            if lista_tuplas:
                lista_tuplas.sort(key=lambda x: x[0])
                tabela_final[chave] = lista_tuplas
                # Pega o primeiro valor para mostrar no log como referência
                base_ref = lista_tuplas[0][1] if lista_tuplas else 0
                print(f"   ✅ Mapeado: Tabela {i+1} (Original {i+1}) -> Faixa '{chave}' (Base: {base_ref})")

        return tabela_final

    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        return None

if __name__ == "__main__":
    dic = gerar_dicionario_ml_multitabela()
    
    if dic:
        print("\n\n⬇️ --- TABELA CORRIGIDA (NOVOS) --- ⬇️\n")
        print("TABELA_FRETE_ML = {")
        for k in ["79-99", "100-119", "120-149", "150-199", "200+"]:
            if k in dic:
                print(f'    "{k}": {dic[k]},')
        print("}")
        print("\n⬆️ ------------------------------- ⬆️")
    else:
        print("Falha na extração.")