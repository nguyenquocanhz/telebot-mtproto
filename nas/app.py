# -*- coding: utf-8 -*-
# HomeNAS FastAPI Backend (app.py)

import os
import shutil
import time
import psutil
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

STORAGE_DIR = os.getenv("STORAGE_DIR", "./storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

app = FastAPI(title="HomeNAS Server", version="1.0.0")

templates = Jinja2Templates(directory="templates")

def get_safe_path(rel_path: str) -> Path:
    """Đảm bảo đường dẫn tuyệt đối nằm trong thư mục STORAGE_DIR (Bảo mật path traversal)"""
    base = Path(STORAGE_DIR).resolve()
    target = (base / rel_path.lstrip("/\\")).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(status_code=403, detail="Access Denied: Path traversal detected")
    return target

def format_size(bytes_size: int) -> str:
    """Format dung lượng dạng KB, MB, GB"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/system")
async def get_system_stats():
    """Lấy thông tin dung lượng ổ đĩa và hệ thống"""
    disk = psutil.disk_usage(STORAGE_DIR)
    mem = psutil.virtual_memory()
    return {
        "disk": {
            "total": format_size(disk.total),
            "used": format_size(disk.used),
            "free": format_size(disk.free),
            "percent": disk.percent,
            "raw_total": disk.total,
            "raw_used": disk.used,
            "raw_free": disk.free
        },
        "memory": {
            "percent": mem.percent
        },
        "cpu": {
            "percent": psutil.cpu_percent(interval=0.1)
        }
    }

@app.get("/api/files")
async def list_files(path: str = Query("", description="Đường dẫn tương đối")):
    target = get_safe_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    items = []
    for p in target.iterdir():
        try:
            stat = p.stat()
            is_dir = p.is_dir()
            ext = p.suffix.lower().replace(".", "") if not is_dir else ""
            
            # Phân loại icon type
            icon_type = "folder" if is_dir else "file"
            if ext in ["jpg", "jpeg", "png", "gif", "webp", "svg"]:
                icon_type = "image"
            elif ext in ["mp4", "mkv", "avi", "mov", "webm"]:
                icon_type = "video"
            elif ext in ["mp3", "flac", "wav", "ogg", "m4a"]:
                icon_type = "audio"
            elif ext in ["zip", "rar", "tar", "gz", "7z"]:
                icon_type = "archive"
            elif ext in ["pdf", "doc", "docx", "txt", "md"]:
                icon_type = "document"

            rel_item_path = str(p.relative_to(Path(STORAGE_DIR).resolve())).replace("\\", "/")

            items.append({
                "name": p.name,
                "path": rel_item_path,
                "is_dir": is_dir,
                "size": format_size(stat.st_size) if not is_dir else "-",
                "raw_size": stat.st_size if not is_dir else 0,
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                "ext": ext,
                "icon": icon_type
            })
        except Exception:
            continue

    # Sắp xếp thư mục lên trước, tệp tin theo sau
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return {"current_path": path, "items": items}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), path: str = Form("")):
    target_dir = get_safe_path(path)
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Invalid target directory")

    dest_path = target_dir / file.filename
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"message": "Upload successful", "filename": file.filename}

@app.get("/api/download")
async def download_file(path: str = Query(...)):
    target = get_safe_path(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target, filename=target.name)

@app.post("/api/mkdir")
async def create_directory(name: str = Form(...), path: str = Form("")):
    target_dir = get_safe_path(path) / name
    if target_dir.exists():
        raise HTTPException(status_code=400, detail="Directory already exists")
    target_dir.mkdir(parents=True, exist_ok=True)
    return {"message": "Folder created successfully"}

@app.delete("/api/delete")
async def delete_item(path: str = Query(...)):
    target = get_safe_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Item not found")

    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()

    return {"message": "Deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    print(f"HomeNAS running on port 8080. Storage: {os.path.abspath(STORAGE_DIR)}")
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
