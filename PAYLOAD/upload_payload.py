from typing import Any
from pydantic import BaseModel, field_validator, model_validator
from UTILS.func import parse_size_str


class FileItem(BaseModel):
    filename: str
    size: str | int

    @model_validator(mode="before")
    @classmethod
    def check_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "filename" not in data and "name" in data:
                data["filename"] = data["name"]
        return data

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("filename must be a string")
        v = v.strip()
        if not v or "/" in v or "\\" in v or "\x00" in v:
            raise ValueError("Invalid filename")
        return v

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: str | int) -> str | int:
        parse_size_str(v)
        return v


class UploadRequest(BaseModel):
    data: list[FileItem]
    parent: int | None = None
    action: str | None = None


class PartInfo(BaseModel):
    part_number: int
    etag: str


    @field_validator("etag")
    @classmethod
    def clean_etag(cls, v: str) -> str:
        return v.strip().strip('"')


class CompleteMultipartRequest(BaseModel):
    object_key: str
    upload_id: str
    parts: list[PartInfo]

    @model_validator(mode="before")
    @classmethod
    def check_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "upload_id" not in data and "uploadId" in data:
                data["upload_id"] = data["uploadId"]
            if "parts" not in data and "partsinfo" in data:
                data["parts"] = data["partsinfo"]
        return data
