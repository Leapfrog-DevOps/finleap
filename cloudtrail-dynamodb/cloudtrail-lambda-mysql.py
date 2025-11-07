import boto3
import json
import pymysql
import os
from datetime import datetime, timezone

# --- CloudTrail client ---
cloudtrail = boto3.client('cloudtrail')

# --- MySQL connection details (stored as Lambda environment variables) ---
DB_HOST = os.environ['DB_HOST']
DB_USER = os.environ['DB_USER']
DB_PASS = os.environ['DB_PASS']
DB_NAME = os.environ['DB_NAME']

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def extract_resource_id(event_name, response_elements, request_parameters):
    if not response_elements:
        return []
    try:
        if event_name in ["RunInstances", "StartInstances", "StopInstances", "TerminateInstances"]:
            items = response_elements.get("instancesSet", {}).get("items") or \
                    response_elements.get("InstancesSet", {}).get("items")
            return [i.get("instanceId") for i in items] if items else []

        elif event_name == "AllocateAddress":
            return [response_elements.get("allocationId")] if response_elements.get("allocationId") else []

        elif event_name == "ReleaseAddress":
            return [request_parameters.get("allocationId")] if request_parameters.get("allocationId") else []

        elif event_name == "CreateImage":
            return [response_elements.get("imageId")] if response_elements.get("imageId") else []

        elif event_name in ["CreateSnapshot", "DeleteSnapshot"]:
            return [response_elements.get("snapshotId")] if response_elements.get("snapshotId") else []

        elif event_name == "CreateSnapshots":
            return [snap.get("snapshotId") for snap in response_elements.get("snapshots", []) if snap.get("snapshotId")]

        elif event_name == "CreateInternetGateway":
            igw = response_elements.get("internetGateway") or response_elements.get("InternetGateway")
            return [igw.get("internetGatewayId")] if igw and igw.get("internetGatewayId") else []

        elif event_name == "DeleteNatGateway":
            nat_gateway = response_elements.get("DeleteNatGatewayResponse", {}).get("natGatewayId")
            return [nat_gateway] if nat_gateway else []

        elif event_name == "CreateFlowLogs":
            return response_elements.get("flowLogIds", [])

        elif event_name == "CreateFleet":
            return [response_elements.get("fleetId")] if response_elements.get("fleetId") else []

        elif event_name == "RequestSpotFleet":
            return [response_elements.get("spotFleetRequestId")] if response_elements.get("spotFleetRequestId") else []

        elif event_name == "RequestSpotInstances":
            return [i.get("spotInstanceRequestId") for i in response_elements.get("spotInstanceRequests", []) if i.get("spotInstanceRequestId")]

        elif event_name == "CreateNatGateway":
            nat_gateway = response_elements.get("CreateNatGatewayResponse", {}).get("natGateway", {})
            return [nat_gateway.get("natGatewayId")] if nat_gateway.get("natGatewayId") else []

        elif event_name == "CreateStoreImageTask":
            return [response_elements.get("objectKey")] if response_elements.get("objectKey") else []

        elif event_name == "DeleteFleets":
            return [fleet.get("fleetId") for fleet in response_elements.get("successfulFleetDeletionSet", []) if fleet.get("fleetId")]

    except Exception as e:
        print(f"⚠️ Could not extract resource ID for {event_name}: {e}")
    return []


event_names = [
    "RunInstances", "StartInstances", "StopInstances", "TerminateInstances",
    "AllocateAddress", "ReleaseAddress", "CreateImage", "CreateSnapshot",
    "DeleteSnapshot", "CreateSnapshots", "CreateInternetGateway",
    "DeleteNatGateway", "CreateFlowLogs", "CreateFleet", "RequestSpotFleet",
    "RequestSpotInstances", "CreateNatGateway", "CreateStoreImageTask",
    "DeleteFleets"
]


def lambda_handler(event, context):
    start_time = datetime(2025, 9, 1, tzinfo=timezone.utc)
    end_time = datetime(2025, 9, 30, tzinfo=timezone.utc)

    inserted = 0
    connection = get_db_connection()
    
    try:
        with connection.cursor() as cursor:
            for event_name in event_names:
                response = cloudtrail.lookup_events(
                    LookupAttributes=[{'AttributeKey': 'EventName', 'AttributeValue': event_name}],
                    MaxResults=50,
                    StartTime=start_time,
                    EndTime=end_time
                )

                for evt in response["Events"]:
                    event_data = json.loads(evt["CloudTrailEvent"])
                    if event_data.get("errorCode") or event_data.get("errorMessage"):
                        continue

                    user_identity = event_data.get("userIdentity", {})
                    event_time_raw = event_data.get("eventTime")
                    event_time = None
                    if event_time_raw:
                        try:
                            # Converts ISO8601 -> Python datetime (MySQL-compatible)
                            event_time = datetime.fromisoformat(event_time_raw.replace("Z", "+00:00"))
                        except Exception:
                            event_time = None
                    record = {
                        "eventID": event_data.get("eventID"),
                        "accountId": str(user_identity.get("accountId", "unknown")),
                        "eventTime": event_time,
                        "principalId": user_identity.get("principalId"),
                        "eventSource": event_data.get("eventSource"),
                        "eventName": event_data.get("eventName"),
                        "awsRegion": event_data.get("awsRegion"),
                        "resourceIds": json.dumps(extract_resource_id(
                            event_data.get("eventName"),
                            event_data.get("responseElements"),
                            event_data.get("requestParameters")
                        ))
                    }

                    sql = """
                        INSERT IGNORE INTO cloudtrail_events (
                            eventID, accountId, eventTime, principalId, eventSource,
                            eventName, awsRegion, resourceIds
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE
                            accountId=VALUES(accountId),
                            eventTime=VALUES(eventTime),
                            principalId=VALUES(principalId),
                            eventSource=VALUES(eventSource),
                            eventName=VALUES(eventName),
                            awsRegion=VALUES(awsRegion),
                            resourceIds=VALUES(resourceIds);
                    """
                    cursor.execute(sql, (
                        record["eventID"], record["accountId"], record["eventTime"],
                        record["principalId"], record["eventSource"], record["eventName"],
                        record["awsRegion"], record["resourceIds"]
                    ))
                    inserted += 1

            connection.commit()
    finally:
        connection.close()

    return {
        "statusCode": 200,
        "body": json.dumps({"inserted_records": inserted})
    }