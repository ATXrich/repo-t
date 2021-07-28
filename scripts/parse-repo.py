import json
import sys
import subprocess
import re


# build_number
# branch_name
# [developers]
# git_logs - is just a JSON string, which we can leverage it into future use for reporting, if required.

# For Git log format, I prefer to consider -- "{ filename_1 : { jira_number, commiter, logs }, filename_2 : { jira_number, commiter, logs } }



pretty_format = '{"commit": "%H", "subject": "%s", "body": "%b", "author": {"name": "%aN", "email": "%aE", "date": "%at"}}'


# sample_log = 

def set_attribute(git_log, pattern, log_location):
    attribute = re.search(pattern, git_log[log_location])
    if attribute != None:
        return attribute.group(1)
    else:
        return ''


def build_json_output(git_log):
    git_log['jira_id'] = set_attribute(git_log, r'(XHFW-\d+)', 'subject')
    git_log['reason_for_change'] = set_attribute(git_log, r'[c|C]hange:\s(.+)\sTest', 'body')
    git_log['test_procedure'] = set_attribute(git_log, r'[p|P]rocedure:\s(.+)\s[r|R]isks', 'body')
    git_log['risks'] = set_attribute(git_log,  r'[r|R]isks:\s(.+)\s[c|C]hange', 'body')
    git_log['change_id'] = set_attribute(git_log, r'[c|C]hange-[i|I]d:\s(.+)', 'body')  
        
    print(git_log)

    # return json.dumps(git_log)






process = subprocess.run(['git','pull'], capture_output=True, text=True)
if process.returncode != 0:
    print(f'error: {process.stderr}')
    sys.exit(process.returncode)
else:
    # fetch last commit
    process = subprocess.run(['git', 'log', '-n', '1', '--raw'], capture_output=True, text=True)

    # process = subprocess.run(['git', 'log', '-n', '1', '--raw', f'--pretty=format:{pretty_format}'], capture_output=True, text=True)

    print(process.stdout)
    #TODO: build json payload
    # git_log = build_json_output(json.loads(process.stdout))


#TODO: upload to dynamo
