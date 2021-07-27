# # !/usr/bin/env python3


# {
#   "commit": "9caf3bc17f34ac3b93c8127dd776e34bad1d6ee0",
#   "abbreviated_commit": "9caf3bc17",
#   "tree": "bd69dee77adb7977a77d07dfcb02d39e3cab9066",
#   "abbreviated_tree": "bd69dee77",
#   "parent": "2798b17a396897b916a2f4a696b5726ff0e519dd",
#   "abbreviated_parent": "2798b17a3",
#   "refs": "HEAD -> master, origin/master, origin/HEAD",
#   "encoding": "",
#   "subject": "XHFW-2272: sync state request causes infinite loop of request",
#   "sanitized_subject_line": "XHFW-2272-sync-state-request-causes-infinite-loop-of-request",
#   "body": "Reason for change: If desired state is not set to null in xhf
# thing full state report in response to sync request, it causes
# server to send request again on reception of each response to
# sync request and this loop never ends.

# Test Procedure: Zith test has been fixed to detect it. It can be
# tested on gateway using iot simulator and send sync request.

# Risks: None

# Change-Id: Iba3e4b684aa312ad90517e532356fcbf30ee3bd6
# ",
#   "commit_notes": "",
#   "verification_flag": "N",
#   "signer": "",
#   "signer_key": "",
#   "author": {
#     "name": "Naeem Khan",
#     "email": "naeem_khan@comcast.com",
#     "date": "Thu, 17 Jun 2021 14:34:29 -0400"
#   },
#   "commiter": {
#     "name": "Thomas Lea",
#     "email": "Thomas_Lea@comcast.com",
#     "date": "Wed, 30 Jun 2021 11:00:38 +0000"
#   }
# }



import json
import sys
import subprocess
import re

body = 'Reason for change: Reason goes here. \
        Test Procedure: Test Goes Here. \
        Risks: None \
        Change-Id: AODIE3r3fwwfd9'

pretty_format = '{"commit": "%H", "subject": "%s", "body": "%b", "author": {"name": "%aN", "email": "%aE", "date": "%aD"}, "commiter": {"name": "%cN", "email": "%cE", "date": "%cD"}}'
body_pattern = r''
jira_ticket_pattern = r'XHFW-\d+'

if __name__ == "__main__":

    #TODO: pull latest from master

    process = subprocess.run(["git","pull"], capture_output=True, text=True)
    if process.returncode != 0:
        print(f'error: {process.stderr}')
        sys.exit(process.returncode)
    else:
        #TODO: git log last 24 hr commits
        process = subprocess.run(["git","log","-n","1",f"--pretty=format:{pretty_format}"], capture_output=True, text=True)
        print(process.stdout)
        git_log_output = json.loads(process.stdout)
        print(git_log_output["subject"])

        # Dict = dict((x.strip(), y.strip())
        #      for x, y in (element.split(':') 
        #      for element in body.split(', ')))

        # print(body)
   

    #TODO: parse git comments (subject and body)

    #TODO: upload to dynamo
