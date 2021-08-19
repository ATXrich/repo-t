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

git_time_period = "24 hours ago"
xhfw_repo = "core"
format = '\'{"commit": "%h", "date": "%ad", "summary": "%s", "author": {"name": "%an", "email": "%aE"}}\''


def parse_git_logs(branch_name: str) -> str:
    """Checks for new git commits in last 24 hours for given branch and developer(s). 
       Formats and uploads payload to Repo_T Execution History table."""

    cpe_branch_details = get_item_from_dynamodb(repo_t_tables[0]['table_name'], 
                                                repo_t_tables[0]['p_key'], 
                                                branch_name)

    payload = build_dynamodb_payload(cpe_branch_details)

    # upload execution history payload to dynamodb table
    response = update_dynamodb_table(repo_t_tables[1]['table_name'], payload)
    
    return response


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
        try:
            response = response['Item']
        except KeyError:
            print(f'error: {pkey_value} not found in table. Check value.')
            exit(1)
    except Exception as e:
        print(f'error fetching data from dynamodb: {e}')
        exit(1)

    return response


def format_git_log(git_log: dict) -> dict:
    """Adds additional attributes to git log before updating dynamodb table item"""

    # add risk to log
    risk_line = ''

    process = subprocess.run(
        [f'cd {xhfw_repo}/ && git show --format="%b" --name-only {git_log["commit"]} && cd ..'],
        shell=True, capture_output=True, text=True)
    git_lines = process.stdout.splitlines()

    for item in git_lines:
        if re.search(r'[Rr]isks:', item):
            risk_line = item

    git_log['risk'] = regex_search(r':\s(.+)', risk_line)
      
    # capture changed files and add to log
    git_log['filenames'] = get_filenames(git_log['commit'])

    # add package
    git_log['package'] = ''

    return git_log


def build_db_item(git_logs_list: list, cpe_branch_details: dict) -> list:
    """Returns payload for dynamodb"""

    payload = []
    jira_ids = []
    db_item = {
        'branch_name': cpe_branch_details['gerrit_branch_name'],
        'build_number': cpe_branch_details['build_version'],
        'components': [],
        'inventory_board': cpe_branch_details['inventory_board'],
        'nexus_url': cpe_branch_details['nexus_url'],
        'pagination': {
            'current_page': 0,
            'page_size': 0,
            'total_pages': 0,
            'total_test_cases': ''
        },
        'test_cycle': '',
        'test_result': {
            'failed_test_cases': '',
            'passed_test_cases': '',
            'unexecuted_test_cases': ''
        }
    }

    # create list of unique jira_id's from git logs
    for git_log in git_logs_list:
        jira_id = regex_search(r'([a-zA-Z]+-\d+)\W', git_log['summary']).upper()
        jira_ids.append(jira_id)

    jira_ids = list(dict.fromkeys(jira_ids))

    for jira_id in jira_ids:
        matched_logs = []
        developers = []
        db_item['jira_id'] = jira_id
        for git_log in git_logs_list:
            git_log_jira_id = regex_search(r'([a-zA-Z]+-\d+)\W', git_log['summary']).upper()
            if jira_id == git_log_jira_id:
                git_log_copy = git_log.copy()
                matched_logs.append(git_log_copy)
                developers.append(git_log['author']['name'])
        db_item['git_logs'] = matched_logs
        db_item['developers'] = list(dict.fromkeys(developers))
        db_item_copy = db_item.copy()
        payload.append(db_item_copy)

    return payload


def get_filenames(commit: str) -> list:
    """Returns list of changed files in git commit"""

    process = subprocess.run(
        [f'cd {xhfw_repo}/ && git show --pretty="format:" --name-only {commit}'], 
        shell=True, capture_output=True, text=True)
    filenames = process.stdout.splitlines()
    return filenames


def regex_search(regex: str, output: str) -> str:
    """Searches string with specified regex"""

    result = re.findall(regex, output)
    if len(result) > 1:
        result = '_'.join(result)
        return result
    elif len(result) == 1:
        return result[0]
    else:
        return 'NONE'


def build_dynamodb_payload(cpe_branch_details: dict) -> list:
    """Builds formatted dynamodb table payload"""

    git_log_list = []
    payload = []

    # clone gerrit repo
    clone_repo(cpe_branch_details)

    for developer in cpe_branch_details['developers']:
        # capture git commits 24 hours ago for given developer and branch
        process = subprocess.run(
            [f'cd {xhfw_repo}/ && git log \
            --author="{developer}" \
            --since="{git_time_period}" \
            --format={format} && cd ..'],
            shell=True, capture_output=True, text=True
        )

        git_logs = process.stdout.splitlines()
                
        print(f'Retrieved {len(git_logs)} commits for {developer} ' 
              f'on branch {cpe_branch_details["gerrit_branch_name"]} since {git_time_period}.')

        # build git log list for payload['git_logs']
        if len(git_logs) > 0:
            for git_log in git_logs:               
                formatted_git_log = format_git_log(json.loads(git_log))
                git_log_list.append(formatted_git_log)

    # return empty payload if no new logs retrieved
    if len(git_log_list) < 1:
        return payload

    payload = build_db_item(git_log_list, cpe_branch_details)

    return payload


def update_dynamodb_table(table_name: str, payload: list) -> str:
    """Adds new item to dynamodb table."""

    if not payload:
        return 'Nothing to update'

    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')  # endpoint_url="http://localhost:8000") 
    try:
        table = dynamodb.Table(table_name)
        for item in payload:
            response = table.put_item(
                Item=item
            )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return f'Successfully added {len(payload)} item(s) to {table_name} table.'
        return f"Status Code {response['ResponseMetadata']['HTTPStatusCode']}: error updating dynamadb"
    except Exception as e:
        return f'error updating dynamadb: {e}'


def clone_repo(db_item: dict):
    git_user = 'rreed210'   # TODO: REPLACE WITH SERVICE USER
    partial_url = regex_search(r'https:\/\/(.+)', db_item['gerrit_url'])
    url = 'https://' + git_user + '@' + partial_url

    # checks to see if repo is already locally available before cloning
    process = subprocess.run([f'ls {xhfw_repo}/'], shell=True, capture_output=True, text=True)
    if process.stderr != "":
        try:
            process = subprocess.run([f'git clone {url}'], shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f'error occurred cloning gerrit repo: {e}')      
            exit(1)  
    subprocess.run(
        [f'cd {xhfw_repo}/ && git checkout {db_item["gerrit_branch_name"]} \
            && git pull && cd ..'], shell=True, capture_output=True, text=True
    )


def delete_repo():
    subprocess.run([f'cd ..'], shell=True)
    try:
        process = subprocess.run([f'rm -rf {xhfw_repo}/'], shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f'error occurred deleting gerrit repo: {e}')
        exit(1)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        response = parse_git_logs(str(sys.argv[1]))
        print(response)
        delete_repo()
    else:
        print('error: missing gerrit_branch_name argument (eg. \"$ python parse_repo.py release/10.7\")')
        exit(1)
