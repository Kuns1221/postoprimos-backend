import os
import json
import re

RULES_DIR = os.path.join(os.path.dirname(__file__), "rules")

def carregar_todas_rules() -> list:
    rules = []
    for arquivo in os.listdir(RULES_DIR):
        if arquivo.endswith(".json"):
            caminho = os.path.join(RULES_DIR, arquivo)
            with open(caminho, "r", encoding="utf-8") as f:
                rules.append(json.load(f))
    return rules

def normalizar(texto: str) -> str:
    texto = texto.upper().strip()
    texto = re.sub(r"[_\-\s]+", " ", texto)
    substituicoes = {
        "Á": "A", "À": "A", "Ã": "A", "Â": "A",
        "É": "E", "Ê": "E",
        "Í": "I",
        "Ó": "O", "Ô": "O", "Õ": "O",
        "Ú": "U", "Ü": "U",
        "Ç": "C",
    }
    for original, substituto in substituicoes.items():
        texto = texto.replace(original, substituto)
    return texto

def identificar_pelo_conteudo(caminho_arquivo: str, rules: list) -> dict | None:
    """Tenta identificar o posto lendo o conteúdo interno da planilha (célula A1)."""
    try:
        import pandas as pd
        ext = caminho_arquivo.lower()
        engine = 'xlrd' if ext.endswith('.xls') else 'openpyxl'
        df = pd.read_excel(caminho_arquivo, sheet_name=0, header=None, engine=engine, nrows=3)
        # Lê as primeiras células para identificar o posto
        textos = []
        for row in range(min(3, len(df))):
            for col in range(min(5, df.shape[1])):
                val = df.iloc[row, col]
                if val and str(val).strip() not in ('nan', ''):
                    textos.append(normalizar(str(val)))

        conteudo = ' '.join(textos)

        melhor_rule = None
        melhor_score = 0

        for rule in rules:
            palavras_chave = rule.get("identificacao_conteudo", [])
            if not palavras_chave:
                continue
            score = sum(1 for p in palavras_chave if normalizar(p) in conteudo)
            if score > melhor_score:
                melhor_score = score
                melhor_rule = rule

        if melhor_score >= 1:
            return melhor_rule
    except Exception:
        pass
    return None

def identificar_posto(nome_arquivo: str, caminho_arquivo: str = None) -> dict | None:
    nome_norm = normalizar(nome_arquivo.replace(".xlsx", "").replace(".xls", ""))
    rules = carregar_todas_rules()

    melhor_rule = None
    melhor_score = 0

    for rule in rules:
        arquivo_rule = normalizar(rule.get("arquivo", ""))
        palavras = arquivo_rule.split()
        score = sum(1 for palavra in palavras if palavra in nome_norm and len(palavra) > 2)
        if score > melhor_score:
            melhor_score = score
            melhor_rule = rule

    if melhor_score >= 1:
        return melhor_rule

    # Fallback: tenta identificar pelo conteúdo interno
    if caminho_arquivo:
        return identificar_pelo_conteudo(caminho_arquivo, rules)

    return None
