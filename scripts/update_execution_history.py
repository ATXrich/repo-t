import sys
import json
import subprocess
import re
from typing import List
import boto3
from boto3.dynamodb.conditions import Key
from botocore import endpoint

repo_t_tables = [
    {
        'table_name': 'Repo_T_Gerrit_CPE_Branch_Details',
        'p_key': 'gerrit_branch_name'

    },
    {
        'table_name': 'Repo_T_Execution_History',
        'p_key': 'build_number'
    }
]


format = '\'{"commit": "%h", "date": "%ad", "subject": "%s", "body": "%b", "author": {"name": "%an", "email": "%aE"}}\''


def parse_git_logs(branch_name: str) -> str:
    """Checks for new git commits in last 24 hours for given branch and developer(s). 
       Formats output and uploads to Repo_T Execution History table."""

    cpe_branch_details = get_item_from_dynamodb(repo_t_tables[0]['table_name'], 
                                                repo_t_tables[0]['p_key'], 
                                                branch_name)

    payload = build_dynamodb_payload(cpe_branch_details)

    # upload history to dynamodb
    response = add_item_to_dynamodb(repo_t_tables[1]['table_name'], payload)
    
    return response


def build_dynamodb_payload(cpe_branch_details: dict) -> dict:
    """Builds formatted dynamodb table payload"""

    payload = {}
    git_log_list = []

    for developer in cpe_branch_details['developers']:
        # capture git commits 24 hours ago for given developer and branch
        process = subprocess.run(
            f'git log --author={developer} --since="24 hours ago" --format={format} \
                {cpe_branch_details["gerrit_branch_name"]}', 
            shell=True, capture_output=True, text=True)

        git_logs = process.stdout.splitlines()
        
        print(f'Retrieved {len(git_logs)} commits in last 24 hours for {developer}' 
              f' on branch {cpe_branch_details["gerrit_branch_name"]}.')

        # build git log list for payload['git_logs']
        if len(git_logs) > 0:
            for git_log in git_logs:
                formatted_git_logs = format_git_logs(json.loads(git_log))
                git_log_list.append(formatted_git_logs)
    
    # return empty payload if no new logs retrieved
    if len(git_log_list) < 1:
        return payload

    payload['branch_name'] = cpe_branch_details['gerrit_branch_name']
    payload['build_number'] = cpe_branch_details['build_version']
    payload['current_page'] = 1
    payload['date_time'] = git_log_list[0]['date']
    payload['developers'] = cpe_branch_details['developers']
    payload['fail_test_cases'] = 0 
    payload['git_logs'] = git_log_list
    payload['inventory_board'] = cpe_branch_details['inventory_board']
    payload['nexus_url'] = cpe_branch_details['nexus_url']
    payload['page_size'] = 50
    payload['pass_test_cases'] = '50'
    payload['test_cycle'] = 'sample_test_cycle'
    payload['total_pages'] = 3
    payload['total_test_cases'] = '150' 

    return payload


def get_item_from_dynamodb(table_name: str, primary_key: str, pkey_value: str):
    """Returns value for a given dynamodb item attribute"""

    try:
        dynamo_db = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')  # region_name='us-east-2')
        table = dynamo_db.Table(table_name)

        response = table.get_item(
            Key={
                primary_key: pkey_value
            }
        )
        return response['Item']
    except Exception as e:
        print(f'error fetching data from dynamodb: {e}')
        exit(1)


def format_git_logs(git_log: dict) -> dict:
    """Adds additional attributes to git log before updating dynamodb table item"""

    # add Jira ID to log
    git_log['jira_id'] = search_git_log(r'([a-zA-Z]+-\d+)', git_log['subject']).upper()
      
    # capture changed files and add to log
    git_log['filenames'] = get_filenames(git_log['commit'])

    return git_log


def get_filenames(commit: str) -> list:
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


def add_item_to_dynamodb(table_name: str, payload: dict) -> str:
    """Adds new item to dynamodb table."""

    if not payload:
        return 'Nothing to update'
        exit(1)

    dynamodb = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")
    try:
        table = dynamodb.Table(table_name)
        response = table.put_item(
            Item=payload
        )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return f'{table_name} table updated with most recent logs.'
        return f"Status Code {response['ResponseMetadata']['HTTPStatusCode']}: error updating dynamadb"
    except Exception as e:
        return f'error updating dynamadb: {e}'


if __name__ == '__main__':
    if len(sys.argv) > 1:
        response = parse_git_logs(str(sys.argv[1]))
        print(response)
    else:
        print('error: missing gerrit_branch_name argument (eg. \"$ python parse_repo.py release/10.7\")')
        exit(1)