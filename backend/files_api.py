import os
import re
import uuid
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from file_validation import FILE_TYPES, MAX_FILE_SIZE, file_info, validate_content
from storage_service import storage


class FileRecord(BaseModel):
    id: str
    original_filename: str
    content_type: str
    kind: Literal["document", "image", "video", "audio"]
    size: int
    created_at: str


class FileList(BaseModel):
    items: list[FileRecord]
    total: int
    total_size: int
    page: int
    page_size: int


def create_files_router(db, current_user):
    router = APIRouter(prefix="/api/files", tags=["files"])

    async def write_origin(request: Request):
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != os.environ["FRONTEND_URL"].rstrip("/"):
            raise HTTPException(403, "Origem não permitida.")

    async def owned_file(file_id, user_id):
        doc = await db.files.find_one({"id": file_id, "user_id": user_id, "is_deleted": False}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Arquivo não encontrado.")
        return doc

    @router.get("/config")
    async def config(user=Depends(current_user)):
        return {"max_file_size": MAX_FILE_SIZE, "extensions": list(FILE_TYPES)}

    @router.get("", response_model=FileList)
    async def list_files(
        q: str = Query("", max_length=180),
        kind: Literal["all", "document", "image", "video", "audio"] = "all",
        page: int = Query(1, ge=1), page_size: int = Query(24, ge=1, le=100), user=Depends(current_user)
    ):
        query = {"user_id": user.id, "is_deleted": False}
        if q.strip():
            query["original_filename"] = {"$regex": re.escape(q.strip()), "$options": "i"}
        if kind != "all":
            query["kind"] = kind
        total = await db.files.count_documents(query)
        docs = await db.files.find(query, {"_id": 0}).sort([("created_at", -1), ("id", 1)]).skip((page - 1) * page_size).to_list(page_size)
        sizes = await db.files.aggregate([
            {"$match": query}, {"$group": {"_id": None, "size": {"$sum": "$size"}}}, {"$project": {"_id": 0, "size": 1}}
        ]).to_list(1)
        return FileList(items=[FileRecord(**doc) for doc in docs], total=total,
                        total_size=sizes[0]["size"] if sizes else 0, page=page, page_size=page_size)

    @router.post("", response_model=FileRecord, status_code=201, dependencies=[Depends(write_origin)])
    async def upload_file(file: UploadFile = File(...), user=Depends(current_user)):
        try:
            name, ext, mime, kind = file_info(file.filename)
            if file.size is not None and file.size > MAX_FILE_SIZE:
                raise HTTPException(413, "Cada arquivo pode ter no máximo 25 MB.")
            data = await file.read(MAX_FILE_SIZE + 1)
            await run_in_threadpool(validate_content, data, ext)
        finally:
            await file.close()
        file_id = str(uuid.uuid4())
        result = await storage.put(f"finance-nunes/uploads/{user.id}/{file_id}{ext}", data, mime)
        record = FileRecord(id=file_id, original_filename=name, content_type=mime, kind=kind,
                            size=len(data), created_at=datetime.now(timezone.utc).isoformat())
        await db.files.insert_one({**record.model_dump(), "user_id": user.id,
                                   "storage_path": result["path"], "is_deleted": False})
        return record

    @router.get("/{file_id}/download")
    async def download_file(file_id: str, user=Depends(current_user)):
        doc = await owned_file(file_id, user.id)
        data = await storage.get(doc["storage_path"])
        return Response(content=data, media_type=doc["content_type"], headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(doc['original_filename'], safe='')}",
            "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
            "Vary": "Cookie, Authorization",
        })

    @router.delete("/{file_id}", status_code=204, dependencies=[Depends(write_origin)])
    async def delete_file(file_id: str, user=Depends(current_user)):
        await owned_file(file_id, user.id)
        await db.files.update_one({"id": file_id, "user_id": user.id, "is_deleted": False},
                                  {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}})
        return Response(status_code=204)

    return router