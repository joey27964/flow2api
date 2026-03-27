import boto3
import uuid
import base64
import asyncio
import random
import string
import time as _time
from datetime import datetime
from botocore.config import Config
from ..core.logger import debug_logger

R2_CONFIG = {
    "endpoint_url": "https://ee73f4262042dc8614e04f1f89aa10f0.r2.cloudflarestorage.com",
    "access_key_id": "d2827b3533b5decdf4cbd2878648d3af",
    "secret_access_key": "e6dbdecdc214ab2373758b0a94e57faf9297fed87775076d6305076ffe467d7b",
    "bucket_name": "moocooai",
    "base_url": "https://storage-googleapis.com"
}

_s3_client = None

def _get_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=R2_CONFIG["endpoint_url"],
            aws_access_key_id=R2_CONFIG["access_key_id"],
            aws_secret_access_key=R2_CONFIG["secret_access_key"],
            config=Config(signature_version="s3v4"),
            region_name="auto"
        )
    return _s3_client

def upload_to_r2_sync(image_bytes, mime_type="image/jpeg"):
    ext = "jpg" if "jpeg" in mime_type else ("png" if "png" in mime_type else "webp")
    hour_prefix = datetime.now().strftime("hour_%H")
    file_id = f"ai-sandbox-videofx/image/{hour_prefix}/{uuid.uuid4()}.{ext}"
    try:
        client = _get_client()
        client.put_object(
            Bucket=R2_CONFIG["bucket_name"],
            Key=file_id,
            Body=image_bytes,
            ContentType=mime_type
        )
        sig = ''.join(random.choices(string.ascii_letters + string.digits, k=60))
        sig_encoded = sig[:20] + '%2F' + sig[20:40] + '%2B' + sig[40:]
        expires = str(int(_time.time()) + 86400)
        url = f"{R2_CONFIG['base_url']}/{file_id}?GoogleAccessId=labs-ai-sandbox-videoserver-prod@system.gserviceaccount.com&Expires={expires}&Signature={sig_encoded}"
        debug_logger.log_info(f"[R2] Uploaded {len(image_bytes)//1024}KB -> {url[:80]}...")
        return url
    except Exception as e:
        debug_logger.log_error(f"[R2] Upload failed: {e}")
        return None

async def upload_to_r2(image_bytes, mime_type="image/jpeg"):
    return await asyncio.to_thread(upload_to_r2_sync, image_bytes, mime_type)
