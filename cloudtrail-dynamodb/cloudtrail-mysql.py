import boto3
import json
import pymysql
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()

# --- MySQL connection details ---
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_NAME = os.getenv('DB_NAME')

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

def get_all_regions():
    ec2 = boto3.client('ec2', region_name='us-east-1')
    return [r['RegionName'] for r in ec2.describe_regions()['Regions']]

def extract_username_from_event(user_identity):
    """
    Best-effort username extraction from CloudTrail userIdentity.
    Returns a string username or None.
    Tries common locations: userName, sessionContext.sessionIssuer.userName, ARN parsing.
    """
    if not user_identity:
        return None

    # 1) direct userName field
    username = user_identity.get("userName")
    if username:
        return username

    # 2) session issuer (commonly present for assumed roles / SSO sessionIssuer)
    session_ctx = user_identity.get("sessionContext", {})
    session_issuer = session_ctx.get("sessionIssuer", {})
    su_name = session_issuer.get("userName")
    if su_name:
        return su_name

    # 3) If arn exists, try to parse a name from the arn (last path component)
    arn = user_identity.get("arn")
    if arn and ":" in arn:
        # ARN examples:
        # arn:aws:iam::123456789012:user/johndoe
        # arn:aws:sts::123456789012:assumed-role/RoleName/session-name
        try:
            parts = arn.split(":")[-1]  # e.g., 'user/johndoe' or 'assumed-role/RoleName/session-name'
            # take last component after '/'
            name = parts.split("/")[-1]
            # filter out account IDs or obviously numeric names
            if name and not name.isdigit():
                return name
        except Exception:
            pass

    # 4) principals for federated identities sometimes have principalId like "ABCDEFG:john@example.com"
    principal_id = user_identity.get("principalId")
    if principal_id and ":" in principal_id:
        possible = principal_id.split(":", 1)[1]
        if possible:
            return possible

    return None

def sync_cloudtrail_to_db():
    start_time = datetime(2025, 10, 1, tzinfo=timezone.utc)
    end_time = datetime(2025, 11, 2, tzinfo=timezone.utc)
    inserted = 0

    regions = get_all_regions()
    print(f"🌍 Found {len(regions)} AWS regions to scan.")

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            for region in regions:
                print(f"🔎 Querying CloudTrail in region: {region}")
                cloudtrail = boto3.client('cloudtrail', region_name=region)

                for event_name in event_names:
                    try:
                        response = cloudtrail.lookup_events(
                            LookupAttributes=[{'AttributeKey': 'EventName', 'AttributeValue': event_name}],
                            MaxResults=50,
                            StartTime=start_time,
                            EndTime=end_time
                        )
                    except Exception as e:
                        print(f"⚠️ Skipping region {region} ({event_name}): {e}")
                        continue

                    for evt in response.get("Events", []):
                        event_data = json.loads(evt["CloudTrailEvent"])
                        if event_data.get("errorCode") or event_data.get("errorMessage"):
                            continue

                        user_identity = event_data.get("userIdentity", {})
                        event_time_raw = event_data.get("eventTime")
                        event_time = None
                        if event_time_raw:
                            try:
                                event_time = datetime.fromisoformat(event_time_raw.replace("Z", "+00:00"))
                            except Exception:
                                event_time = None

                        # New: best-effort username extraction
                        user_name = extract_username_from_event(user_identity)

                        record = {
                            "eventID": event_data.get("eventID"),
                            "accountId": str(user_identity.get("accountId", "unknown")),
                            "eventTime": event_time,
                            "principalId": user_identity.get("principalId"),
                            "userName": user_name,
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
                                eventID, accountId, eventTime, principalId, userName, eventSource,
                                eventName, awsRegion, resourceIds
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            ON DUPLICATE KEY UPDATE
                                accountId=VALUES(accountId),
                                eventTime=VALUES(eventTime),
                                principalId=VALUES(principalId),
                                userName=VALUES(userName),
                                eventSource=VALUES(eventSource),
                                eventName=VALUES(eventName),
                                awsRegion=VALUES(awsRegion),
                                resourceIds=VALUES(resourceIds);
                        """
                        cursor.execute(sql, (
                            record["eventID"], record["accountId"], record["eventTime"],
                            record["principalId"], record["userName"], record["eventSource"],
                            record["eventName"], record["awsRegion"], record["resourceIds"]
                        ))
                        inserted += 1

            connection.commit()
    finally:
        connection.close()

    print(f"✅ Inserted/updated {inserted} records across all AWS regions.")

if __name__ == "__main__":
    print("=== Running CloudTrail → MySQL Sync (All Regions) ===")
    sync_cloudtrail_to_db()