import re
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from rpg_rules_ai import services
from rpg_rules_ai.config import settings

app = FastAPI(title="RPG Rules AI")

_pkg_dir = Path(__file__).parent
templates = Jinja2Templates(directory=str(_pkg_dir / "templates"))
templates.env.filters["regex_replace"] = lambda s, pattern, repl: re.sub(pattern, repl, s)
app.mount("/static", StaticFiles(directory=str(_pkg_dir / "static")), name="static")


# --- JSON API router (mounted at /api/) ---

api_router = APIRouter(prefix="/api")


@api_router.get("/health")
def health():
    return {"status": "ok"}


# Keep /health at root too for backwards compatibility
@app.get("/health")
def health_root():
    return {"status": "ok"}


# --- Ask ---


class AskRequest(BaseModel):
    question: str


@api_router.post("/ask")
async def ask(req: AskRequest):
    return await services.ask_question(req.question)


# --- Documents ---


class IngestRequest(BaseModel):
    paths: list[str]
    replace: bool = False


MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB


@api_router.get("/documents")
def list_documents():
    return services.list_books()


@api_router.post("/documents/upload", status_code=202)
async def upload_documents(files: list[UploadFile], replace: bool = False):
    saved_paths: list[Path] = []
    sources_dir = Path(settings.sources_dir)

    for f in files:
        if not f.filename or not f.filename.endswith(".md"):
            raise HTTPException(
                status_code=400,
                detail=f"Only .md files are accepted, got: {f.filename}",
            )
        content = await f.read()
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {f.filename} ({len(content)} bytes, max {MAX_UPLOAD_SIZE})",
            )
        dest = sources_dir / f.filename
        dest.write_bytes(content)
        saved_paths.append(dest)

    try:
        job_id = services.create_ingestion_job(saved_paths, replace=replace)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"job_id": job_id}


@api_router.post("/documents/ingest", status_code=202)
def ingest_documents(req: IngestRequest):
    resolved = [Path(p) for p in req.paths]
    try:
        job_id = services.create_ingestion_job(resolved, replace=req.replace)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"job_id": job_id}


@api_router.get("/documents/jobs/{job_id}")
def get_job_progress(job_id: str):
    try:
        return services.get_job_progress(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


@api_router.delete("/documents/{book}")
def delete_document(book: str):
    services.delete_book(book)
    return {"deleted": book}


# --- Entity Graph ---


@api_router.get("/entity-graph")
def entity_graph(chunks: str = ""):
    """Return entity graph for given chunk doc_ids (comma-separated)."""
    if not chunks:
        return {"nodes": [], "edges": []}
    chunk_ids = [c.strip() for c in chunks.split(",") if c.strip()]
    if not chunk_ids:
        return {"nodes": [], "edges": []}
    try:
        from rpg_rules_ai.entity_index import EntityIndex
        idx = EntityIndex()
        try:
            return idx.build_graph_for_chunks(chunk_ids)
        finally:
            idx.close()
    except Exception:
        return {"nodes": [], "edges": []}


# --- Prompts ---


@api_router.get("/prompts")
def list_prompts():
    return services.list_prompts()


@api_router.get("/prompts/{name}")
def get_prompt(name: str):
    try:
        return services.get_prompt(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {name}")


class PromptUpdateRequest(BaseModel):
    content: str


@api_router.put("/prompts/{name}")
def update_prompt(name: str, req: PromptUpdateRequest):
    try:
        services.save_prompt(name, req.content)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {name}")
    return {"saved": name}


@api_router.delete("/prompts/{name}")
def delete_prompt(name: str):
    try:
        return services.reset_prompt(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {name}")


# --- Mount routers ---

app.include_router(api_router)

from rpg_rules_ai.frontend import router as frontend_router  # noqa: E402

app.include_router(frontend_router)
