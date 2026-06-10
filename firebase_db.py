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

def _extrair_data_dia(data: dict) -> str:
    dia = data.get("data_dia")
    if dia:
        return dia
    reg = data.get("data_registro", "")
    if not reg:
        return ""
    try:
        dt = datetime.fromisoformat(reg)
        return dt.astimezone(BR_TZ).strftime("%Y-%m-%d")
    except Exception:
        return reg[:10]

def _batch_delete(db, refs: list) -> int:
    if not refs:
        return 0
    batch = db.batch()
    count = 0
    for i, ref in enumerate(refs):
        batch.delete(ref)
        count += 1
        if (i + 1) % 500 == 0:
            batch.commit()
            batch = db.batch()
    batch.commit()
    return count

# ── Metadata / Resumo ─────────────────────────────────────────────────────────
# O documento metadata/resumo guarda um índice leve de datas e postos.
# Isso elimina scans completos da coleção em buscar_datas_disponiveis e
# buscar_postos_disponiveis — de 50k leituras para 1 leitura por chamada.

def _resumo_ref(db):
    return db.collection("metadata").document("resumo")

def _resumo_add(db, data_dia: str, posto: str, descricao: str):
    """Registra um posto numa data no resumo. Cria o documento se não existir."""
    ref = _resumo_ref(db)
    try:
        ref.update({
            f"datas.{data_dia}": firestore.ArrayUnion([posto]),
            f"postos.{posto}": descricao,
        })
    except Exception:
        ref.set({
            "datas": {data_dia: [posto]},
            "postos": {posto: descricao},
        }, merge=True)

def _resumo_remove_data(db, data_dia: str):
    """Remove uma data do resumo ao deletar todos os registros dela."""
    ref = _resumo_ref(db)
    try:
        ref.update({f"datas.{data_dia}": firestore.DELETE_FIELD})
    except Exception:
        pass

def reconstruir_resumo() -> dict:
    """
    Reconstrói o documento metadata/resumo varrendo a coleção historico.
    Deve ser chamado uma única vez via POST /admin/reconstruir-resumo
    para popular o índice a partir dos dados existentes.
    """
    db = get_db()
    docs = db.collection("historico").select(
        ["data_dia", "posto", "descricao", "data_registro"]
    ).stream()

    datas: dict[str, set] = {}
    postos: dict[str, str] = {}

    for d in docs:
        data = d.to_dict()
        dia = _extrair_data_dia(data)
        posto = data.get("posto")
        descricao = data.get("descricao", posto or "")
        if not dia or not posto:
            continue
        datas.setdefault(dia, set()).add(posto)
        postos.setdefault(posto, descricao)

    resumo = {
        "datas":  {k: list(v) for k, v in datas.items()},
        "postos": postos,
    }
    _resumo_ref(db).set(resumo)
    return {"datas": len(datas), "postos": len(postos)}

# ── CRUD principal ────────────────────────────────────────────────────────────

def salvar_historico(dados: dict) -> str:
    db = get_db()
    data_planilha = dados.pop("data_planilha", None)
    dados["data_registro"] = datetime.now(timezone.utc).isoformat()
    dados["data_dia"] = data_planilha if data_planilha else datetime.now(BR_TZ).strftime("%Y-%m-%d")

    _, ref = db.collection("historico").add(dados)

    # Atualiza o resumo sem bloquear o retorno em caso de falha
    try:
        _resumo_add(db, dados["data_dia"], dados.get("posto", ""), dados.get("descricao", ""))
    except Exception:
        pass

    return ref.id

def buscar_historico(posto: str = None, limite: int = 100) -> list:
    db = get_db()
    col = db.collection("historico")
    if posto:
        col = col.where("posto", "==", posto)
    docs = col.order_by("data_registro", direction=firestore.Query.DESCENDING).limit(limite).stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]

def buscar_datas_disponiveis() -> list:
    """1 leitura Firestore — usa o documento de resumo."""
    db = get_db()
    doc = _resumo_ref(db).get()
    if not doc.exists:
        return []
    datas = doc.to_dict().get("datas", {})
    result = [
        {"data": k, "total": len(v) if isinstance(v, list) else int(v)}
        for k, v in datas.items()
    ]
    return sorted(result, key=lambda x: x["data"], reverse=True)

def buscar_por_data(data_dia: str) -> list:
    """Filtra no Firestore — lê apenas documentos da data solicitada."""
    db = get_db()
    docs = db.collection("historico").where("data_dia", "==", data_dia).stream()
    por_posto: dict = {}
    for d in docs:
        data = d.to_dict()
        posto = data.get("posto")
        if posto is None:
            continue
        existente = por_posto.get(posto)
        if existente is None or data.get("data_registro", "") > existente.get("data_registro", ""):
            por_posto[posto] = {"id": d.id, **data}
    return sorted(por_posto.values(), key=lambda x: x.get("descricao", ""))

def deletar_por_id(doc_id: str) -> bool:
    db = get_db()
    db.collection("historico").document(doc_id).delete()
    return True

def deletar_por_data(data_dia: str) -> int:
    db = get_db()
    docs = list(db.collection("historico").where("data_dia", "==", data_dia).stream())
    refs = [d.reference for d in docs]
    count = _batch_delete(db, refs)
    if count:
        try:
            _resumo_remove_data(db, data_dia)
        except Exception:
            pass
    return count

def limpar_duplicatas() -> dict:
    db = get_db()
    docs = list(db.collection("historico").select(
        ["data_dia", "posto", "data_registro"]
    ).stream())

    por_chave: dict = {}
    deletar_refs = []

    for d in docs:
        data = d.to_dict()
        dia = _extrair_data_dia(data)
        posto = data.get("posto")
        if not dia or not posto:
            continue
        chave = f"{dia}|{posto}"
        existente = por_chave.get(chave)
        if existente is None or data.get("data_registro", "") > existente["data"].get("data_registro", ""):
            if existente:
                deletar_refs.append(existente["ref"])
            por_chave[chave] = {"ref": d.reference, "data": data}
        else:
            deletar_refs.append(d.reference)

    deletados = _batch_delete(db, deletar_refs)
    return {"mantidos": len(por_chave), "deletados": deletados}

def buscar_postos_disponiveis() -> list:
    """1 leitura Firestore — usa o documento de resumo."""
    db = get_db()
    doc = _resumo_ref(db).get()
    if not doc.exists:
        return []
    postos = doc.to_dict().get("postos", {})
    return [{"posto": k, "descricao": v} for k, v in sorted(postos.items())]
