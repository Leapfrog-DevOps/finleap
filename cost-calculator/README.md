# Cost Calculator API

Calculate EC2 instance costs by principalId from CloudTrail events.

## Setup

1. Copy `.env.example` to `.env` and configure your MySQL database settings
2. Install dependencies: `go mod tidy`
3. Run the application: `go run cmd/main.go`

## API Endpoints

- `GET /api/v1/costs/principals` - Get all principal costsls

- `GET /api/v1/costs/principals/:id` - Get specific principal cost by ID
- `GET /api/v1/instances` - Get all EC2 instance costs

## Example Response

```json
[
  {
    "principal_id": "AROA52BEGI3BHMK4NYVCU:ankitkarna@lftechnology.com",
    "total_cost": 125.75,
    "total_hours": 240.0,
    "instances": 3
  }
]
```

## How it works

The API joins `cloudtrail_events` and `ec2_costs` tables where:
- CloudTrail events contain `resourceIds` as JSON array with instance IDs
- EC2 costs contain actual cost and usage data per instance
- Costs are calculated per `principalId` who created/managed the resources