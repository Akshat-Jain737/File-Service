import asyncio
from math import ceil
from urllib.parse import unquote_plus
from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from models import Files, Status, UploadSession
from UTILS.miniIO import BUCKET_NAME, s3_client
from UTILS.func import (
    MULTIPART_THRESHOLD,
    WEBHOOK_SECRET,
    calculate_part_size,
    generate_object_key,
    generate_presigned_url,
    parse_size_str,
    s3_complete_multipart_upload,
    s3_create_multipart_upload,
)
from PAYLOAD.upload_payload import CompleteMultipartRequest, FileItem, Download


class DataServices:
    def __init__(self, session: AsyncSession | None = None):
        self.session = session

    async def init_upload(self, files: list[FileItem]) -> list[dict]:
        result = []
        for file in files:
            file_name = file.filename
            size_bytes = parse_size_str(file.size)
            obj_name = generate_object_key(file_name)

            if size_bytes >= MULTIPART_THRESHOLD:
                try:
                    mp_resp = await asyncio.to_thread(
                        s3_create_multipart_upload,
                        bucket=BUCKET_NAME,
                        key=obj_name,
                    )
                    upload_id = mp_resp["UploadId"]
                except Exception as e:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to initiate multipart upload for '{file_name}': {str(e)}",
                    )

                part_size = calculate_part_size(size_bytes)
                total_parts = ceil(size_bytes / part_size)

                # Persist upload session record in DB
                upload_session = UploadSession(
                    name=file_name,
                    file_size=size_bytes,
                    object_key=obj_name,
                    upload_id=upload_id,
                    total_parts=total_parts,
                    status=Status.pending,
                )
                if self.session:
                    self.session.add(upload_session)

                urls = [
                    {
                        "part_number": part_num,
                        "upload_url": generate_presigned_url(
                            object_key=obj_name,
                            upload_id=upload_id,
                            part_number=part_num,
                        ),
                    }
                    for part_num in range(1, total_parts + 1)
                ]

                result.append(
                    {
                        "filename": file_name,
                        "size": file.size,
                        "upload": "multipart",
                        "object_key": obj_name,
                        "upload_id": upload_id,
                        "part_size": part_size,
                        "total_parts": total_parts,
                        "URL_part": urls,
                    }
                )
            else:
                url = generate_presigned_url(object_key=obj_name)

                # Persist direct upload session record in DB
                upload_session = UploadSession(
                    name=file_name,
                    file_size=size_bytes,
                    object_key=obj_name,
                    upload_id=None,
                    total_parts=None,
                    status=Status.pending,
                )
                if self.session:
                    self.session.add(upload_session)

                result.append(
                    {
                        "filename": file_name,
                        "size": file.size,
                        "upload": "direct",
                        "object_key": obj_name,
                        "URL": url,
                    }
                )

        if self.session:
            try:
                await self.session.commit()
            except Exception as e:
                await self.session.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to save upload session to database: {str(e)}",
                )

        return result

    async def complete_multipart(self, payload: CompleteMultipartRequest) -> dict:
        parts = [
            {"PartNumber": p.part_number, "ETag": p.etag}
            for p in payload.parts
        ]
        parts.sort(key=lambda x: x["PartNumber"])

        try:
            resp = await asyncio.to_thread(
                s3_complete_multipart_upload,
                bucket=BUCKET_NAME,
                key=payload.object_key,
                upload_id=payload.upload_id,
                parts=parts,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to complete multipart upload on S3: {str(e)}",
            )

        if self.session:
            try:
                query = select(UploadSession).where(
                    UploadSession.object_key == payload.object_key
                )
                session_record = (await self.session.exec(query)).first()

                if session_record:
                    session_record.status = Status.completed
                    self.session.add(session_record)

                    file_record = Files(
                        name=session_record.name,
                        size=session_record.file_size,
                        object_key=session_record.object_key,
                        status=Status.completed,
                    )
                    self.session.add(file_record)
                else:
                    file_record = Files(
                        name=payload.object_key,
                        size=0,
                        object_key=payload.object_key,
                        status=Status.completed,
                    )
                    self.session.add(file_record)

                await self.session.commit()
            except Exception as e:
                await self.session.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to update database after multipart upload: {str(e)}",
                )

        return {
            "status": "success",
            "object_key": payload.object_key,
            "location": resp.get("Location", ""),
        }

    async def WebHook(self,request, token):
        if token != WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Forbidden")
    
        payload=await request.json()
        if payload.get("EventName") == "s3:TestEvent":
            return {"status": "OK"}

        for record in payload["Records"]:
            eventname=record['eventName']

            if eventname is not None:
                raw_key=record['s3']['object']['key']
                objectkey=unquote_plus(raw_key)
                filesize=record['s3']['object']['size']

                query = select(UploadSession).where(
                UploadSession.object_key == objectkey
                ).where(UploadSession.file_size==filesize)

                session_record = (await self.session.exec(query)).first()

                if session_record is not None:
                    session_record.status = Status.completed
                    self.session.add(session_record)
                    file_record = Files(
                        name=session_record.name,
                        size=session_record.file_size,
                        object_key=session_record.object_key,
                        status=Status.completed,
                    )
                    self.session.add(file_record)
                
                else:
                    raise HTTPException(
                        status_code=200, detail='file corrupted'
                    )
            else:
                raise HTTPException(status_code=500)
            
        try:
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to complete direct upload in database: {str(e)}",
            )
        return {'status': 'sucess'}
    
    async def init_download(self,file_ids:Download):
        result=[]
        for file_id in file_ids:
            rec = (
                await self.session.exec(select(Files).where(Files.id == file_id))
            ).first()
            if not rec:
                raise HTTPException(status_code=500, detail='file not found')
            
            result.append({
                "file_id":file_id,
                "url": generate_presigned_url(object_key=rec.object_key, method='GET'),
            })
        
        return result