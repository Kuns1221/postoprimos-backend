from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

from processor import processar_planilha
from firebase_db import salvar_historico, buscar_historico, buscar_postos_disponiveis

app = FastAPI(title="PostoPrimos API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
def root():
    return {"status": "PostoPrimos API rodando", "versao": "2.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/processar")
async def processar(arquivo: UploadFile = File(...)):
    if not arquivo.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Apenas arquivos .xls ou .xlsx são aceitos.")

    caminho = os.path.join(UPLOAD_DIR, arquivo.filename)
    conteudo = await arquivo.read()
    with open(caminho, "wb") as f:
        f.write(conteudo)

    resultado = processar_planilha(caminho, arquivo.filename)
    os.remove(caminho)

    if "erro" in resultado:
        raise HTTPException(status_code=422, detail=resultado["erro"])

    return resultado

@app.post("/salvar")
async def salvar(dados: dict):
    try:
        id_salvo = salvar_historico(dados)
        return {"ok": True, "id": id_salvo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/historico")
def historico(posto: str = Query(None), limite: int = Query(100)):
    try:
        return buscar_historico(posto=posto, limite=limite)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/historico/postos")
def historico_postos():
    try:
        return buscar_postos_disponiveis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-firebase")
def test_firebase():
    try:
        from firebase_db import get_db
        db = get_db()
        db.collection("test").document("ping").set({"ok": True})
        return {"status": "Firebase conectado com sucesso"}
    except Exception as e:
        return {"status": "Erro", "detalhe": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
