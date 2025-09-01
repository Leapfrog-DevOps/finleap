# AWS CloudTrail → DynamoDB Aggregator 

This module provides an AWS Lambda function that **ingests CloudTrail logs from S3** via S3 triggers and writes them into a DynamoDB table.  
The table acts as an **aggregation layer** for downstream analytics.

---

## 📌 Features
- Triggered automatically when new CloudTrail logs are written to an S3 bucket.
- Decompresses and parses CloudTrail log files (`.gz` JSON format).
- Inserts each CloudTrail event into DynamoDB for downstream processing.
- Supports **KMS-encrypted S3 buckets**.
- DynamoDB table configured with:
  - **Partition key**: `eventId`
  - **Sort key**: `eventTime`

---

## 🏗️ Architecture
- **CloudTrail** delivers logs to an S3 bucket.
- **S3 Event Notification** triggers the Lambda on new object creation.
- **Lambda**:
  - lambda-s3-dynamodb.py
  - Reads + decompresses CloudTrail logs.
  - Pushes each record into DynamoDB.
- **DynamoDB** stores events temporarily (can use TTL to auto-expire).

---

## 📜 IAM Role for Lambda
- lambda-role.json
- Permissions:
  - Read from S3 bucket (GetObject).
  - Write to DynamoDB table (PutItem).
  - KMS decrypt if S3 bucket is encrypted.


