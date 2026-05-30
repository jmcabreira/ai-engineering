#!/bin/bash
set -e

echo "Waiting for SeaweedFS to be ready..."
until curl -sf http://seaweedfs:9333/cluster/status > /dev/null 2>&1; do
    sleep 2
done
echo "SeaweedFS is ready."

# Create bucket via S3 API
aws --endpoint-url http://seaweedfs:8333 s3 mb s3://dataops-lake 2>/dev/null || true
echo "Bucket 'dataops-lake' ready."

# Upload seed documents
for f in /infra/docs/*; do
    filename=$(basename "$f")
    aws --endpoint-url http://seaweedfs:8333 s3 cp "$f" "s3://dataops-lake/docs/$filename"
    echo "Uploaded: $filename"
done

echo "SeaweedFS init complete."
