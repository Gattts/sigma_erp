import re

# --- TABELA DE FRETE ATUALIZADA ---
TABELA_FRETE_ML = {
    "79-99": [(0.3, 11.97), (0.5, 12.87), (1.0, 13.47), (2.0, 14.07), (3.0, 14.97), (4.0, 16.17), (5.0, 17.07), (9.0, 26.67), (13.0, 39.57), (17.0, 44.07), (23.0, 51.57), (30.0, 59.37), (40.0, 61.17), (50.0, 63.27), (60.0, 67.47), (70.0, 72.27), (80.0, 75.57), (90.0, 83.97), (100.0, 95.97), (125.0, 107.37), (150.0, 113.97)],
    "100-119": [(0.3, 13.97), (0.5, 15.02), (1.0, 15.72), (2.0, 16.42), (3.0, 17.47), (4.0, 18.87), (5.0, 19.92), (9.0, 31.12), (13.0, 46.17), (17.0, 51.42), (23.0, 60.17), (30.0, 69.27), (40.0, 71.37), (50.0, 73.82), (60.0, 78.72), (70.0, 84.32), (80.0, 88.17), (90.0, 97.97), (100.0, 111.97), (125.0, 125.27), (150.0, 132.97)],
    "120-149": [(0.3, 15.96), (0.5, 17.16), (1.0, 17.96), (2.0, 18.76), (3.0, 19.96), (4.0, 21.56), (5.0, 22.76), (9.0, 35.56), (13.0, 52.76), (17.0, 58.76), (23.0, 68.76), (30.0, 79.16), (40.0, 81.56), (50.0, 84.36), (60.0, 89.96), (70.0, 96.36), (80.0, 100.76), (90.0, 111.96), (100.0, 127.96), (125.0, 143.16), (150.0, 151.96)],
    "150-199": [(0.3, 17.96), (0.5, 19.31), (1.0, 20.21), (2.0, 21.11), (3.0, 22.46), (4.0, 24.26), (5.0, 25.61), (9.0, 40.01), (13.0, 59.36), (17.0, 66.11), (23.0, 77.36), (30.0, 89.06), (40.0, 91.76), (50.0, 94.91), (60.0, 101.21), (70.0, 108.41), (80.0, 113.36), (90.0, 125.96), (100.0, 143.96), (125.0, 161.06), (150.0, 170.96)],
    "200+": [(0.3, 19.95), (0.5, 21.45), (1.0, 22.45), (2.0, 23.45), (3.0, 24.95), (4.0, 26.95), (5.0, 28.45), (9.0, 44.45), (13.0, 65.95), (17.0, 73.45), (23.0, 85.95), (30.0, 98.95), (40.0, 101.95), (50.0, 105.45), (60.0, 112.45), (70.0, 120.45), (80.0, 125.95), (90.0, 139.95), (100.0, 159.95), (125.0, 178.95), (150.0, 189.95)],
}

def str_to_float(valor_str):
    if not valor_str: return 0.0
    if isinstance(valor_str, (float, int)): return float(valor_str)
    try:
        return float(str(valor_str).replace(',', '.').strip())
    except:
        return 0.0

def obter_taxa_fixa_ml(preco):
    if preco >= 79.00: return 0.00 
    elif preco >= 50.00: return 6.75 
    elif preco >= 29.00: return 6.50 
    elif preco >= 12.50: return 6.25 
    else: return preco / 2.0 

def obter_frete_ml_tabela(preco, peso):
    if preco < 79.00: return 0.00
    faixa = "200+" 
    if preco < 100: faixa = "79-99"
    elif preco < 120: faixa = "100-119"
    elif preco < 150: faixa = "120-149"
    elif preco < 200: faixa = "150-199"
    
    lista = TABELA_FRETE_ML.get(faixa, TABELA_FRETE_ML["200+"])
    for limite, valor in lista:
        if peso <= limite: return valor
    return lista[-1][1]

def calcular_custo_aquisicao(pc, frete, ipi, outros, st_val, icms_frete, icms_prod, regime, pis=0, cofins=0):
    """
    Calcula o custo de aquisição considerando o regime tributário para aproveitamento de créditos.
    Regimes que NÃO aproveitam crédito: 'Simples Nacional', 'CPF'.
    Regimes que APROVEITAM crédito: 'Lucro Real', 'TTD 478'.
    """
    v_pc, v_frete, v_ipi = str_to_float(pc), str_to_float(frete), str_to_float(ipi)
    v_outros, v_st = str_to_float(outros), str_to_float(st_val)
    v_icms_frete, v_icms_prod = str_to_float(icms_frete), str_to_float(icms_prod)
    v_pis_pct, v_cofins_pct = str_to_float(pis), str_to_float(cofins)
    
    valor_ipi = v_pc * (v_ipi / 100)
    preco_medio = v_pc + v_frete + valor_ipi + v_outros + v_st
    
    credito_icms = 0.0
    credito_pis_cofins = 0.0
    
    # Lógica de Aproveitamento de Crédito baseada no Regime
    aproveita_credito = regime not in ['Simples Nacional', 'CPF']
    
    if aproveita_credito:
        c_frete = v_frete * (v_icms_frete / 100)
        c_prod = v_pc * (v_icms_prod / 100)
        credito_icms = c_frete + c_prod
        
        base_pis_cofins = v_pc - c_prod 
        if base_pis_cofins < 0: base_pis_cofins = 0
        
        val_pis = base_pis_cofins * (v_pis_pct / 100)
        val_cofins = base_pis_cofins * (v_cofins_pct / 100)
        credito_pis_cofins = val_pis + val_cofins
        
    total_creditos = credito_icms + credito_pis_cofins
    custo_final = preco_medio - total_creditos
    
    return {
        'custo_final': custo_final, 
        'creditos': total_creditos, 
        'icms_rec': credito_icms, 
        'pis_cof_rec': credito_pis_cofins,
        'valor_ipi': valor_ipi
    }

def calcular_cenario(margem_alvo, preco_manual, comissao, modo, canal, custo_base, impostos, peso, is_full, regime, logistica_pct, origem_produto, armaz=0):
    """
    Calcula o preço de venda ou margem considerando:
    - Regimes: Lucro Real, Simples Nacional, TTD 478, CPF.
    - Logística: % sobre o preço de venda.
    """
    v_margem = str_to_float(margem_alvo)
    v_preco_man = str_to_float(preco_manual)
    v_comissao = str_to_float(comissao)
    v_logistica = str_to_float(logistica_pct)
    v_peso = str_to_float(peso)
    v_armaz = str_to_float(armaz)
    
    # --- CONFIGURAÇÃO DE IMPOSTOS POR REGIME ---
    v_icms = 0.0
    v_difal = 0.0
    rate_pis = 0.0
    rate_cofins = 0.0
    pis_cofins_efetivo = 0.0
    
    # Tratamento de Origem (Para TTD) - Códigos de importados comuns: 1, 2, 3, 5, 8
    is_importado = str(origem_produto) in ['1', '2', '3', '5', '8']

    if regime == 'CPF':
        # CPF: Sem emissão de nota, sem impostos
        v_icms = 0.0
        v_difal = 0.0
        rate_pis = 0.0
        rate_cofins = 0.0
        imposto_total_pct = 0.0
        
    elif regime == 'Simples Nacional':
        # Simples: Alíquota única sobre faturamento (DAS)
        # Espera-se que venha em impostos['simples_aliquota'] ou usa o campo icms como 'total'
        try:
            # Tenta pegar alíquota específica do simples, se não tiver, usa o campo ICMS como sendo a alíquota total
            aliquota_simples = str_to_float(impostos.get('simples_aliquota', impostos.get('icms', 0)))
        except:
            aliquota_simples = 0.0
            
        imposto_total_pct = aliquota_simples / 100
        # Zeramos os individuais para o cálculo detalhado não duplicar
        v_icms = 0.0 
        rate_pis = 0.0
        rate_cofins = 0.0
        
    else:
        # Lucro Real ou TTD 478
        try:
            v_difal = str_to_float(impostos.get('difal', 0)) / 100
            
            if regime == 'TTD 478':
                # Lógica TTD: Trava ICMS
                if is_importado:
                    v_icms = 0.01 # 1% Importado
                else:
                    v_icms = 0.02 # 2% Nacional
            else:
                # Lucro Real Padrão
                v_icms = str_to_float(impostos.get('icms', 0)) / 100
                
        except:
            v_icms = 0.18 # Fallback
            v_difal = 0.0

        # PIS/COFINS (Lucro Real / TTD)
        rate_pis = 0.0165   # 1.65%
        rate_cofins = 0.0760 # 7.60%
        
        # Efetiva aproximada para o cálculo reverso (base excluindo ICMS)
        fator_base = 1 - v_icms
        pis_cofins_efetivo = fator_base * (rate_pis + rate_cofins)
        imposto_total_pct = v_icms + v_difal + pis_cofins_efetivo

    # --- CUSTOS FIXOS ---
    taxa_fixa = 0.0
    if "Shopee" in canal: taxa_fixa = 4.00
    
    custo_full = custo_base * (v_armaz/100) if is_full else 0.0
    custos_fixos_base = custo_base + custo_full + taxa_fixa

    preco = 0.0
    frete = 0.0
    val_comissao = 0.0
    val_logistica = 0.0

    # Percentual de custos variáveis (Comissão + Impostos + Logística + Armazenagem Venda)
    # Logística entra aqui pois é % sobre a venda
    perc_variaveis_base = imposto_total_pct + (v_comissao/100) + (v_logistica/100) + (v_armaz/100 if not is_full else 0.0)

    # =========================================================
    # CÁLCULO REVERSO (ALVO: PREÇO)
    # =========================================================
    if modo == "preco":
        preco = v_preco_man
        val_comissao = preco * (v_comissao/100)
        
        # Trava Shopee R$ 100
        if "Shopee" in canal and val_comissao > 100.00: val_comissao = 100.00
        
        if "Mercado Livre" in canal:
            taxa_fixa = obter_taxa_fixa_ml(preco)
            frete = obter_frete_ml_tabela(preco, v_peso)
            
    # =========================================================
    # CÁLCULO DIRETO (ALVO: MARGEM)
    # =========================================================
    else:
        divisor = 1 - (perc_variaveis_base + (v_margem/100))
        if divisor <= 0: divisor = 0.01 
        
        preco_preliminar = 0.0
        
        if "Mercado Livre" in canal:
            frete_est = obter_frete_ml_tabela(100.0, v_peso) 
            # Taxa Fixa ML (base aproximada)
            tx_base_ml = 0.0
            
            # Iteração 1: Estimativa
            p_teste = (custos_fixos_base + frete_est) / divisor
            
            # Refinamento Frete e Taxa Fixa
            frete_real = obter_frete_ml_tabela(p_teste, v_peso)
            tx_real = obter_taxa_fixa_ml(p_teste)
            
            p_final = (custos_fixos_base + frete_real + tx_real) / divisor
            
            # Verificação final de taxa fixa (pois o preço pode ter mudado de faixa)
            tx_final_check = obter_taxa_fixa_ml(p_final)
            if tx_final_check != tx_real:
                 p_final = (custos_fixos_base + frete_real + tx_final_check) / divisor
                 taxa_fixa += tx_final_check
            else:
                 taxa_fixa += tx_real
                 
            preco = p_final
            frete = frete_real
            
        else:
            preco = custos_fixos_base / divisor

        # --- VERIFICAÇÃO DO CAP DA SHOPEE ---
        comissao_preliminar = preco * (v_comissao/100)
        if "Shopee" in canal and comissao_preliminar > 100.00:
            # Recalcula tirando a comissão do divisor e somando o valor fixo de 100 nos custos
            perc_variaveis_novo = imposto_total_pct + (v_logistica/100) + (v_armaz/100 if not is_full else 0.0)
            divisor_novo = 1 - (perc_variaveis_novo + (v_margem/100))
            if divisor_novo <= 0: divisor_novo = 0.01
            
            custos_com_cap = custos_fixos_base + 100.00 + frete # Frete já definido acima
            preco = custos_com_cap / divisor_novo
            val_comissao = 100.00
        else:
            val_comissao = comissao_preliminar

    # 3. APURAÇÃO FINAL
    # Recalcula valores absolutos com o preço final definido
    val_comissao = min(preco * (v_comissao/100), 100.00) if "Shopee" in canal else preco * (v_comissao/100)
    val_logistica = preco * (v_logistica/100)
    
    val_imposto_total = 0.0
    val_icms = 0.0
    val_difal = 0.0
    val_pis = 0.0
    val_cofins = 0.0

    if regime == 'Simples Nacional':
         val_imposto_total = preco * imposto_total_pct
    elif regime == 'CPF':
         val_imposto_total = 0.0
    else:
        # Lucro Real / TTD
        val_icms = preco * v_icms
        val_difal = preco * v_difal
        
        # Base PIS/COFINS (Deduz ICMS)
        base_pis_cofins_venda = preco - val_icms
        if base_pis_cofins_venda < 0: base_pis_cofins_venda = 0
        
        val_pis = base_pis_cofins_venda * rate_pis
        val_cofins = base_pis_cofins_venda * rate_cofins
        val_imposto_total = val_icms + val_difal + val_pis + val_cofins

    val_armaz = preco * (v_armaz/100) if not is_full else custo_full 

    # Receita Líquida deduzindo TUDO
    receita_liq = preco - val_imposto_total - val_comissao - frete - taxa_fixa - custo_full - val_armaz - val_logistica
    lucro = receita_liq - custo_base
    margem_real = (lucro / preco * 100) if preco > 0 else 0.0

    return {
        "preco": round(preco, 2),
        "lucro": round(lucro, 2),
        "margem": round(margem_real, 2),
        "frete": round(frete, 2),
        "custo": round(custo_base, 2),
        "taxa_fixa": round(taxa_fixa, 2),
        "val_icms": round(val_icms, 2),
        "val_difal": round(val_difal, 2),
        "val_pis": round(val_pis, 2),       
        "val_cofins": round(val_cofins, 2), 
        "val_comissao": round(val_comissao, 2),
        "val_logistica": round(val_logistica, 2),
        "val_imposto_total": round(val_imposto_total, 2)
    }