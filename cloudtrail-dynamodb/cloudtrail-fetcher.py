import boto3
import json
from datetime import datetime, timezone

client = boto3.client('cloudtrail')
start_time = datetime(2025, 8, 1, tzinfo=timezone.utc)
end_time = datetime(2025, 9, 10, tzinfo=timezone.utc)

def extract_resource_id(event_name, response_elements, request_parameters):
    """Extract resource ID(s) from CloudTrail responseElements depending on event type."""
    if not response_elements:
        return []

    try:
        if event_name == "RunInstances":
            items = response_elements.get("instancesSet", {}).get("items") or \
                    response_elements.get("InstancesSet", {}).get("items")
            return [i.get("instanceId") for i in items] if items else []

        elif event_name == "StartInstances":
            items = response_elements.get("instancesSet", {}).get("items") or \
                    response_elements.get("InstancesSet", {}).get("items")
            return [i.get("instanceId") for i in items] if items else []

        elif event_name == "StopInstances":
            items = response_elements.get("instancesSet", {}).get("items") or \
                    response_elements.get("InstancesSet", {}).get("items")
            return [i.get("instanceId") for i in items] if items else []

        elif event_name == "TerminateInstances":
            items = response_elements.get("instancesSet", {}).get("items") or \
                    response_elements.get("InstancesSet", {}).get("items")
            return [i.get("instanceId") for i in items] if items else []

        elif event_name == "AllocateAddress":
            return [response_elements.get("allocationId")] if response_elements.get("allocationId") else []

        elif event_name == "ReleaseAddress":
            return [request_parameters.get("allocationId")] if request_parameters.get("allocationId") else []

        elif event_name == "CreateImage":
            return [response_elements.get("imageId")] if response_elements.get("imageId") else []

        elif event_name == "CreateSnapshot":
            return [response_elements.get("snapshotId")] if response_elements.get("snapshotId") else []

        elif event_name == "DeleteSnapshot":
            return [response_elements.get("snapshotId")] if response_elements.get("snapshotId") else []

        elif event_name == "CreateSnapshots":
            return [snap.get("snapshotId") for snap in response_elements.get("snapshots", []) if snap.get("snapshotId")]

        elif event_name == "CreateInternetGateway":
            igw = response_elements.get("internetGateway") or response_elements.get("InternetGateway")
            return [igw.get("internetGatewayId")] if igw and igw.get("internetGatewayId") else []

        elif event_name == "DeleteNatGateway":
            nat_gateway = (
                response_elements.get("DeleteNatGatewayResponse", {})
                .get("natGatewayId")
            )
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
            nat_gateway = (
                response_elements.get("CreateNatGatewayResponse", {})
                .get("natGateway", {})
            )
            return [nat_gateway.get("natGatewayId")] if nat_gateway.get("natGatewayId") else []

        elif event_name == "CreateStoreImageTask":
            return [response_elements.get("objectKey")] if response_elements.get("objectKey") else []

        elif event_name == "DeleteFleets":
            return [fleet.get("fleetId") for fleet in response_elements.get("successfulFleetDeletionSet", []) if fleet.get("fleetId")]

    except Exception as e:
        print(f"⚠️ Could not extract resource ID for {event_name}: {e}")

    return []

event_names = [
    "RunInstances",
    "StartInstances",
    "StopInstances",
    "TerminateInstances",
    "AllocateAddress",
    "ReleaseAddress",
    "CreateImage",
    "CreateSnapshot",
    "DeleteSnapshot",
    "CreateSnapshots",
    "CreateInternetGateway",
    "DeleteNatGateway",
    "CreateFlowLogs",
    "CreateFleet",
    "RequestSpotFleet",
    "RequestSpotInstances",
    "CreateNatGateway",
    "DeleteNatGateway"
    "CreateStoreImageTask",
    "DeleteFleets"
]


for event_name in event_names:
    response = client.lookup_events(
        LookupAttributes=[
            {
                'AttributeKey': 'EventName',
                'AttributeValue': event_name
            }
        ],
        MaxResults=50,
        StartTime=start_time,
        EndTime=end_time
    )

    #Prints raw cloudtrail data
    
    # print(f"Events for {event_name}:")
    # for event in response["Events"]:
    #     event_data = json.loads(event["CloudTrailEvent"])
    #     print(json.dumps(event_data, indent=2))
    # print("-" * 40)
    
    print(f"Events for {event_name}:")
    for event in response["Events"]:
        event_data = json.loads(event["CloudTrailEvent"])
        
        if event_data.get("errorCode") or event_data.get("errorMessage"):
            continue
        
        user_identity = event_data.get("userIdentity", {})
        session_context = user_identity.get("sessionContext", {})
        creation_date = session_context.get("creationDate")
        output = {
            "eventID": event_data.get("eventID"),                     
            "principalId": user_identity.get("principalId"),
            "accountId": user_identity.get("accountId"),
            "eventTime": event_data.get("eventTime"),
            "eventSource": event_data.get("eventSource"),
            "eventName": event_data.get("eventName"),
            "awsRegion": event_data.get("awsRegion"),
            "resourceIds": extract_resource_id(event_data.get("eventName"), event_data.get("responseElements"), event_data.get("requestParameters"))
        }
        print(json.dumps(output, indent=2))
    print("-" * 40)