import re
import uuid
from math import ceil
from fastapi import HTTPException
from UTILS.miniIO import BUCKET_NAME, s3_client

MIN_PART_SIZE = 5 * 1024 * 1024       # 5MB — S3 minimum chunk size
MAX_PARTS = 10_000                     # S3 max parts per upload
TARGET_PART_SIZE = 8 * 1024 * 1024    # 8MB default chunk size
MULTIPART_THRESHOLD = 100 * 1024 * 1024  # 100MB threshold: >= 100MB uses multipart
WEBHOOK_SECRET = 'rogjirigeuoweih948579438uwohw;gih'


def parse_size_str(size: str | int | float) -> int:
    """
    Parses size strings like '10mb', '13MB', '300mb', '1.5GB', '500kb', '1024b',
    or numeric values into byte integers.
    """
    if size is None:
        raise ValueError("File size cannot be None or empty")

    if isinstance(size, (int, float)):
        size_bytes = int(size)
        if size_bytes <= 0:
            raise ValueError("File size must be greater than 0")
        return size_bytes

    cleaned = str(size).strip().lower()
    if not cleaned:
        raise ValueError("File size cannot be empty")

    match = re.match(r"^(\d+(?:\.\d+)?)\s*([a-z]+)?$", cleaned)
    if not match:
        raise ValueError(f"Invalid file size format: '{size}'")

    number, unit = match.groups()
    number = float(number)

    if number <= 0:
        raise ValueError("File size must be greater than 0")

    unit_multipliers = {
        None: 1,
        "b": 1,
        "bytes": 1,
        "kb": 1024,
        "k": 1024,
        "mb": 1024 * 1024,
        "m": 1024 * 1024,
        "gb": 1024 * 1024 * 1024,
        "g": 1024 * 1024 * 1024,
        "tb": 1024 * 1024 * 1024 * 1024,
    }

    if unit not in unit_multipliers:
        raise ValueError(f"Unknown size unit: '{unit}' in '{size}'")

    return int(number * unit_multipliers[unit])


def calculate_part_size(total_size: int) -> int:
    if total_size <= 0:
        raise ValueError("Invalid file size")

    part_size = TARGET_PART_SIZE
    required_parts = ceil(total_size / part_size)

    if required_parts > MAX_PARTS:
        part_size = ceil(total_size / MAX_PARTS)
        part_size = ceil(part_size / (1024 * 1024)) * (1024 * 1024)

    return max(part_size, MIN_PART_SIZE)


def generate_object_key(filename: str) -> str:
    ext = filename.split(".")[-1] if "." in filename else ""
    suffix = f".{ext}" if ext else ""
    return f"{uuid.uuid4()}{suffix}"


def generate_presigned_url(
    object_key: str,
    method: str = "PUT",
    expires_in: int = 3600,
    upload_id: str | None = None,
    part_number: int | None = None,
    extra_params: dict | None = None,
) -> str:
    """
    Generate presigned URL using boto3 s3_client for MinIO/S3.
    """
    params = {"Bucket": BUCKET_NAME, "Key": object_key}
    if extra_params:
        params.update(extra_params)

    if upload_id is not None and part_number is not None:
        client_method = "upload_part"
        params["UploadId"] = upload_id
        params["PartNumber"] = part_number
    else:
        method_map = {
            "PUT": "put_object",
            "GET": "get_object",
            "DELETE": "delete_object",
        }
        client_method = method_map.get(method.upper(), method)

    try:
        return s3_client.generate_presigned_url(
            ClientMethod=client_method,
            Params=params,
            ExpiresIn=expires_in,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate presigned URL: {str(e)}",
        )
