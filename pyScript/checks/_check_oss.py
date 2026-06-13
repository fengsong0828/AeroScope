import os, ssl
ssl._create_default_https_context = ssl._create_unverified_context
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
from dotenv import load_dotenv
load_dotenv(os.path.join(_PROJECT_ROOT, '.env'))
import oss2
auth = oss2.Auth(os.getenv('ALIBABA_ACCESS_KEY_ID'), os.getenv('ALIBABA_ACCESS_KEY_SECRET'))
bucket = oss2.Bucket(auth, os.getenv('OSS_ENDPOINT'), os.getenv('OSS_PRIVATE_BUCKET'))
obj = bucket.get_object_meta('patents/CN114987756A.pdf')
print(f"Exists: True")
print(f"Size: {obj.content_length} bytes ({obj.content_length/1024:.0f} KB)")
print(f"Content-Type: {obj.headers.get('Content-Type','N/A')}")
