from datetime import datetime
from pytz import timezone
import json
import boto3
import os

_eastern_timezone = timezone('Canada/Eastern')

def lambda_handler(event, context):
    message = json.loads(event['Records'][0]['Sns']['Message'])
    message_detail = message['detail']
    pipeline_state = message_detail['state']
    pipeline_name = message_detail['pipeline']
    execution_id = message_detail['execution-id']
    deployment_time = datetime.strptime(message['time'], '%Y-%m-%dT%H:%M:%SZ')
    local_deployment_time = _eastern_timezone.fromutc(deployment_time)
    local_deployment_time = datetime.strftime(local_deployment_time, '%Y-%m-%d %I:%M:%S %p')

    notification_subject = ""
    notification_body = ""

    if pipeline_state == "SUCCEEDED":
        notification_subject = f'AWS Deployment Successful - {pipeline_name} - {local_deployment_time}'
        notification_body = "The deployment completed successfully"
    elif pipeline_state == "FAILED":
        notification_subject = f'AWS Deployment Failed - {pipeline_name} - {local_deployment_time}'

        client = boto3.client('codepipeline')
        action_executions = client.list_action_executions(
            pipelineName = pipeline_name,
            filter = {
                'pipelineExecutionId': execution_id
            }
        )

        notification_body += f'''Errors occurred during the deployment:
---------------------------------------------------------------
'''

        failed_executions = [x for x in action_executions['actionExecutionDetails'] if x['status'] == 'Failed']
        for failed_execution in failed_executions:
            if 'externalExecutionSummary' in failed_execution['output']['executionResult']:
                error_message = failed_execution['output']['executionResult']['externalExecutionSummary']
            else:
                error_message = "An error occurred.  See CodePipeline in AWS console for more details."                    

            notification_body += f'''
Stage: {failed_execution["stageName"]}
Action: {failed_execution["actionName"]}
Error: {error_message}
---------------------------------------------------------------
'''
    else:
        notification_subject = f'AWS Deployment Completed - {pipeline_name} - {local_deployment_time}'
        notification_body = f'A deployment completed with state {pipeline_state}. See CodePipeline in AWS console for more details.'

    print('Subject: ' + notification_subject)
    print('Body: ' + notification_body)

    snsTopic = os.environ['CustomizedNotificationTopicArn']
    sns = boto3.client('sns')

    sns.publish(
        TopicArn=snsTopic,
        Subject=notification_subject,
        Message=notification_body
    )

    return