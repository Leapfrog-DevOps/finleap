# AWS CloudTrail → DynamoDB Aggregator 

This module  **ingests CloudTrail logs from Cloudtrail API**  and writes them into a DynamoDB table.  
The table acts as an **aggregation layer** for downstream analytics.

---

## 📌 Services
-  "RunInstances",
-  "StartInstances",
-  "StopInstances",
-  "TerminateInstances",
-  "AllocateAddress",
-  "ReleaseAddress",
-  "CreateImage",
-  "CreateSnapshot",
-  "DeleteSnapshot",
-  "CreateSnapshots",
-  "CreateInternetGateway",
-  "DeleteNatGateway",
-  "CreateFlowLogs",
-  "CreateFleet",
-  "RequestSpotFleet",
-  "RequestSpotInstances",
-  "CreateNatGateway",
-  "DeleteNatGateway"
-  "CreateStoreImageTask",
-  "DeleteFleets"

## DynamoDB Keys
  - **Partition key**: `eventId`
  - **Sort key**: `eventTime`

---

## 🏗️ Architecture
- **CloudTrail** API allows logs to be pulled for the past 90 days
- **Lambda** reads the logs with one eventAPI at a time in loop with predefined JSON structures for resourceids
- **DynamoDB** stores events temporarily (can use TTL to auto-expire).

---

## 📜 IAM Role for Lambda
- lambda-role.json
- Permissions:
  - Write to DynamoDB table (PutItem).
  - Read from Cloudtrail (lookupevents)


