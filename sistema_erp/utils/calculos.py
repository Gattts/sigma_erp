TABELA_FRETE_ML = {
    # Valores aproximados (Jan/2024) - Mantenha atualizado
    "79-99": [(0.3, 20.90), (0.5, 21.90), (1.0, 22.90), (2.0, 23.90), (5.0, 28.90), (9.0, 43.90), (13.0, 68.90), (17.0, 83.90), (23.0, 98.90), (30.0, 113.90)],
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
    """
    Retorna o Custo Fixo do Mercado Livre baseado nas faixas de preço (Regras 2024/2025).
    """
    if preco >= 79.00: 
        return 0.00 # Frete Grátis (Vendedor paga envio, isento de taxa fixa)
    elif preco >= 50.00: 
        return 6.75 # Faixa R$ 50 - R$ 79
    elif preco >= 29.00: 
        return 6.50 # Faixa R$ 29 - R$ 50
    elif preco >= 12.50: 
        return 6.25 # Faixa R$ 12,50 - R$ 29
    else: 
        # REGRA ESPECIAL: Produtos < R$ 12,50 pagam metade do valor de venda
        return preco / 2.0 

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

def calcular_custo_aquisicao(pc, frete, ipi, outros, st_val, icms_frete, icms_prod, l_real, pis=0, cofins=0):
    v_pc, v_frete, v_ipi = str_to_float(pc), str_to_float(frete), str_to_float(ipi)
    v_outros, v_st = str_to_float(outros), str_to_float(st_val)
    v_icms_frete, v_icms_prod = str_to_float(icms_frete), str_to_float(icms_prod)
    v_pis_pct, v_cofins_pct = str_to_float(pis), str_to_float(cofins)

    valor_ipi = v_pc * (v_ipi / 100)
    preco_medio = v_pc + v_frete + valor_ipi + v_outros + v_st
    
    credito_icms = 0.0
    credito_pis_cofins = 0.0

    if l_real:
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

    pis_cofins_pct = 0.0925 
    imposto_total_pct = v_icms + v_difal + pis_cofins_pct
    
    # Taxas Fixas Iniciais (Placeholder, será calculado dinamicamente)
    taxa_fixa = 0.0
    if "Shopee" in canal:
        taxa_fixa = 4.00
    
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
        
        # Cap Shopee R$ 100
        if "Shopee" in canal and val_comissao > 100.00:
            val_comissao = 100.00
        
        if "Mercado Livre" in canal:
            taxa_fixa = obter_taxa_fixa_ml(preco)
            frete = obter_frete_ml_tabela(preco, v_peso)
            
    # =========================================================
    # CÁLCULO DIRETO (ALVO: MARGEM)
    # =========================================================
    else:
        # Perc Variaveis PADRÃO
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
                # Se for abaixo de 79, precisamos recalcular com a taxa fixa correta
                # Estimativa inicial com a maior taxa (6.75) para segurança
                p_estimado = (custos_fixos_base + 6.75) / divisor
                
                # Se cair muito (abaixo de 12.50), a taxa vira 50% do preço. 
                # Isso cria uma equação recursiva: Preço = (Custos + Preço/2) / Divisor
                # Simplificando: Preço - Preço/2/Divisor = Custos/Divisor
                # Mas para simplificar a lógica e não complicar a matemática:
                taxa_ml = obter_taxa_fixa_ml(p_estimado)
                
                # Refinamento para caso < 12.50
                if p_estimado < 12.50:
                    # Fórmula especial: Preço = (Custos + 0.5*Preço) / (1 - Variaveis - Margem)
                    # Preço * (1 - 0.5/Divisor_Inverso) ... melhor iterar simples:
                    taxa_ml = p_estimado * 0.5
                
                preco_preliminar = (custos_fixos_base + taxa_ml) / divisor
                
                # Recalcula taxa com o preço final obtido para garantir precisão
                taxa_fixa_final = obter_taxa_fixa_ml(preco_preliminar)
                if abs(taxa_fixa_final - taxa_ml) > 0.10:
                     # Se deu diferença grande, ajusta
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
            
            if "Mercado Livre" in canal:
                preco = (custos_com_cap + frete) / divisor_novo
            else:
                preco = custos_com_cap / divisor_novo
                
            val_comissao = 100.00
        else:
            preco = preco_preliminar
            val_comissao = comissao_preliminar

    # 3. Apuração Final
    val_icms = preco * v_icms
    val_difal = preco * v_difal
    val_pis_cofins = preco * pis_cofins_pct 
    val_imposto_total = val_icms + val_difal + val_pis_cofins
    
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
        "val_pis_cofins": round(val_pis_cofins, 2),
        "val_comissao": round(val_comissao, 2),
        "val_imposto_total": round(val_imposto_total, 2),
        "imposto_total_pct": round((val_imposto_total / preco * 100) if preco > 0 else 0, 2)
    }
