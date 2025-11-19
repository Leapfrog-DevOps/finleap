import boto3
import json
from datetime import datetime, timedelta

def lambda_handler(event, context):
    ce = boto3.client('ce')
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=1)
    
    response = ce.get_cost_and_usage(
        TimePeriod={
            'Start': start_date.strftime('%Y-%m-%d'),
            'End': end_date.strftime('%Y-%m-%d')
        },
        Granularity='DAILY',
        Metrics=['BlendedCost', 'UnblendedCost', 'UsageQuantity'],
        GroupBy=[
            {'Type': 'DIMENSION', 'Key': 'SERVICE'},
            {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}
        ]
    )
    
    detailed_costs = []
    for result in response['ResultsByTime']:
        for group in result['Groups']:
            cost_data = {
                'date': result['TimePeriod']['Start'],
                'service': group['Keys'][0],
                'usage_type': group['Keys'][1],
                'blended_cost': group['Metrics']['BlendedCost']['Amount'],
                'unblended_cost': group['Metrics']['UnblendedCost']['Amount'],
                'usage_quantity': group['Metrics']['UsageQuantity']['Amount'],
                'unit': group['Metrics']['BlendedCost']['Unit']
            }
            detailed_costs.append(cost_data)
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps({
            'detailed_costs': detailed_costs,
            'raw_response': response
        })
    }
