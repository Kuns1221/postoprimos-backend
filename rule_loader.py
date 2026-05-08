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
    """Remove acentos, espaços extras, underscores e converte para maiúsculo."""
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

def identificar_posto(nome_arquivo: str) -> dict | None:
    """
    Tenta identificar o posto pelo nome do arquivo.
    Compara o nome do arquivo com o campo 'arquivo' de cada rule.
    """
    nome_norm = normalizar(nome_arquivo.replace(".xlsx", "").replace(".xls", ""))
    rules = carregar_todas_rules()

    melhor_rule = None
    melhor_score = 0

    for rule in rules:
        arquivo_rule = normalizar(rule.get("arquivo", ""))
        
        # Verifica se há palavras-chave do arquivo da rule no nome do arquivo enviado
        palavras = arquivo_rule.split()
        score = sum(1 for palavra in palavras if palavra in nome_norm and len(palavra) > 2)

        if score > melhor_score:
            melhor_score = score
            melhor_rule = rule

    if melhor_score >= 1:
        return melhor_rule

    return None
