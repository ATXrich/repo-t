import json
import subprocess
import re


format = '\'{"commit": "%h", "date": "%ct", "subject": "%s", "body": "%b", \
        "author": {"name": "%aN", "email": "%aE"}, "committer": {"name": "%cN", "email": "%cE"}}\''


def search_git_output(regex, output):
    result = re.search(regex, output).group(1)
    if result is not None:
        return result
    else:
        return ''


def build_json_payload(git_log):
    payload = {}

    # add Jira ID to log
    git_log['jira_id'] = search_git_output(r'([a-zA-Z]+-\d+)', git_log['subject'])
    
    # add build and branch to log
    process = subprocess.run([f'git status'], shell=True, capture_output=True, text=True)
    payload['build'] = search_git_output(r'release/(\d.+\d)', process.stdout)
    payload['branch'] = search_git_output(r'branch\s(.+)', process.stdout)
    
    # capture changed files and add to log
    changed_files = subprocess.run(
        [f'git show --pretty="format:" --name-only {git_log["commit"]}'], 
        shell=True, capture_output=True, text=True)
    git_log['filenames'] = changed_files.stdout.splitlines()

    payload['developer'] = git_log['author']['name']
    payload['git_log'] = git_log

    return payload


# capture git logs in the past 24 hours
git_logs = subprocess.run(
    f'git log --since="24 hours ago" --format={format}', 
    shell=True, capture_output=True, text=True).stdout.splitlines()
if len(git_logs) > 0:
    for log in git_logs:
        payload = build_json_payload(json.loads(log))

        # TODO: upload to dynamo
        print(f'To be sent to DynamoDB: {payload}')
else:
    print("No new commits in last 24 hours")
