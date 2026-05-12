from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os

from processor import processar_planilha

app = FastAPI(title="PostoPrimos API", version="1.0.0")

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
    return {"status": "PostoPrimos API rodando", "versao": "1.0.0"}

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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
