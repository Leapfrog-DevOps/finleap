import boto3
import gzip
import json
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["DDB_TABLE_NAME"])
s3 = boto3.client('s3')

def lambda_handler(event, context):
    # Get S3 bucket and object key from the event
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        # Download and decompress the log file
        response = s3.get_object(Bucket=bucket, Key=key)
        with gzip.GzipFile(fileobj=response['Body']) as gz:
            log_data = json.loads(gz.read().decode('utf-8'))
        
        # Insert each CloudTrail record into DynamoDB
        for item in log_data.get('Records', []):
            # You may want to customize the key schema here
            table.put_item(Item=item)
    
    return {'statusCode': 200, 'body': 'Success'}