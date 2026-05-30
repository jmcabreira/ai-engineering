"""Custom readers for SeaweedFS and MongoDB data sources."""
import logging
from datetime import datetime, timedelta, timezone
from io import BytesIO

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from llama_index.core.schema import Document
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from src.ingestion.config import IngestionConfig

log = logging.getLogger(__name__)


class SeaweedFSReader:
    """Reads documents from a SeaweedFS S3-compatible bucket."""

    def __init__(self, config: IngestionConfig) -> None:
        self._config = config

    def load_data(self) -> list[Document]:
        endpoint = f"http://{self._config.seaweedfs_host}:{self._config.seaweedfs_port}"
        try:
            s3 = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id="any",
                aws_secret_access_key="any",
                region_name="us-east-1",
            )
            response = s3.list_objects_v2(Bucket=self._config.seaweedfs_bucket)
        except (BotoCoreError, ClientError) as exc:
            log.warning("SeaweedFS unavailable — skipping: %s", exc)
            return []

        documents: list[Document] = []
        for obj in response.get("Contents", []):
            key: str = obj["Key"]
            try:
                body = s3.get_object(Bucket=self._config.seaweedfs_bucket, Key=key)["Body"].read()
                text = body.decode("utf-8", errors="replace")
                ext = key.rsplit(".", 1)[-1].lower() if "." in key else "unknown"
                documents.append(
                    Document(
                        text=text,
                        metadata={
                            "source_type": "seaweedfs",
                            "file_name": key.split("/")[-1],
                            "file_path": key,
                            "file_type": ext,
                            "upload_date": obj.get("LastModified", "").isoformat()
                            if obj.get("LastModified")
                            else "",
                            "bucket": self._config.seaweedfs_bucket,
                        },
                    )
                )
                log.debug("Loaded from SeaweedFS: %s (%d chars)", key, len(text))
            except Exception as exc:
                log.warning("Failed to read %s from SeaweedFS: %s", key, exc)

        log.info("SeaweedFSReader loaded %d documents", len(documents))
        return documents


class MongoDBReader:
    """Reads event_logs and user_activity from MongoDB (last 24 hours)."""

    def __init__(self, config: IngestionConfig) -> None:
        self._config = config

    def load_data(self) -> list[Document]:
        uri = f"mongodb://{self._config.mongo_host}:{self._config.mongo_port}"
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            db = client[self._config.mongo_db]
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        except PyMongoError as exc:
            log.warning("MongoDB unavailable — skipping: %s", exc)
            return []

        documents: list[Document] = []

        # event_logs
        try:
            for doc in db.event_logs.find({"timestamp": {"$gte": cutoff}}):
                error_part = f" | error: {doc['error_message']}" if doc.get("error_message") else ""
                text = (
                    f"Pipeline: {doc['pipeline_name']} | status: {doc['status']} "
                    f"| severity: {doc['severity']} | duration: {doc['duration_seconds']}s "
                    f"| records: {doc['records_processed']}{error_part}"
                )
                documents.append(
                    Document(
                        text=text,
                        metadata={
                            "source_type": "mongodb",
                            "collection": "event_logs",
                            "pipeline_name": doc.get("pipeline_name", ""),
                            "status": doc.get("status", ""),
                            "severity": doc.get("severity", ""),
                            "timestamp": doc.get("timestamp", datetime.now(timezone.utc)).isoformat(),
                        },
                    )
                )
        except PyMongoError as exc:
            log.warning("Failed to read event_logs: %s", exc)

        # user_activity
        try:
            for doc in db.user_activity.find({"timestamp": {"$gte": cutoff}}):
                metadata_str = " | ".join(f"{k}: {v}" for k, v in doc.get("metadata", {}).items())
                text = (
                    f"User: {doc['user_id']} | action: {doc['action']} "
                    f"| session: {doc['session_id']}"
                    + (f" | {metadata_str}" if metadata_str else "")
                )
                documents.append(
                    Document(
                        text=text,
                        metadata={
                            "source_type": "mongodb",
                            "collection": "user_activity",
                            "action": doc.get("action", ""),
                            "user_id": doc.get("user_id", ""),
                            "timestamp": doc.get("timestamp", datetime.now(timezone.utc)).isoformat(),
                        },
                    )
                )
        except PyMongoError as exc:
            log.warning("Failed to read user_activity: %s", exc)

        client.close()
        log.info("MongoDBReader loaded %d documents", len(documents))
        return documents
