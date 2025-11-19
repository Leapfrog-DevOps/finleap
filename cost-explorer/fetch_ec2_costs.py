import boto3
import json
import re
import pymysql
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import time

load_dotenv()

# --- Configuration ---
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
INSTANCE_ID_PATTERN = re.compile(r"^i-[0-9a-f]+$")
DAYS_BACK = int(os.getenv("DAYS_BACK", "1"))

# --- MySQL Connection ---
def get_db_connection():
    """Establish MySQL connection using .env vars."""
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        connect_timeout=10
    )

# --- Fetch EC2 cost data from AWS Cost Explorer ---
def fetch_ec2_costs(start_date, end_date, retries=3, delay=5):
    """Fetch EC2 cost data from AWS Cost Explorer with retry on data unavailability."""
    ce = boto3.client("ce", region_name=AWS_REGION)
    for attempt in range(retries):
        try:
            response = ce.get_cost_and_usage_with_resources(
                TimePeriod={"Start": start_date, "End": end_date},
                Granularity="DAILY",
                Metrics=["UnblendedCost", "UsageQuantity"],
                Filter={
                    "Dimensions": {
                        "Key": "SERVICE",
                        "Values": ["Amazon Elastic Compute Cloud - Compute"]
                    }
                },
                GroupBy=[
                    {"Type": "DIMENSION", "Key": "RESOURCE_ID"},
                    {"Type": "DIMENSION", "Key": "INSTANCE_TYPE"}
                ]
            )
            break
        except ce.exceptions.DataUnavailableException:
            print(f"Cost data not available yet (attempt {attempt+1}/{retries}), retrying in {delay}s...")
            time.sleep(delay)
    else:
        print("Failed to fetch data: cost data not available.")
        return []

    results = []
    for day in response["ResultsByTime"]:
        raw_date = day["TimePeriod"]["Start"]
        clean_date = raw_date.split("T")[0]

        for group in day.get("Groups", []):
            resource_id, instance_type = group["Keys"]
            if not INSTANCE_ID_PATTERN.match(resource_id):
                continue

            cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
            usage = float(group["Metrics"]["UsageQuantity"]["Amount"])
            results.append({
                "date": clean_date,
                "instance_id": resource_id,
                "instance_type": instance_type or "Unknown",
                "cost_usd": round(cost, 4),
                "usage_hours": round(usage, 2)
            })

    return results

# --- Insert or update into MySQL ---
def upsert_cost_data(records):
    """Insert or update EC2 cost records into MySQL."""
    if not records:
        print("No records to insert.")
        return

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ec2_costs (
                date DATE NOT NULL,
                instance_id VARCHAR(32) NOT NULL,
                instance_type VARCHAR(64),
                cost_usd DECIMAL(10,4),
                usage_hours DECIMAL(10,2),
                PRIMARY KEY (date, instance_id)
            );
        """)
        conn.commit()

        for record in records:
            cursor.execute("""
                INSERT INTO ec2_costs (date, instance_id, instance_type, cost_usd, usage_hours)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    instance_type = VALUES(instance_type),
                    cost_usd = VALUES(cost_usd),
                    usage_hours = VALUES(usage_hours);
            """, (
                record["date"],
                record["instance_id"],
                record["instance_type"],
                record["cost_usd"],
                record["usage_hours"]
            ))
        conn.commit()

    conn.close()
    print(f"Inserted/Updated {len(records)} records in MySQL.")

# --- Main execution ---
if __name__ == "__main__":
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=DAYS_BACK)
    print(f"Fetching EC2 cost data from {start_date} to {end_date} for last {DAYS_BACK} days...")

    records = fetch_ec2_costs(str(start_date), str(end_date))

    if not records:
        print("No EC2 cost data found for this period.")
    else:
        upsert_cost_data(records)
        print("Done!")
