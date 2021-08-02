import json
import subprocess
import re
import boto3


format = '\'{"commit": "%h", "date": "%ad", "subject": "%s", "body": "%b", "author": {"name": "%aN", "email": "%aE"}}\''


def search_git_log(regex, output):
    try:
        result = re.search(regex, output).group(1)
        return result
    except AttributeError:
        return ''


def build_dynamodb_item(git_log):
    dynamodb_item = {}

    # add Jira ID to log
    git_log['jira_id'] = search_git_log(r'([a-zA-Z]+-\d+)', git_log['subject']).upper()
    
    # add build and branch to log
    process = subprocess.run([f'git status'], shell=True, capture_output=True, text=True)
    dynamodb_item['build_number'] = search_git_log(r'release/(\d.+\d)', process.stdout)
    dynamodb_item['branch_name'] = search_git_log(r'branch\s(.+)', process.stdout)
    
    # capture changed files and add to log
    changed_files = subprocess.run(
        [f'git show --pretty="format:" --name-only {git_log["commit"]}'], 
        shell=True, capture_output=True, text=True)
    git_log['filenames'] = changed_files.stdout.splitlines()

    dynamodb_item['developer'] = git_log['author']['name']
    dynamodb_item['git_logs'] = git_log

    return dynamodb_item


# capture git commits 24 hours ago
git_logs = subprocess.run(
    f'git log --since="24 hours ago" --format={format}', 
    shell=True, capture_output=True, text=True).stdout.splitlines()

# build payload for dynamodb
if len(git_logs) > 0:
    payload = []

    for git_log in git_logs:
        dynamodb_item = build_dynamodb_item(json.loads(git_log))
        payload.append(dynamodb_item)

    # TODO: upload to dynamodb
    print(f'To be sent to DynamoDB: {json.dumps(payload)}')  ## NEED TO REMOVE WHEN DONE
    # dynamodb = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")

    # table = dynamodb.Table('Repo_T_Execution_History')
    # table.put_item(Item=dynamodb_item)


else:
    print("No new commits in last 24 hours.")


# {
#     "build_number": "1.0", 
#     "branch_name": "release/1.0", 
#     "developer": "rreed210", 
#     "git_logs": {
#         "commit": "e893f32", 
#         "date": "Mon Aug 2 12:38:10 2021 -0500", 
#         "subject": "XHAVEN-5184: adding gerritt resource reference", 
#         "body": "", 
#         "author": {
#             "name": "rreed210", 
#             "email": "richard_reed@comcast.com"
#         }, 
#         "jira_id": "XHAVEN-5184", 
#         "filenames": ["ci/pipeline.yaml"]
#     }
# }


