import pandas as pd
import numpy as np
from rule_loader import identificar_posto

# Mapeamento de nomes internos para nomes de exibição
NOMES_EXIBICAO = {
    "S500":   "Diesel S-500",
    "S10":    "Diesel S-10",
    "Adit":   "Gasolina Aditivada",
    "Comum":  "Gasolina Comum",
    "Etanol": "Etanol",
    "GNV":    "GNV",
}

def ler_valor(df: pd.DataFrame, linha: int, coluna: int) -> float:
    """Lê um valor numérico do DataFrame com segurança."""
    try:
        val = df.iloc[linha, coluna]
        if pd.isna(val):
            return 0.0
        return float(str(val).replace(",", ".").strip())
    except (ValueError, IndexError):
        return 0.0

def ultima_linha_preenchida(df: pd.DataFrame, coluna: int, linha_inicio: int, linha_fim: int) -> int:
    """Retorna o índice da última linha preenchida em uma coluna dentro de um intervalo."""
    ultima = linha_inicio
    for i in range(linha_inicio, min(linha_fim + 1, len(df))):
        val = df.iloc[i, coluna]
        if not pd.isna(val) and str(val).strip() not in ("", "0"):
            ultima = i
    return ultima

def penultima_linha_preenchida(df: pd.DataFrame, coluna: int, linha_inicio: int, linha_fim: int) -> int:
    """Retorna o índice da penúltima linha preenchida em uma coluna dentro de um intervalo."""
    linhas = []
    for i in range(linha_inicio, min(linha_fim + 1, len(df))):
        val = df.iloc[i, coluna]
        if not pd.isna(val) and str(val).strip() not in ("", "0"):
            linhas.append(i)
    if len(linhas) >= 2:
        return linhas[-2]
    if len(linhas) == 1:
        return linhas[0]
    return linha_inicio

# ─────────────────────────────────────────────
# PROCESSADORES POR TIPO DE RULE
# ─────────────────────────────────────────────

def processar_6primos(df: pd.DataFrame, rule: dict) -> dict:
    """Processa planilha do posto 6primos (estrutura com linha fixa de estoque e vendas)."""
    estrutura = rule["estrutura_planilha"]
    tanques = rule["tanques"]
    agrupamento = rule["agrupamento_estoque"]
    mapeamento_vendas = rule["mapeamento_vendas"]

    # Lê estoque por tanque
    linha_estoque = estrutura["estoque"]["linha_valores"] - 1  # 0-indexed
    estoques_tanque = {}
    for tanque in tanques:
        val = ler_valor(df, linha_estoque, tanque["coluna"])
        estoques_tanque[tanque["tanque"]] = val

    # Agrupa estoques
    estoques = {}
    for combustivel, config in agrupamento.items():
        total = sum(estoques_tanque.get(t, 0) for t in config["tanques"])
        estoques[combustivel] = round(total, 2)

    # Lê vendas
    linha_cabecalho_vendas = estrutura["vendas"]["linha_cabecalho"] - 1
    linha_valores_vendas = estrutura["vendas"]["linha_valores"] - 1

    vendas = {}
    for col in range(len(df.columns)):
        try:
            cabecalho = str(df.iloc[linha_cabecalho_vendas, col]).strip().upper()
        except IndexError:
            continue

        for nome_original, combustivel in mapeamento_vendas.items():
            if nome_original.upper() in cabecalho or cabecalho in nome_original.upper():
                val = ler_valor(df, linha_valores_vendas, col)
                vendas[combustivel] = vendas.get(combustivel, 0) + val
                break

    return montar_resultado(rule, estoques, vendas)


def processar_gaslab(df: pd.DataFrame, rule: dict) -> dict:
    """Processa planilha do posto Gaslab (leitura por última/penúltima linha preenchida)."""
    estrutura = rule["estrutura_planilha"]
    tanques = rule["tanques"]
    agrupamento = rule["agrupamento_estoque"]
    mapeamento_vendas = rule["mapeamento_vendas"]

    est_cfg = estrutura["estoque"]
    vnd_cfg = estrutura["vendas"]

    col_data = est_cfg.get("coluna_data", 0)
    linha_inicio_est = est_cfg["linha_inicio_dados"] - 1
    linha_fim_est = est_cfg["linha_fim_dados"] - 1
    linha_est = ultima_linha_preenchida(df, col_data, linha_inicio_est, linha_fim_est)

    estoques_tanque = {}
    for tanque in tanques:
        val = ler_valor(df, linha_est, tanque["coluna_estoque"])
        estoques_tanque[tanque["tanque"]] = val

    estoques = {}
    for combustivel, config in agrupamento.items():
        total = sum(estoques_tanque.get(t, 0) for t in config["tanques"])
        estoques[combustivel] = round(total, 2)

    col_data_v = vnd_cfg.get("coluna_data", 0)
    linha_inicio_vnd = vnd_cfg["linha_inicio_dados"] - 1
    linha_fim_vnd = vnd_cfg["linha_fim_dados"] - 1
    linha_vnd = penultima_linha_preenchida(df, col_data_v, linha_inicio_vnd, linha_fim_vnd)

    vendas = {}
    for chave_coluna, combustivel in mapeamento_vendas.items():
        try:
            idx = int(chave_coluna.replace("coluna_", ""))
        except ValueError:
            continue
        val = ler_valor(df, linha_vnd, idx)
        vendas[combustivel] = vendas.get(combustivel, 0) + val

    return montar_resultado(rule, estoques, vendas)


def processar_cafe(df: pd.DataFrame, rule: dict) -> dict:
    """Processa planilha do posto Trevo Café (estrutura com combustiveis unificados)."""
    estrutura = rule["estrutura_planilha"]
    combustiveis = rule["combustiveis"]

    est_cfg = estrutura["estoque"]
    vnd_cfg = estrutura["vendas"]

    col_data = est_cfg.get("coluna_data", 0)
    linha_inicio_est = est_cfg["linha_inicio_dados"] - 1
    linha_fim_est = est_cfg["linha_fim_dados"] - 1
    linha_est = ultima_linha_preenchida(df, col_data, linha_inicio_est, linha_fim_est)

    col_data_v = vnd_cfg.get("coluna_data", 0)
    linha_inicio_vnd = vnd_cfg["linha_inicio_dados"] - 1
    linha_fim_vnd = vnd_cfg["linha_fim_dados"] - 1
    linha_vnd = penultima_linha_preenchida(df, col_data_v, linha_inicio_vnd, linha_fim_vnd)

    estoques = {}
    vendas = {}

    for comb in combustiveis:
        nome = comb["combustivel"]

        # Estoque
        total_estoque = 0
        for col in comb.get("colunas_estoque", []):
            total_estoque += ler_valor(df, linha_est, col)
        estoques[nome] = round(total_estoque, 2)

        # Venda
        col_venda = comb.get("coluna_venda")
        if col_venda is not None:
            vendas[nome] = ler_valor(df, linha_vnd, col_venda)

    return montar_resultado(rule, estoques, vendas)


# ─────────────────────────────────────────────
# MONTAGEM DO RESULTADO FINAL
# ─────────────────────────────────────────────

def montar_resultado(rule: dict, estoques: dict, vendas: dict) -> dict:
    """Monta o objeto de resposta padronizado."""
    combustiveis_resultado = []

    todos = set(list(estoques.keys()) + list(vendas.keys()))
    for nome in todos:
        estoque = estoques.get(nome, 0)
        venda = vendas.get(nome, 0)
        combustiveis_resultado.append({
            "combustivel": nome,
            "nome_exibicao": NOMES_EXIBICAO.get(nome, nome),
            "estoque": estoque,
            "venda": venda,
            "enviado": 0,
            "resultado": round(estoque - venda, 2),
        })

    # Ordena por nome
    ordem = ["S500", "S10", "Adit", "Comum", "Etanol", "GNV"]
    combustiveis_resultado.sort(key=lambda x: ordem.index(x["combustivel"]) if x["combustivel"] in ordem else 99)

    total_estoque = round(sum(c["estoque"] for c in combustiveis_resultado), 2)
    total_venda = round(sum(c["venda"] for c in combustiveis_resultado), 2)

    return {
        "posto": rule.get("posto"),
        "descricao": rule.get("descricao"),
        "combustiveis": combustiveis_resultado,
        "total_estoque": total_estoque,
        "total_venda": total_venda,
    }


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

PROCESSADORES = {
    "6primos": processar_6primos,
    "gaslab":  processar_gaslab,
    "cafe":    processar_cafe,
}

def processar_planilha(caminho: str, nome_arquivo: str) -> dict:
    rule = identificar_posto(nome_arquivo)
    if not rule:
        return {"erro": f"Nenhuma RULE encontrada para o arquivo '{nome_arquivo}'. Verifique o nome ou cadastre uma nova RULE."}

    posto = rule.get("posto")
    processador = PROCESSADORES.get(posto)
    if not processador:
        return {"erro": f"Processador não implementado para o posto '{posto}'."}

    try:
        aba = rule.get("estrutura_planilha", {}).get("aba", 0)
        df = pd.read_excel(caminho, sheet_name=aba, header=None)
        return processador(df, rule)
    except Exception as e:
        return {"erro": f"Erro ao processar planilha: {str(e)}"}
