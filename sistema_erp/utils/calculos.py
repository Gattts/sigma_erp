TABELA_FRETE_ML = {
    "79-99": [(0.3, 11.97), (0.5, 12.87), (1.0, 13.47), (2.0, 14.07),(3.0, 14.97), (4.0, 16.17), (5.0, 17.07), (9.0, 26.67), (13.0, 39.57), (17.0, 44.07), (23.0, 51.57), (30.0, 59.37)],
    "100-119": [(0.3, 20.90), (0.5, 21.90), (1.0, 22.90), (2.0, 23.90), (5.0, 28.90), (9.0, 43.90), (13.0, 68.90), (17.0, 83.90), (23.0, 98.90), (30.0, 113.90)], 
    "120-149": [(0.3, 20.90), (0.5, 21.90), (1.0, 22.90), (2.0, 23.90), (5.0, 28.90), (9.0, 43.90), (13.0, 68.90), (17.0, 83.90), (23.0, 98.90), (30.0, 113.90)],
    "150-199": [(0.3, 20.90), (0.5, 21.90), (1.0, 22.90), (2.0, 23.90), (5.0, 28.90), (9.0, 43.90), (13.0, 68.90), (17.0, 83.90), (23.0, 98.90), (30.0, 113.90)],
    "200+":    [(0.3, 20.90), (0.5, 21.90), (1.0, 22.90), (2.0, 23.90), (5.0, 28.90), (9.0, 43.90), (13.0, 68.90), (17.0, 83.90), (23.0, 98.90), (30.0, 113.90)]
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

# --- ATUALIZAÇÃO DA LÓGICA DE CUSTO ---
def calcular_custo_aquisicao(pc, frete, ipi, outros, st_val, icms_frete, icms_prod, l_real, pis=0, cofins=0):
    # 1. Conversão de valores
    v_pc = str_to_float(pc)
    v_frete = str_to_float(frete)
    v_ipi_pct = str_to_float(ipi)
    v_outros = str_to_float(outros)
    v_st = str_to_float(st_val)
    
    # Percentuais
    v_icms_prod_pct = str_to_float(icms_prod)
    v_pis_pct = str_to_float(pis)
    v_cofins_pct = str_to_float(cofins)

    # 2. Valores Monetários
    valor_ipi = v_pc * (v_ipi_pct / 100)
    
    # Passo 1: Preço Médio (Total da Nota / Desembolso)
    # Nota: O Excel considera Produto + Frete + IPI (Outros/ST entram se existirem)
    preco_medio = v_pc + v_frete + valor_ipi + v_outros + v_st

    # 3. Cálculo dos Créditos (Lucro Real)
    total_creditos = 0.0
    val_icms_prod = 0.0
    val_pis = 0.0
    val_cofins = 0.0

    if l_real:
        # A. Crédito de ICMS
        val_icms_prod = v_pc * (v_icms_prod_pct / 100)
        
        # B. Crédito de PIS/COFINS (Base = (Produto + Frete) - ICMS)
        # Regra da "Tese do Século" aplicada no Excel enviado
        base_pis_cofins = (v_pc + v_frete) - val_icms_prod
        if base_pis_cofins < 0: base_pis_cofins = 0
        
        val_pis = base_pis_cofins * (v_pis_pct / 100)
        val_cofins = base_pis_cofins * (v_cofins_pct / 100)

        # C. Soma dos Créditos (ICMS + PIS + COFINS + IPI)
        total_creditos = val_icms_prod + val_pis + val_cofins + valor_ipi
        
        # Passo 2: Custo Final = Preço Médio - Créditos
        custo_final = preco_medio - total_creditos
    else:
        # Se não for Lucro Real, o custo é o desembolso total
        custo_final = preco_medio
        total_creditos = 0.0

    return {
        'custo_final': round(custo_final, 4),
        'creditos': round(total_creditos, 2),
        'icms_rec': round(val_icms_prod, 2),
        'pis_cof_rec': round(val_pis + val_cofins, 2), # Soma para exibir no resumo
        'val_pis': round(val_pis, 2),
        'val_cofins': round(val_cofins, 2),
        'valor_ipi': round(valor_ipi, 2),
        'preco_medio': round(preco_medio, 2)
    }
def calcular_cenario(margem_alvo, preco_manual, comissao, modo, canal, custo_base, impostos, peso, is_full, armaz=0):
    v_margem = str_to_float(margem_alvo)
    v_preco_man = str_to_float(preco_manual)
    v_comissao = str_to_float(comissao)
    
    try:
        v_icms = str_to_float(impostos.get('icms', 0)) / 100
        v_difal = str_to_float(impostos.get('difal', 0)) / 100
    except:
        v_icms = 0.18
        v_difal = 0.0

    v_peso = str_to_float(peso)
    v_armaz = str_to_float(armaz)

    # --- DEFINIÇÃO DE ALIQUOTAS PIS/COFINS (Lucro Real) ---
    rate_pis = 0.0165   # 1.65%
    rate_cofins = 0.0760 # 7.60%
    
    # Efetiva aproximada para o cálculo reverso
    fator_base = 1 - v_icms
    pis_cofins_efetivo = fator_base * (rate_pis + rate_cofins)
    imposto_total_pct = v_icms + v_difal + pis_cofins_efetivo
    
    # Taxas Fixas Iniciais
    taxa_fixa = 0.0
    if "Shopee" in canal: taxa_fixa = 4.00
    
    custo_full = custo_base * (v_armaz/100) if is_full else 0.0
    custos_fixos_base = custo_base + custo_full + taxa_fixa

    preco = 0.0
    frete = 0.0
    val_comissao = 0.0

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
        perc_variaveis = imposto_total_pct + (v_comissao/100) + (v_armaz/100 if not is_full else 0.0)
        divisor = 1 - (perc_variaveis + (v_margem/100))
        if divisor <= 0: divisor = 0.01 
        
        preco_preliminar = 0.0
        
        if "Mercado Livre" in canal:
            frete_est = obter_frete_ml_tabela(100.0, v_peso) 
            p_teste = (custos_fixos_base + frete_est) / divisor
            frete_real = obter_frete_ml_tabela(p_teste, v_peso)
            p_final = (custos_fixos_base + frete_real) / divisor
            
            if p_final >= 79.00:
                preco_preliminar = p_final
                frete = frete_real
            else:
                p_estimado = (custos_fixos_base + 6.75) / divisor
                taxa_ml = obter_taxa_fixa_ml(p_estimado)
                if p_estimado < 12.50: taxa_ml = p_estimado * 0.5
                
                preco_preliminar = (custos_fixos_base + taxa_ml) / divisor
                taxa_fixa_final = obter_taxa_fixa_ml(preco_preliminar)
                if abs(taxa_fixa_final - taxa_ml) > 0.10:
                     preco_preliminar = (custos_fixos_base + taxa_fixa_final) / divisor
                     taxa_fixa += taxa_fixa_final
                else:
                     taxa_fixa += taxa_ml
                frete = 0.0 
        else:
            preco_preliminar = custos_fixos_base / divisor

        # --- VERIFICAÇÃO DO CAP DA SHOPEE ---
        comissao_preliminar = preco_preliminar * (v_comissao/100)
        if "Shopee" in canal and comissao_preliminar > 100.00:
            perc_variaveis_novo = imposto_total_pct + (v_armaz/100 if not is_full else 0.0)
            divisor_novo = 1 - (perc_variaveis_novo + (v_margem/100))
            if divisor_novo <= 0: divisor_novo = 0.01
            custos_com_cap = custos_fixos_base + 100.00
            if "Mercado Livre" in canal: preco = (custos_com_cap + frete) / divisor_novo
            else: preco = custos_com_cap / divisor_novo
            val_comissao = 100.00
        else:
            preco = preco_preliminar
            val_comissao = comissao_preliminar

    # 3. APURAÇÃO FINAL
    val_icms = preco * v_icms
    val_difal = preco * v_difal
    
    # AQUI ESTÁ A MÁGICA: Base = Preço - ICMS
    base_pis_cofins_venda = preco - val_icms
    if base_pis_cofins_venda < 0: base_pis_cofins_venda = 0
    
    val_pis = base_pis_cofins_venda * rate_pis
    val_cofins = base_pis_cofins_venda * rate_cofins
    
    val_imposto_total = val_icms + val_difal + val_pis + val_cofins
    val_armaz = preco * (v_armaz/100) if not is_full else custo_full 

    receita_liq = preco - val_imposto_total - val_comissao - frete - taxa_fixa - custo_full - val_armaz
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
        "val_imposto_total": round(val_imposto_total, 2)
    }