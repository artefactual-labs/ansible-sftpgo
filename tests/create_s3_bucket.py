import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


client = boto3.client(
    "s3",
    endpoint_url=os.environ.get("SFTPGO_CI_S3_ENDPOINT", "http://127.0.0.1:8333"),
    aws_access_key_id="sftpgo-ci-access",
    aws_secret_access_key="sftpgo-ci-secret",
    region_name="us-east-1",
    config=Config(s3={"addressing_style": "path"}),
)
try:
    client.create_bucket(Bucket="sftpgo-ci")
except ClientError as error:
    if error.response["Error"]["Code"] not in {"BucketAlreadyExists", "BucketAlreadyOwnedByYou"}:
        raise

client.put_object(Bucket="sftpgo-ci", Key="protected/seed.txt", Body=b"read-only test fixture\n")
