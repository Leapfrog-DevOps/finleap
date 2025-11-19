# FinLeap – AWS FinOps Tool

**FinLeap** is a FinOps tool designed to help teams gain visibility into their AWS usage and costs.  
It provides a unified way to collect, process, and analyze **CloudTrail logs, cost data, and service usage**, giving you actionable insights per **user, service, region, and account**.

# Finleap Cloud Cost Attribution

Serviceto attribute AWS cloud costs to individual users by correlating Cost Explorer cost data with CloudTrail user activity.

## Overview

- Ingestion 1: Cost Data  
  - AWS Lambda invokes the Cost Explorer API daily to pull detailed resource cost data and writes results to a relational database.
- Ingestion 2: CloudTrail Activity  
  - AWS Lambda queries CloudTrail events, filters for API calls that create or modify billable resources, parses resource IDs and the caller identity, and stores activity records in the database.
- Backend: Go (Golang) service correlates Cost Explorer rows with CloudTrail activity to attribute cost to IAM principals.
- Frontend: React UI for visualization and analysis.
- Database: MySQL (local dev can use SQLite as fallback).

## Features

- Attribute cloud spend to individual users/principals
- Correlate Cost Explorer cost lines with CloudTrail-created resources
- Filter out failed API events (skip if `errorCode` / `errorMessage` present)
- Extensible resource ID parser for many EC2/EBS/VPC related events
- Intuitive UI for financial analysis and quick drill-down

## Architecture (high level)

1. Daily Lambda (Cost) -> Cost Explorer -> DB (cost rows)
2. Periodic Lambda (CloudTrail) -> lookup_events or S3 logs -> parse events -> DB (activity rows)
3. Backend (Go) -> correlates costs <-> activities, serves APIs for frontend
4. Frontend (React) -> queries backend for dashboards and reports


## Getting started (local dev)

1. Prereqs
   - Go (version compatible with `go.mod`)
   - Node.js & npm/yarn for frontend
   - MySQL server (or use SQLite for local testing)
   - AWS CLI configured for credentials and default region

2. Configure environment variables (example)
   - DATABASE_URL=mysql://user:pass@tcp(localhost:3306)/finleap
   - AWS_REGION=us-east-1
   - LOG_LEVEL=info
   - (Lambda-specific) COST_LAMBDA_SCHEDULE, CLOUDTRAIL_LAMBDA_SCHEDULE

3. Run backend
   - Build: `go build ./...` (from /backend)
   - Run: `DATABASE_URL=... ./backend` or use `go run ./cmd/server`

4. Run frontend
   - `cd frontend` && `npm install` && `npm start`

5. Local DB (optional)
   - Use migrations in /migrations to create tables. For quick tests, a SQLite file can be used (repository already includes sqlite dependency for dev/test).

## AWS IAM permissions (minimum)

Lambdas / service roles require:
- Cost Explorer
  - `ce:GetCostAndUsage`
  - `ce:GetCostAndUsageWithResources`
  - `ce:GetCostForecast` (optional)
- CloudTrail
  - `cloudtrail:LookupEvents`
  - If reading S3-delivered logs: `s3:GetObject`, `s3:ListBucket`
- EC2 (read metadata)
  - `ec2:DescribeInstances`, `ec2:DescribeImages`, `ec2:DescribeSnapshots`, etc. (optional for enrichment)
- RDS / Secrets Manager (if storing DB credentials there)
- CloudWatch Logs (for Lambda logging)

Adjust policy to least privilege for each Lambda and the backend.

## Event parsing notes

- CloudTrail events contain `CloudTrailEvent` as a JSON string; code should `json.loads(event["CloudTrailEvent"])` (or equivalent) to parse.
- Skip events where `errorCode` or `errorMessage` are present — those indicate the API call failed and the resource was not created.
- Response structures vary by service and API version. Implement a robust `extract_resource_id(eventName, responseElements)` helper that:
  - Handles nested wrappers (eg: `CreateNatGatewayResponse.natGateway.natGatewayId`)
  - Accepts multiple casing/field-name variants (`instancesSet` vs `InstancesSet`)
  - Returns a list (0..N) of resource IDs for correlation
  - Current Scope involves manual manipulation of API calls & response

## Correlation strategy

- For each cost line (Cost Explorer), try to match by resource id via Cloudtrail logs (instanceId, snapshotId, AMI id, fleetId, natGatewayId, allocationId, etc.)
- If resource id not present, use heuristic enrichment (tags, account, region, time-window proximity)
- Store correlation 

## Deployment

- Current Deployment involves Lambda with EC2 hosting the DB & backend.


## Troubleshooting

- No resource id found — add more event samples with API calls, response structures and update extractor paths.
- Cost lines not matching — check timezone/aggregation, charge type, and whether Cost Explorer returns resource IDs for that service/charge.
- Missing CloudTrail events — ensure lookup window includes the creation time and that CloudTrail logging is enabled for management events.

---


