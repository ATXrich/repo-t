import sys
import json
import subprocess
import re
from typing import List
import boto3
from boto3.dynamodb.conditions import Key
from botocore import endpoint

TABLE_NAME = 'Repo_T_Execution_History'
format = '\'{"commit": "%h", "date": "%ad", "subject": "%s", "body": "%b", "author": {"name": "%an", "email": "%aE"}}\''


def parse_git_logs(build_number: str) -> str:
    """Checks for new git commits in last 24 hours for given branch and developer(s). 
       Formats output and uploads to dynamodb table."""

    payload = []

    branch_name = get_value_from_dynamodb(build_number, 'branch_name')
    developers = get_value_from_dynamodb(build_number, 'developers')
    for developer in developers:
        # capture git commits 24 hours ago for given developer and branch
        process = subprocess.run(
            f'git log -n 2 --author={developer} --since="24 hours ago" --format={format} {branch_name}', 
            shell=True, capture_output=True, text=True)

        git_logs = process.stdout.splitlines()
        
        print(f'Retrieved {len(git_logs)} commits in last 24 hours for {developer} on branch {branch_name}.')

        # build payload for dynamodb
        if len(git_logs) > 0:
            for git_log in git_logs:
                dynamodb_item = build_dynamodb_item(json.loads(git_log))
                payload.append(dynamodb_item)

    # upload git logs to dynamodb
    if len(payload) > 0:
        response = update_dynamodb(payload, build_number)
    else:
        response = f'{TABLE_NAME} table update not required.'
    return response


def get_value_from_dynamodb(build_number: str, attribute: str):
    """Returns value for a given dynamodb item attribute"""

    try:
        dynamo_db = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')  # region_name='us-east-2')
        table = dynamo_db.Table(TABLE_NAME)

        response = table.get_item(
            Key={
                "build_number": build_number
            }
        )
        attribute = response['Item'][attribute]
        if len(attribute) > 0:
            return attribute
        else:
            print(f'{attribute} not found for build: {build_number}')
            exit(1)
    except Exception as e:
        print(f'error fetching data from dynamodb: {e}')
        exit(1)


def build_dynamodb_item(git_log: dict) -> dict:
    """Adds additional attributes to git log before updating dynamodb table item"""

    # add Jira ID to log
    git_log['jira_id'] = search_git_log(r'([a-zA-Z]+-\d+)', git_log['subject']).upper()
      
    # capture changed files and add to log
    git_log['filenames'] = get_filenames(git_log['commit'])

    return git_log


def get_filenames(commit: str) -> List:
    """Returns list of changed files in git commit"""

    process = subprocess.run(
        [f'git show --pretty="format:" --name-only {commit}'], 
        shell=True, capture_output=True, text=True)
    filenames = process.stdout.splitlines()
    return filenames


def search_git_log(regex: str, output: str) -> str:
    """Searches string with specified regex"""

    try:
        result = re.search(regex, output).group(1)
        return result
    except AttributeError:
        return ''


def update_dynamodb(payload: str, build_number: str) -> str:
    """Writes payload to dynamodb table."""

    dynamodb = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")
    try:
        table = dynamodb.Table(TABLE_NAME)
        response = table.update_item(
            Key={
                'build_number': build_number
            },
            UpdateExpression="SET git_logs=:g",
            ExpressionAttributeValues={
                ':g': payload
            },
            ReturnValues="UPDATED_NEW"
        )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return f'{TABLE_NAME} table updated with most recent logs.'
        return f"error updating dynamadb: Status Code {response['ResponseMetadata']['HTTPStatusCode']}"
    except Exception as e:
        return f'error updating dynamadb: {e}'


if __name__ == '__main__':
    if len(sys.argv) > 1:
        response = parse_git_logs(str(sys.argv[1]))
        print(response)
    else:
        print('error: missing build_number (eg. \"$ python parse_repo.py 10.07.00.000000-20210805.015637\")')
        exit(1)
