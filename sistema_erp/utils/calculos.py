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
    # ML cobra taxa fixa (ex: R$ 6.00) apenas abaixo de R$ 79
    if preco >= 79.00: return 0.00
    elif preco >= 6.00: return 6.00 # Mínimo para venda geralmente
    else: return 0.00

def obter_frete_ml_tabela(preco, peso):
    if preco < 79.00: return 0.00
    
    # Lógica simplificada de faixas
    faixa = "200+" 
    if preco < 100: faixa = "79-99"
    elif preco < 120: faixa = "100-119"
    elif preco < 150: faixa = "120-149"
    elif preco < 200: faixa = "150-199"

    lista = TABELA_FRETE_ML.get(faixa, TABELA_FRETE_ML["200+"])
    
    for limite, valor in lista:
        if peso <= limite: return valor
    
    return lista[-1][1] # Retorna o maior valor se passar do peso máximo tabelado

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
        
        # Base de PIS/COFINS na compra (Sem ICMS na base se for decisão judicial, mas padrão contábil varia)
        # Vamos usar a regra padrão simplificada:
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
    pis_cofins_pct = 0.0925 # 9.25% padrão Lucro Real
    
    # Ajuste fino: Pis/Cofins incide sobre o total, mas exclui ICMS da base em algumas regras
    # Vamos manter simplificado sobre o total para margem de segurança
    imposto_total_pct = v_icms + v_difal + pis_cofins_pct
    
    # Soma todas as porcentagens que mordem o preço de venda
    perc_variaveis = imposto_total_pct + (v_comissao/100) + (v_armaz/100 if not is_full else 0.0)
    
    # 2. Definição de Custos Fixos INICIAIS
    custo_full = custo_base * (v_armaz/100) if is_full else 0.0
    
    # Lógica de Taxa Fixa por Canal
    taxa_fixa = 0.0
    
    if "Shopee" in canal:
        taxa_fixa = 4.00 # Regra Nova: Fixa em R$ 4,00
    elif "Mercado Livre" in canal:
        taxa_fixa = 0.0 # Será calculada dinamicamente baseada no preço final (< 79)
    else:
        taxa_fixa = 0.0 # Site próprio geralmente não tem taxa fixa por pedido (ou é baixa)

    preco = 0.0
    frete = 0.0

    # --- CÁLCULO REVERSO (ALVO: PREÇO) ---
    if modo == "preco":
        preco = v_preco_man
        
        # Se for ML, calcula as taxas baseadas nesse preço manual
        if "Mercado Livre" in canal:
            taxa_fixa = obter_taxa_fixa_ml(preco)
            frete = obter_frete_ml_tabela(preco, v_peso)
            
    # --- CÁLCULO DIRETO (ALVO: MARGEM) ---
    else:
        divisor = 1 - (perc_variaveis + (v_margem/100))
        if divisor <= 0: divisor = 0.01 
        
        custos_fixos_base = custo_base + custo_full + taxa_fixa
        
        if "Mercado Livre" in canal:
            # ML é complexo pois Frete e Taxa Fixa dependem do Preço Final (problema do ovo e galinha)
            # Tentativa 1: Assume que vai passar de 79 (com Frete Grátis)
            frete_est = obter_frete_ml_tabela(100.0, v_peso) 
            p_teste = (custos_fixos_base + frete_est) / divisor
            
            # Recalcula com o preço teste
            frete_real = obter_frete_ml_tabela(p_teste, v_peso)
            p_final = (custos_fixos_base + frete_real) / divisor
            
            if p_final >= 79.00:
                preco = p_final
                frete = frete_real
                # Taxa fixa se mantém 0
            else:
                # Se caiu abaixo de 79, remove frete grátis e adiciona taxa fixa de 6 reais
                taxa_ml = 6.00
                preco = (custos_fixos_base + taxa_ml) / divisor
                taxa_fixa += taxa_ml
                frete = 0.0 # Abaixo de 79 quem paga frete é o comprador
        else:
            # Shopee e outros canais simples
            preco = custos_fixos_base / divisor

    # 3. Apuração Final
    val_icms = preco * v_icms
    val_difal = preco * v_difal
    val_pis_cofins = preco * pis_cofins_pct # Base cheia para segurança
    
    val_imposto_total = val_icms + val_difal + val_pis_cofins
    
    val_comissao = preco * (v_comissao/100)
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
