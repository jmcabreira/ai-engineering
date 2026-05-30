"""Continuous data generator for the DataOps Knowledge Hub."""
import asyncio
import csv
import io
import json
import logging
import os
import random
import signal
import string
import sys
from datetime import datetime, timezone

import boto3
import psycopg2
import psycopg2.extras
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from faker import Faker
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    stream=sys.stdout,
)
log = logging.getLogger("generator")

fake = Faker("pt_BR")

INTERVAL = int(os.getenv("GENERATOR_INTERVAL_SECONDS", "30"))

PG_DSN = (
    f"host={os.getenv('POSTGRES_HOST', 'postgres')} "
    f"port={os.getenv('POSTGRES_PORT', '5432')} "
    f"dbname={os.getenv('POSTGRES_DB', 'dataops')} "
    f"user={os.getenv('POSTGRES_USER', 'dataops')} "
    f"password={os.getenv('POSTGRES_PASSWORD', 'dataops123')}"
)

MONGO_URI = (
    f"mongodb://{os.getenv('MONGO_HOST', 'mongo')}:{os.getenv('MONGO_PORT', '27017')}"
)
MONGO_DB = os.getenv("MONGO_DB", "dataops")

S3_ENDPOINT = (
    f"http://{os.getenv('SEAWEEDFS_HOST', 'seaweedfs')}:{os.getenv('SEAWEEDFS_PORT', '8333')}"
)
S3_BUCKET = os.getenv("SEAWEEDFS_BUCKET", "dataops-lake")

PIPELINES = [
    "etl_billing_daily",
    "etl_orders_hourly",
    "etl_customer_sync",
    "analytics_revenue_agg",
]

PLANS = ["free"] * 6 + ["pro"] * 3 + ["enterprise"]
STATUSES = ["completed"] * 7 + ["pending"] * 2 + ["failed"] + ["refunded"]
EVENT_STATUSES = ["completed"] * 17 + ["failed"] * 2 + ["warning"]
ACTIONS = [
    "query_executed",
    "dashboard_viewed",
    "export_requested",
    "schema_browsed",
    "pipeline_triggered",
]
CATEGORIES = ["Analytics", "Integration", "Storage", "Compute"]
ERROR_MESSAGES = [
    "Connection timeout to source DB",
    "Schema mismatch on column revenue",
    "Out of memory during aggregation",
    "Duplicate key violation on insert",
    "Permission denied on target table",
]

_shutdown = False


def _handle_signal(sig, frame):
    global _shutdown
    log.info("Received signal %s — shutting down gracefully", sig)
    _shutdown = True


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


def _random_hex(n: int) -> str:
    return "".join(random.choices(string.hexdigits[:16], k=n))


async def _retry(coro_fn, name: str, retries: int = 3, delay: float = 2.0):
    for attempt in range(1, retries + 1):
        try:
            return await coro_fn()
        except Exception as exc:
            if attempt == retries:
                log.error("[%s] failed after %d attempts: %s", name, retries, exc)
                raise
            log.warning("[%s] attempt %d failed: %s — retrying in %.1fs", name, attempt, exc, delay)
            await asyncio.sleep(delay * attempt)


# ── PostgreSQL ────────────────────────────────────────────────────────────────

async def write_postgres(cycle: int) -> dict:
    def _run():
        conn = psycopg2.connect(PG_DSN)
        try:
            cur = conn.cursor()

            # Fetch existing customer and product ids
            cur.execute("SELECT id FROM customers ORDER BY RANDOM() LIMIT 100")
            customer_ids = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT id, price FROM products WHERE active = true ORDER BY RANDOM() LIMIT 50")
            products = cur.fetchall()

            counts = {"customers": 0, "products": 0, "orders": 0}

            # Occasional new products (every 5th cycle)
            if cycle % 5 == 0:
                n_products = random.randint(1, 3)
                for _ in range(n_products):
                    name = f"{fake.word().capitalize()} {random.choice(CATEGORIES)} Suite"
                    cur.execute(
                        "INSERT INTO products (name, category, price, sku, active) VALUES (%s,%s,%s,%s,%s)",
                        (
                            name,
                            random.choice(CATEGORIES),
                            round(random.uniform(29, 999), 2),
                            f"SKU-{_random_hex(8).upper()}",
                            True,
                        ),
                    )
                counts["products"] = n_products

            # New customers
            n_customers = random.randint(2, 5)
            new_customer_ids = []
            for _ in range(n_customers):
                cur.execute(
                    "INSERT INTO customers (name, email, plan, company) VALUES (%s,%s,%s,%s) RETURNING id",
                    (
                        fake.name(),
                        fake.email(),
                        random.choice(PLANS),
                        fake.company(),
                    ),
                )
                new_customer_ids.append(cur.fetchone()[0])
            counts["customers"] = n_customers

            # New orders
            all_customer_ids = customer_ids + new_customer_ids
            if all_customer_ids and products:
                n_orders = random.randint(5, 15)
                for _ in range(n_orders):
                    prod_id, price = random.choice(products)
                    qty = random.randint(1, 10)
                    cur.execute(
                        "INSERT INTO orders (customer_id, product_id, amount, quantity, status) VALUES (%s,%s,%s,%s,%s)",
                        (
                            random.choice(all_customer_ids),
                            prod_id,
                            round(price * qty, 2),
                            qty,
                            random.choice(STATUSES),
                        ),
                    )
                counts["orders"] = n_orders

            conn.commit()
            return counts
        finally:
            conn.close()

    return await asyncio.get_event_loop().run_in_executor(None, _run)


# ── MongoDB ───────────────────────────────────────────────────────────────────

async def write_mongo() -> dict:
    def _run():
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[MONGO_DB]
        counts = {"event_logs": 0, "user_activity": 0}

        # event_logs
        n_events = random.randint(3, 8)
        events = []
        for _ in range(n_events):
            pipeline = random.choice(PIPELINES)
            status = random.choice(EVENT_STATUSES)
            is_hourly = "hourly" in pipeline
            duration = random.randint(10, 120) if is_hourly else random.randint(30, 600)
            events.append({
                "pipeline_name": pipeline,
                "status": status,
                "severity": {"completed": "info", "warning": "warning", "failed": "critical"}[status],
                "error_message": random.choice(ERROR_MESSAGES) if status == "failed" else None,
                "duration_seconds": duration if status != "failed" else random.randint(1, 30),
                "records_processed": random.randint(1000, 100000) if status != "failed" else 0,
                "timestamp": datetime.now(timezone.utc),
            })
        db.event_logs.insert_many(events)
        counts["event_logs"] = n_events

        # user_activity
        n_activity = random.randint(5, 10)
        activities = []
        for _ in range(n_activity):
            action = random.choice(ACTIONS)
            metadata: dict = {}
            if action == "query_executed":
                metadata = {
                    "table": random.choice(["customers", "orders", "products", "fact_revenue"]),
                    "rows_returned": random.randint(0, 5000),
                    "execution_time_ms": random.randint(10, 3000),
                }
            elif action == "dashboard_viewed":
                metadata = {"dashboard": f"dashboard_{random.randint(1, 3)}"}
            elif action == "export_requested":
                metadata = {"format": random.choice(["csv", "parquet", "json"]), "rows": random.randint(100, 50000)}
            elif action == "pipeline_triggered":
                metadata = {"pipeline": random.choice(PIPELINES)}

            activities.append({
                "user_id": f"usr_{_random_hex(8)}",
                "action": action,
                "metadata": metadata,
                "session_id": f"sess_{_random_hex(8)}",
                "timestamp": datetime.now(timezone.utc),
            })
        db.user_activity.insert_many(activities)
        counts["user_activity"] = n_activity

        client.close()
        return counts

    return await asyncio.get_event_loop().run_in_executor(None, _run)


# ── SeaweedFS ─────────────────────────────────────────────────────────────────

async def write_seaweedfs() -> dict:
    def _run():
        s3 = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "any"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "any"),
            region_name="us-east-1",
        )
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"reports/daily-summary-{today}.csv"

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["metric", "value", "timestamp"])
        writer.writerow(["total_customers", random.randint(100, 10000), today])
        writer.writerow(["total_orders", random.randint(500, 50000), today])
        writer.writerow(["revenue_brl", round(random.uniform(10000, 1000000), 2), today])
        writer.writerow(["failed_pipelines", random.randint(0, 3), today])

        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=buf.getvalue().encode())
        return {"reports": 1, "key": key}

    return await asyncio.get_event_loop().run_in_executor(None, _run)


# ── Main loop ─────────────────────────────────────────────────────────────────

async def run_cycle(cycle: int):
    tasks = [
        _retry(lambda: write_postgres(cycle), "postgres"),
        _retry(lambda: write_mongo(), "mongo"),
    ]
    if cycle % 10 == 0:
        tasks.append(_retry(lambda: write_seaweedfs(), "seaweedfs"))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    pg_result = results[0] if not isinstance(results[0], Exception) else {}
    mg_result = results[1] if not isinstance(results[1], Exception) else {}
    sw_result = results[2] if len(results) > 2 and not isinstance(results[2], Exception) else {}

    log.info(
        "cycle=%d postgres=%s mongo=%s%s",
        cycle,
        json.dumps(pg_result),
        json.dumps(mg_result),
        f" seaweedfs={json.dumps(sw_result)}" if sw_result else "",
    )


async def main():
    log.info("Data generator starting — interval=%ds", INTERVAL)
    cycle = 0
    while not _shutdown:
        cycle += 1
        try:
            await run_cycle(cycle)
        except Exception as exc:
            log.error("cycle=%d unhandled error: %s", cycle, exc)
        if not _shutdown:
            await asyncio.sleep(INTERVAL)
    log.info("Generator stopped cleanly after %d cycles", cycle)


if __name__ == "__main__":
    asyncio.run(main())
