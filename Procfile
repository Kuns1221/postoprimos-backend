import pandas as pd
import numpy as np
from rule_loader import identificar_posto, identificar_pelo_conteudo

# Mapeamento de nomes internos para nomes de exibição
NOMES_EXIBICAO = {
    "S500":   "Diesel S-500",
    "S10":    "Diesel S-10",
    "Adit":   "Gasolina Aditivada",
    "Comum":  "Gasolina Comum",
    "Etanol": "Etanol",
    "Podium":   "Gasolina Podium",
    "EtanolVP": "Etanol V-Power",
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

def _linha_tem_dados(df, linha, coluna_data, colunas_ignorar=None, ncols_max=None):
    ncols = min(ncols_max or 8, df.shape[1])
    ignorar = set([coluna_data] + (colunas_ignorar or []))
    for c in range(ncols):
        if c in ignorar:
            continue
        val = df.iloc[linha, c]
        if isinstance(val, (int, float)) and not pd.isna(val) and val > 0:
            return True
    return False

def ultima_linha_preenchida(df, coluna, linha_inicio, linha_fim, colunas_ignorar=None, ncols_max=None):
    ultima = linha_inicio
    for i in range(linha_inicio, min(linha_fim + 1, len(df))):
        if _linha_tem_dados(df, i, coluna, colunas_ignorar, ncols_max):
            ultima = i
    return ultima

def penultima_linha_preenchida(df, coluna, linha_inicio, linha_fim, colunas_ignorar=None):
    linhas = []
    for i in range(linha_inicio, min(linha_fim + 1, len(df))):
        if _linha_tem_dados(df, i, coluna, colunas_ignorar):
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
    ncols_max_est = est_cfg.get("ncols_max")
    linha_est = ultima_linha_preenchida(df, col_data, linha_inicio_est, linha_fim_est, ncols_max=ncols_max_est)

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
    leitura_vnd = vnd_cfg.get("leitura", "penultima_linha_preenchida")
    if leitura_vnd == "ultima_linha_preenchida":
        linha_vnd = ultima_linha_preenchida(df, col_data_v, linha_inicio_vnd, linha_fim_vnd)
    else:
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
    ncols_max_est = est_cfg.get("ncols_max")
    linha_est = ultima_linha_preenchida(df, col_data, linha_inicio_est, linha_fim_est, ncols_max=ncols_max_est)

    col_data_v = vnd_cfg.get("coluna_data", 0)
    linha_inicio_vnd = vnd_cfg["linha_inicio_dados"] - 1
    linha_fim_vnd = vnd_cfg["linha_fim_dados"] - 1
    leitura_vnd = vnd_cfg.get("leitura", "penultima_linha_preenchida")
    if leitura_vnd == "ultima_linha_preenchida":
        linha_vnd = ultima_linha_preenchida(df, col_data_v, linha_inicio_vnd, linha_fim_vnd)
    else:
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

    # Remove GNV e ordena
    combustiveis_resultado = [c for c in combustiveis_resultado if c["combustivel"] != "GNV"]
    ordem = ["S500", "S10", "Adit", "Podium", "Comum", "Etanol", "EtanolVP"]
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



def processar_4primos(df: pd.DataFrame, rule: dict) -> dict:
    """Processa planilha do 4primos — estoque em linha fixa, vendas por data."""
    estrutura = rule["estrutura_planilha"]
    est_cfg = estrutura["estoque"]
    vnd_cfg = estrutura["vendas"]

    linha_est = est_cfg["linha_valores"] - 1
    colunas_est = est_cfg["colunas"]

    # Estoque — S10 é soma de dois tanques
    estoques = {}
    for combustivel, col in colunas_est.items():
        if isinstance(col, list):
            estoques[combustivel] = round(sum(ler_valor(df, linha_est, c) for c in col), 2)
        else:
            estoques[combustivel] = ler_valor(df, linha_est, col)

    # Vendas — pega última linha com dados
    col_data = vnd_cfg.get("coluna_data", 0)
    linha_inicio = vnd_cfg["linha_inicio_dados"] - 1
    linha_fim = vnd_cfg["linha_fim_dados"] - 1
    linha_vnd = ultima_linha_preenchida(df, col_data, linha_inicio, linha_fim)

    colunas_vnd = vnd_cfg["colunas"]
    vendas = {}
    for combustivel, col in colunas_vnd.items():
        if isinstance(col, list):
            vendas[combustivel] = round(sum(ler_valor(df, linha_vnd, c) for c in col), 2)
        else:
            vendas[combustivel] = ler_valor(df, linha_vnd, col)

    return montar_resultado(rule, estoques, vendas)


def processar_trevo4(df: pd.DataFrame, rule: dict) -> dict:
    """Processa planilha Trevo4 — estoque e vendas por data, colunas com soma de tanques."""
    estrutura = rule["estrutura_planilha"]
    est_cfg = estrutura["estoque"]
    vnd_cfg = estrutura["vendas"]

    # Estoque — última linha preenchida
    col_data = est_cfg.get("coluna_data", 0)
    linha_inicio_est = est_cfg["linha_inicio_dados"] - 1
    linha_fim_est = est_cfg["linha_fim_dados"] - 1
    ncols_max_est = est_cfg.get("ncols_max")
    linha_est = ultima_linha_preenchida(df, col_data, linha_inicio_est, linha_fim_est, ncols_max=ncols_max_est)

    estoques = {}
    for combustivel, col in est_cfg["colunas"].items():
        if isinstance(col, list):
            estoques[combustivel] = round(sum(ler_valor(df, linha_est, c) for c in col), 2)
        else:
            estoques[combustivel] = ler_valor(df, linha_est, col)

    # Vendas — última linha preenchida
    col_data_v = vnd_cfg.get("coluna_data", 0)
    linha_inicio_vnd = vnd_cfg["linha_inicio_dados"] - 1
    linha_fim_vnd = vnd_cfg["linha_fim_dados"] - 1
    ignorar = vnd_cfg.get("colunas_ignorar") or (
        [vnd_cfg["coluna_total"]] if vnd_cfg.get("coluna_total") is not None else []
    )
    linha_vnd = ultima_linha_preenchida(df, col_data_v, linha_inicio_vnd, linha_fim_vnd, ignorar)

    vendas = {}
    for combustivel, col in vnd_cfg["colunas"].items():
        if isinstance(col, list):
            vendas[combustivel] = round(sum(ler_valor(df, linha_vnd, c) for c in col), 2)
        else:
            vendas[combustivel] = ler_valor(df, linha_vnd, col)

    return montar_resultado(rule, estoques, vendas)

# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

PROCESSADORES = {
    "6primos": processar_6primos,
    "gaslab":  processar_gaslab,
    "cafe":    processar_cafe,
    "5primos": processar_6primos,
    "4primos": processar_4primos,
    "trevo4":  processar_trevo4,
    "nego":    processar_trevo4,
    "mariuca":    processar_trevo4,
    "santamonica": processar_trevo4,
    "rkz":         processar_trevo4,
    "ppc":         processar_6primos,
    "florida":     processar_6primos,
    "stabarbara":  processar_6primos,
    "picheth":     processar_6primos,
}

def processar_planilha(caminho: str, nome_arquivo: str) -> dict:
    rule = identificar_posto(nome_arquivo, caminho)
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
