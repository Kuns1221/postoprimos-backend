import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone, timedelta

_db = None
BR_TZ = timezone(timedelta(hours=-3))

def get_db():
    global _db
    if _db is None:
        cred_json = os.environ.get("FIREBASE_CREDENTIALS")
        if not cred_json:
            raise RuntimeError("FIREBASE_CREDENTIALS não configurado no ambiente.")
        cred_dict = json.loads(cred_json)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(cred_dict))
        _db = firestore.client()
    return _db

def salvar_historico(dados: dict) -> str:
    db = get_db()
    agora_br = datetime.now(BR_TZ)
    dados["data_registro"] = datetime.now(timezone.utc).isoformat()
    dados["data_dia"] = agora_br.strftime("%Y-%m-%d")
    _, ref = db.collection("historico").add(dados)
    return ref.id

def buscar_historico(posto: str = None, limite: int = 100) -> list:
    db = get_db()
    col = db.collection("historico")
    if posto:
        col = col.where("posto", "==", posto)
    docs = col.order_by("data_registro", direction=firestore.Query.DESCENDING).limit(limite).stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]

def buscar_datas_disponiveis() -> list:
    db = get_db()
    docs = db.collection("historico").stream()
    datas = {}
    for d in docs:
        data = d.to_dict()
        dia = data.get("data_dia") or data.get("data_registro", "")[:10]
        if dia:
            datas[dia] = datas.get(dia, 0) + 1
    return [{"data": k, "total": v} for k, v in sorted(datas.items(), reverse=True)]

def buscar_por_data(data_dia: str) -> list:
    db = get_db()
    docs = db.collection("historico").stream()
    result = []
    for d in docs:
        data = d.to_dict()
        dia = data.get("data_dia") or data.get("data_registro", "")[:10]
        if dia == data_dia:
            result.append({"id": d.id, **data})
    return sorted(result, key=lambda x: x.get("descricao", ""))

def buscar_postos_disponiveis() -> list:
    db = get_db()
    docs = db.collection("historico").stream()
    postos = {}
    for d in docs:
        data = d.to_dict()
        posto = data.get("posto")
        if posto and posto not in postos:
            postos[posto] = data.get("descricao", posto)
    return [{"posto": k, "descricao": v} for k, v in sorted(postos.items())]
