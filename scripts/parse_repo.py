import sys
import json
import subprocess
import re
from typing import List
import boto3
from boto3.dynamodb.conditions import Key
from botocore import endpoint

TABLE_NAME = 'Repo_T_Execution_History'
BUILD_NUMBER = ""
payload = []
format = '\'{"commit": "%h", "date": "%ad", "subject": "%s", "body": "%b", "author": {"name": "%an", "email": "%aE"}}\''



def parse_git_logs():
    """Checks for new git commits in last 24 hours for given developer(s). Formats output and uploads to dynamodb table."""

    # obtain developer names for build
    developers = get_developers_from_dynamodb()
    for developer in developers:
        # capture git commits 24 hours ago
        git_logs = subprocess.run(f'git log --author={developer} --since="24 hours ago" --format={format}', 
                                shell=True, capture_output=True, text=True).stdout.splitlines()

        # build payload for dynamodb
        if len(git_logs) > 0:
            for git_log in git_logs:
                dynamodb_item = build_dynamodb_item(json.loads(git_log))
                payload.append(dynamodb_item)

            # upload git logs to dynamodb
            write_to_dynamodb(json.dumps(payload))
            
        else:
            print(f'No new commits from {developer} in last 24 hours.')


def get_developers_from_dynamodb() -> List:
    try:
        dynamo_db = boto3.resource('dynamodb', endpoint_url='http://localhost:8000') # region_name='us-east-2')
        table = dynamo_db.Table(TABLE_NAME)

        response = table.get_item(
            Key={
                "build_number": BUILD_NUMBER
            }
        )
        developers = response['Item']['developers']
        if len(developers) > 0:
            return developers
        else:
            print(f'developers not found for build: {BUILD_NUMBER}')
            exit(1)
    except Exception as e:
        print(f'error fetching data from dynamadb: {e}')
        exit(1)


def build_dynamodb_item(git_log: dict) -> dict:
    """Formats git log into dynamodb table item"""

    dynamodb_item = {}

    # add Jira ID to log
    git_log['jira_id'] = search_git_log(r'([a-zA-Z]+-\d+)', git_log['subject']).upper()
      
    # capture changed files and add to log
    changed_files = subprocess.run(
        [f'git show --pretty="format:" --name-only {git_log["commit"]}'], 
        shell=True, capture_output=True, text=True)
    git_log['filenames'] = changed_files.stdout.splitlines()

    dynamodb_item['git_logs'] = git_log

    return dynamodb_item


def search_git_log(regex: str, output: str) -> str:
    """Searches string with specified regex"""

    try:
        result = re.search(regex, output).group(1)
        return result
    except AttributeError:
        return ''


def write_to_dynamodb(payload: str):
    """Writes payload to dynamodb table."""

    # print(f'To be sent to DynamoDB: {payload}')  # NEED TO REMOVE WHEN DONE

    dynamodb = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")
    try:
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item=payload)
        print('Updated table with most recent git logs.')
        return_item()   # DELETE WHEN DONE
    except Exception as e:
        print(f'error updating dynamadb: {e}')
        exit(1)

####### HELPER FUNC -- DELETE WHEN DONE ######
def return_item():
    try:
        dynamo_db = boto3.resource('dynamodb', endpoint_url='http://localhost:8000') # region_name='us-east-2')
        table = dynamo_db.Table(TABLE_NAME)

        response = table.get_item(
            Key={
                "build_number": BUILD_NUMBER
            }
        )
        print(response['Item'])
    except Exception as e:
        print(f'error fetching data from dynamadb: {e}')
        exit(1)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        BUILD_NUMBER = str(sys.argv[1])
        parse_git_logs()
    else:
        print('error: missing build_number (eg. \"$ python parse_repo.py 10.07.00.000000-20210805.015637\")')
        exit(1)





# 1) query db for branch name and developer name(s) DONE
# 2) capture 24-hr git logs by developer DONE
# 4) format logs 
# 5) update db table w/ new logs 