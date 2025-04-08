import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import NoCredentialsError
import time
from tuyendung.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME, AWS_S3_URL, AWS_REGION

AWS_ACCESS_KEY = AWS_ACCESS_KEY_ID
AWS_SECRET_KEY = AWS_SECRET_ACCESS_KEY
BUCKET_NAME = AWS_STORAGE_BUCKET_NAME
REGION_NAME = AWS_REGION

def get_content_type(file_path):
    extension = os.path.splitext(file_path)[1].lower()
    content_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.txt': 'text/plain'
    }
    return content_types.get(extension, 'application/octet-stream')  # Mặc định nếu không nhận diện được

def upload_to_s3(file_path, object_name=None):
    if object_name is None:
        object_name = os.path.basename(file_path)
    
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION_NAME
    )
    
    try:
        s3.upload_file(
            Filename=file_path,
            Bucket=BUCKET_NAME,
            Key=object_name,
            ExtraArgs={
                'ContentType': get_content_type(file_path),
                'ContentDisposition': 'inline'  
            }
        )
        url = f"https://{BUCKET_NAME}.s3.{REGION_NAME}.amazonaws.com/{object_name}"
        return url

    except FileNotFoundError:
        return "❌ File không tồn tại."
    except NoCredentialsError:
        return "❌ Lỗi credential AWS."
    except Exception as e:
        return f"❌ Lỗi: {e}"
