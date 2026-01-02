TABELA_FRETE_ML = {
    # Valores de exemplo (Jan/2024) - É crucial manter isso atualizado via API ou tabela oficial
    "79-99": [(0.3, 20.90), (0.5, 21.90), (1.0, 22.90), (2.0, 23.90), (5.0, 28.90), (9.0, 43.90), (13.0, 68.90), (17.0, 83.90), (23.0, 98.90), (30.0, 113.90)],
    "100-119": [(0.3, 20.90), (0.5, 21.90), (1.0, 22.90), (2.0, 23.90), (5.0, 28.90), (9.0, 43.90), (13.0, 68.90), (17.0, 83.90), (23.0, 98.90), (30.0, 113.90)], # Muitas vezes a tabela unifica faixas acima de X valor
    "120-149": [(0.3, 20.90), (0.5, 21.90), (1.0, 22.90), (2.0, 23.90), (5.0, 28.90), (9.0, 43.90), (13.0, 68.90), (17.0, 83.90), (23.0, 98.90), (30.0, 113.90)],
    "150-199": [(0.3, 20.90), (0.5, 21.90), (1.0, 22.90), (2.0, 23.90), (5.0, 28.90), (9.0, 43.90), (13.0, 68.90), (17.0, 83.90), (23.0, 98.90), (30.0, 113.90)],
    "200+":    [(0.3, 20.90), (0.5, 21.90), (1.0, 22.90), (2.0, 23.90), (5.0, 28.90), (9.0, 43.90), (13.0, 68.90), (17.0, 83.90), (23.0, 98.90), (30.0, 113.90)]
}
# IMPORTANTE: A tabela acima é ilustrativa para estrutura. Substitua pelos valores reais vigentes do ML.

def str_to_float(valor_str):
    if not valor_str: return 0.0
    if isinstance(valor_str, (float, int)): return float(valor_str)
    try:
        return float(str(valor_str).replace(',', '.').strip())
    except:
        return 0.0

def obter_taxa_fixa_ml(preco):
    # ML cobra taxa fixa apenas abaixo de R$ 79
    if preco >= 79.00: return 0.00
    # Abaixo de 79, a taxa fixa varia (hoje em dia costuma ser fixa em R$ 6.00 para Clássico/Premium em certas categorias, mas vamos manter a lógica escalonada se for sua regra específica)
    elif preco >= 50.00: return 6.00 # Ajustado valor comum
    elif preco >= 29.00: return 6.00
    elif preco > 10.00: return 6.00
    else: return 0.00 # Produtos muito baratos as vezes tem regras diferentes, ou taxa fixa igual

def obter_frete_ml_tabela(preco, peso):
    if preco < 79.00: return 0.00
    
    # Simplificação: ML geralmente usa uma tabela única para Frete Grátis acima de 79, variando apenas por peso e reputação.
    # Vamos assumir a faixa "200+" como padrão se não houver distinção.
    # Se houver distinção real no seu contrato, mantenha a lógica de faixas.
    faixa = "200+" 
    
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
    
    # Custo Base (O que sai do caixa)
    preco_medio = v_pc + v_frete + valor_ipi + v_outros + v_st
    
    credito_icms = 0.0
    credito_pis_cofins = 0.0

    if l_real:
        # Crédito de ICMS
        c_frete = v_frete * (v_icms_frete / 100)
        c_prod = v_pc * (v_icms_prod / 100)
        credito_icms = c_frete + c_prod
        
        # CORREÇÃO: Base de PIS/COFINS na compra (Sem ICMS)
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

    # 1. Definição de Variáveis Percentuais
    pis_cofins_pct = 0.0925
    
    # CORREÇÃO: A alíquota efetiva sobre o preço cheio muda porque a base diminui.
    # Base PIS/COFINS = Preço * (1 - ICMS)
    # Imposto Efetivo = Preço * (1 - ICMS) * 9.25%
    # Aproximação para cálculo iterativo:
    fator_pis_cofins_efetivo = (1 - v_icms) * pis_cofins_pct
    
    imposto_total_pct = v_icms + v_difal + fator_pis_cofins_efetivo
    
    perc_variaveis = imposto_total_pct + (v_comissao/100) + (v_armaz/100 if not is_full else 0.0)
    
    # 2. Definição de Custos Fixos
    taxa_fixa = 4.00 if "Shopee" in canal else 0.0
    custo_full = custo_base * (v_armaz/100) if is_full else 0.0
    
    preco = 0.0
    frete = 0.0

    if modo == "preco":
        preco = v_preco_man
        if "Mercado Livre" in canal:
            taxa_fixa += obter_taxa_fixa_ml(preco)
            frete = obter_frete_ml_tabela(preco, v_peso)
    else:
        divisor = 1 - (perc_variaveis + (v_margem/100))
        if divisor <= 0: divisor = 0.01 
        
        custos_fixos = custo_base + custo_full + taxa_fixa
        
        if "Mercado Livre" in canal:
            frete_est = obter_frete_ml_tabela(100.0, v_peso)
            p_teste = (custos_fixos + frete_est) / divisor
            
            frete = obter_frete_ml_tabela(p_teste, v_peso)
            p_final = (custos_fixos + frete) / divisor
            
            if p_final >= 79.00:
                preco = p_final
            else:
                taxa_ml = obter_taxa_fixa_ml((custos_fixos + 6.00)/divisor)
                preco = (custos_fixos + taxa_ml) / divisor
                taxa_fixa += taxa_ml
                frete = 0.0
        else:
            preco = custos_fixos / divisor

    # 3. Apuração Final (CORRIGIDA)
    val_icms = preco * v_icms
    val_difal = preco * v_difal
    
    # Base de cálculo PIS/COFINS na venda exclui ICMS
    base_pis_cofins_venda = preco - val_icms
    if base_pis_cofins_venda < 0: base_pis_cofins_venda = 0
    
    val_pis_cofins = base_pis_cofins_venda * pis_cofins_pct
    
    val_imposto_total = val_icms + val_difal + val_pis_cofins
    
    val_comissao = preco * (v_comissao/100)
    val_armaz = preco * (v_armaz/100) if not is_full else custo_full 

    receita_liq = preco - val_imposto_total - val_comissao - frete - taxa_fixa - custo_full - val_armaz
    
    lucro = receita_liq - custo_base
    margem_real = (lucro / preco * 100) if preco > 0 else 0.0

    return {
        "preco": preco,
        "lucro": lucro,
        "margem": margem_real,
        "frete": frete,
        "custo": custo_base,
        "taxa_fixa": taxa_fixa,
        "val_icms": val_icms,
        "val_difal": val_difal,
        "val_pis_cofins": val_pis_cofins,
        "val_comissao": val_comissao,
        "val_imposto_total": val_imposto_total,
        "imposto_total_pct": (val_imposto_total / preco * 100) if preco > 0 else 0
    }