"""
bucket_utils.py  –  S3 helper functions for Parent Reports service.

Responsibilities:
  • Ensure a bucket exists (idempotent)
  • Wipe & recreate for tests (dangerous)
  • Configure public-read access via policy/ACL
  • Reset the S3 client pool to avoid socket exhaustion
"""
from __future__ import annotations
import os
import json
import boto3
import botocore.exceptions as bex
import botocore.config

from web.Exam.Parent_Reports.logging_logs.log_config import get_logger

# ───────────────────────── Configuration ─────────────────────────
REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET = os.getenv(
    "S3_BUCKET_PARENT_REPORTS", "parent-whatsapp-report"
)

_cfg = botocore.config.Config(
    max_pool_connections=50,  # Reduced to avoid connection issues
    connect_timeout=30,       # Increased timeout
    read_timeout=120,
    retries={"max_attempts": 5, "mode": "adaptive"},
    tcp_keepalive=True,
    # Add SSL-specific configurations
    parameter_validation=False,  # Skip parameter validation for speed
)

# boto3 s3 client and resource share the same config
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=REGION,
    config=_cfg,
)
s3_resource = boto3.resource(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=REGION,
    config=_cfg,
)

logger = get_logger("s3.bucket_utils")

# ────────────────────────── Internal helpers ──────────────────────────

def _empty_bucket(bucket_name: str) -> None:
    """Delete all objects and versions in the bucket."""
    bucket = s3_resource.Bucket(bucket_name)
    to_delete = [
        {"Key": obj.object_key if hasattr(obj, 'object_key') else obj.key,
         **({"VersionId": obj.id} if hasattr(obj, 'id') else {})
        }
        for obj in bucket.object_versions.all()
    ]
    if to_delete:
        bucket.delete_objects(Delete={"Objects": to_delete})
        logger.info("Deleted %s objects from %s", len(to_delete), bucket_name)


def _allow_public_read(bucket_name: str) -> None:
    """Disable block-public-access and attach a public-read policy."""
    # disable the block-public-access settings
    s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )
    # attach bucket policy
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{bucket_name}/*",
        }],
    }
    s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
    # try to set ACL, ignore if unsupported
    try:
        s3.put_bucket_acl(Bucket=bucket_name, ACL="public-read")
    except bex.ClientError as e:
        if e.response['Error']['Code'] != 'AccessControlListNotSupported':
            raise
        logger.debug("ACL not supported on %s, relying on policy.", bucket_name)
    logger.info("Bucket %s is now public-read", bucket_name)

# ─────────────────────────── Public API ────────────────────────────

def ensure_bucket_exists(bucket_name: str, max_retries: int = 3) -> None:
    """Idempotent: create bucket if missing with SSL retry logic."""
    import time
    import ssl
    
    for attempt in range(max_retries):
        try:
            s3.head_bucket(Bucket=bucket_name)
            logger.debug("Bucket %s already exists", bucket_name)
            return
        except (ssl.SSLError, bex.SSLError) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"SSL error on attempt {attempt + 1}, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"SSL error after {max_retries} attempts: {e}")
                raise
        except bex.ClientError as e:
            if e.response['Error']['Code'] in ("404", "NoSuchBucket"):
                try:
                    create_args = {"Bucket": bucket_name}
                    if REGION != "us-east-1":
                        create_args['CreateBucketConfiguration'] = {'LocationConstraint': REGION}
                    s3.create_bucket(**create_args)
                    logger.info("Created bucket %s in %s", bucket_name, REGION)
                    return
                except (ssl.SSLError, bex.SSLError) as ssl_err:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"SSL error creating bucket on attempt {attempt + 1}, retrying in {wait_time}s: {ssl_err}")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"SSL error creating bucket after {max_retries} attempts: {ssl_err}")
                        raise
            else:
                raise


def recreate_bucket(bucket_name: str, public: bool = False) -> None:
    """Dangerous: delete everything & re-create.
    Useful for CI/tests when you need a clean slate."""
    try:
        s3.head_bucket(Bucket=bucket_name)
        logger.warning("Recreating bucket %s", bucket_name)
        _empty_bucket(bucket_name)
        s3.delete_bucket(Bucket=bucket_name)
    except bex.ClientError as e:
        if e.response['Error']['Code'] not in ("404", "NoSuchBucket"):
            raise
    # now create fresh
    create_args = {"Bucket": bucket_name}
    if REGION != "us-east-1":
        create_args['CreateBucketConfiguration'] = {'LocationConstraint': REGION}
    s3.create_bucket(**create_args)
    logger.info("Recreated bucket %s", bucket_name)
    if public:
        _allow_public_read(bucket_name)


def ensure_bucket_ready(bucket_name: str, public: bool = False) -> None:
    """
    Ensure the bucket exists; if `public=True`, also enable public-read.
    Does *not* delete anything.
    """
    try:
        ensure_bucket_exists(bucket_name)
        if public:
            _allow_public_read(bucket_name)
    except Exception as e:
        logger.error(f"Failed to ensure bucket ready: {e}")
        # Don't re-raise to allow the application to continue
        # The upload functions will handle individual failures


def reset_s3_connection_pool() -> bool:
    """Reinitialize the module-level S3 client to clear pools."""
    global s3
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=REGION,
            config=_cfg,
        )
        logger.info("S3 connection pool reset")
        return True
    except Exception as e:
        logger.error("Error resetting S3 pool: %s", e)
        return False
