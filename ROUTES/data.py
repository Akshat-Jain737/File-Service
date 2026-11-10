from urllib.parse import unquote_plus

from fastapi import APIRouter, Body, HTTPException, Request
from PAYLOAD.upload_payload import CompleteMultipartRequest, Download, FileItem, UploadRequest
from UTILS.dependencies import dep
from UTILS.func import WEBHOOK_SECRET
from models import UploadSession

data = APIRouter(tags=["Upload"], prefix="/data")

@data.post("/upload_init")
async def upload_init(service: dep, payload: list[FileItem] | UploadRequest = Body(...)):
    files = payload.data if isinstance(payload, UploadRequest) else payload
    return await service.init_upload(files)

@data.post("/minio_webhook")
async def webhook(service:dep, request:Request, token:str):
    return await service.WebHook(request, token)


@data.post("/upload_multipart/complete")
async def upload_multipart_complete(service: dep, payload: CompleteMultipartRequest):
    return await service.complete_multipart(payload)


@data.post("/download_init")
async def download_init(service: dep, payload: Download):
    return await service.init_download(payload.file_ids)