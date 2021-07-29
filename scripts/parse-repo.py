import json
import sys
import subprocess
import re


# build_number
# branch_name
# [developers]
# git_logs - is just a JSON string, which we can leverage it into future use for reporting, if required.
# {
#   commit:
#   date:
#   jira_id:
#   committer: {
#               name:
#               email: 
#   }
#   filenames: {}
#   subject:
#   body:
# }

# For Git log format, I prefer to consider -- "{ filename_1 : { jira_number, commiter, logs }, filename_2 : { jira_number, commiter, logs } }



format = '\'{"commit": "%h", "date": "%ct", "subject": "%s", "body": "%b", "committer": {"name": "%cN", "email": "%cE"}}\''


# sample_log = 

def build_json_output(git_log):
    # add Jira ID to log
    jira_id = re.search(r'([a-zA-Z]+-\d+)', git_log['subject']).group(1)
    if jira_id != None:
        git_log['jira_id'] = jira_id
    else:
        git_log['jira_id'] = ''

    # get release version and add to log
    process = subprocess.run([f'git status'], shell=True, capture_output=True, text=True)
    build = re.search(r'release/(\d.+\d)', process.stdout).group(1)
    if build != None:
        git_log['build'] = build
    else:
        git_log['build'] = ''

    # capture changed files and add to log
    changed_files = subprocess.run([f'git show --pretty="format:" --name-only {git_log["commit"]}'], shell=True, capture_output=True, text=True)
    git_log['files'] = changed_files.stdout.splitlines()

    return json.dumps(git_log)






# process = subprocess.run(['git pull'], shell=True, capture_output=True, text=True)
# if process.returncode != 0:
#     print(f'error: {process.stderr}')
#     sys.exit(process.returncode)
# else:
# capture git logs in the past 24 hours
git_logs = subprocess.run(f'git log --since="1 hour ago" --format={format}', shell=True, capture_output=True, text=True).stdout.splitlines()
# print(git_logs)
if len(git_logs) > 0:
    for log in git_logs:
        #TODO: build json payload
        payload = build_json_output(json.loads(log))

        print(f'To be sent to DynamoDB: {payload} ({type(payload)})')
else:
    print("No new commits in last 24 hours")
        



#TODO: upload to dynamo
