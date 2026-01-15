import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm = boto3.client('ssm')
PARA_NAME = os.environ['SSM_PARAM_NAME']

def get_parameter(para_name):
    parameter = ssm.get_parameter(Name=para_name)
    env = parameter['Parameter']['Value'].strip().lower()
    value = 0
    if env == 'development':
        value = 1
    elif env in ['staging', 'production']:
        value = 2
    else:
        raise ValueError(f'Invalid environment {env} in SSM Parameter {para_name}')
    
    logger.info(f"Computed replicaCount={value} for env={env}")
    
    return {
        'Environment' : env,
        'ReplicaCount' : value
    }

def lambda_handler(event, context):

    if event.get("RequestType") == "Delete":
        return {
            "PhysicalResourceId": event.get("PhysicalResourceId", "env"),
            "Data": {}
        }

    para_name = os.environ['SSM_PARAM_NAME']
    data = get_parameter(para_name)
    return {
        'PhysicalResourceId': f"{para_name}:{data['Environment']}",
        'Data': data
    }
        
