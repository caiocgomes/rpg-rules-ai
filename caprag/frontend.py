from pathlib import Path

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from caprag import services
from caprag.config import settings

router = APIRouter()


def _templates():
    from caprag.api import templates
    return templates


# --- Chat ---


@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return _templates().TemplateResponse(
        "chat.html", {"request": request, "active_page": "chat"}
    )


@router.post("/chat/ask", response_class=HTMLResponse)
async def chat_ask(request: Request, question: str = Form(...)):
    answer = await services.ask_question(question)
    t = _templates()
    user_html = t.TemplateResponse(
        "fragments/chat_message.html",
        {"request": request, "question": question},
    ).body.decode()
    answer_html = t.TemplateResponse(
        "fragments/chat_answer.html",
        {"request": request, "answer": answer},
    ).body.decode()
    return HTMLResponse(user_html + answer_html)


# --- Documents ---


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(request: Request):
    books = services.list_books()
    return _templates().TemplateResponse(
        "documents.html",
        {"request": request, "active_page": "documents", "books": books},
    )


@router.get("/documents/list", response_class=HTMLResponse)
async def documents_list_fragment(request: Request):
    books = services.list_books()
    return _templates().TemplateResponse(
        "fragments/doc_list.html", {"request": request, "books": books}
    )


@router.post("/documents/htmx/upload", response_class=HTMLResponse)
async def documents_htmx_upload(
    request: Request, files: list[UploadFile], replace: bool = Form(False)
):
    saved_paths: list[Path] = []
    sources_dir = Path(settings.sources_dir)

    for f in files:
        if not f.filename or not f.filename.endswith(".md"):
            return HTMLResponse(
                f'<div class="file-result error">Only .md files accepted: {f.filename}</div>',
                status_code=400,
            )
        content = await f.read()
        dest = sources_dir / f.filename
        dest.write_bytes(content)
        saved_paths.append(dest)

    try:
        job_id = services.create_ingestion_job(saved_paths, replace=replace)
    except (ValueError, FileNotFoundError) as exc:
        return HTMLResponse(
            f'<div class="file-result error">{exc}</div>',
            status_code=400,
        )

    progress = services.get_job_progress(job_id)
    return _templates().TemplateResponse(
        "fragments/progress.html",
        {
            "request": request,
            "job_id": job_id,
            "progress": progress,
        },
    )


@router.post("/documents/htmx/ingest", response_class=HTMLResponse)
async def documents_htmx_ingest(
    request: Request, directory: str = Form(...), replace: bool = Form(False)
):
    d = Path(directory)
    if not d.is_dir():
        return HTMLResponse(
            f'<div class="file-result error">Directory not found: {directory}</div>',
            status_code=400,
        )
    md_files = sorted(d.glob("*.md"))
    if not md_files:
        return HTMLResponse(
            '<div class="file-result skipped">No .md files found in directory.</div>'
        )

    try:
        job_id = services.create_ingestion_job(list(md_files), replace=replace)
    except (ValueError, FileNotFoundError) as exc:
        return HTMLResponse(
            f'<div class="file-result error">{exc}</div>',
            status_code=400,
        )

    progress = services.get_job_progress(job_id)
    return _templates().TemplateResponse(
        "fragments/progress.html",
        {
            "request": request,
            "job_id": job_id,
            "progress": progress,
        },
    )


@router.get("/documents/htmx/progress/{job_id}", response_class=HTMLResponse)
async def documents_htmx_progress(request: Request, job_id: str):
    try:
        progress = services.get_job_progress(job_id)
    except KeyError:
        return HTMLResponse('<div class="file-result error">Job not found</div>')
    return _templates().TemplateResponse(
        "fragments/progress.html",
        {
            "request": request,
            "job_id": job_id,
            "progress": progress,
        },
    )


@router.delete("/documents/htmx/{book}", response_class=HTMLResponse)
async def documents_htmx_delete(request: Request, book: str):
    services.delete_book(book)
    return HTMLResponse(
        "",
        headers={"HX-Trigger": "refreshDocList"},
    )


# --- Prompts ---


@router.get("/prompts/page", response_class=HTMLResponse)
async def prompts_page(request: Request):
    prompts = services.list_prompts()
    return _templates().TemplateResponse(
        "prompts.html",
        {"request": request, "active_page": "prompts", "prompts": prompts},
    )


@router.put("/prompts/htmx/{name}", response_class=HTMLResponse)
async def prompts_htmx_save(request: Request, name: str, content: str = Form(...)):
    try:
        services.save_prompt(name, content)
        prompt_data = services.get_prompt(name)
    except KeyError:
        return HTMLResponse("Prompt not found", status_code=404)
    return _templates().TemplateResponse(
        "fragments/prompt_card.html",
        {"request": request, "prompt": prompt_data, "saved": True},
    )


@router.delete("/prompts/htmx/{name}", response_class=HTMLResponse)
async def prompts_htmx_reset(request: Request, name: str):
    try:
        services.reset_prompt(name)
        prompt_data = services.get_prompt(name)
    except KeyError:
        return HTMLResponse("Prompt not found", status_code=404)
    return _templates().TemplateResponse(
        "fragments/prompt_card.html",
        {"request": request, "prompt": prompt_data, "reset": True},
    )
