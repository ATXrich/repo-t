# # !/usr/bin/env python3

import sys, subprocess


if __name__ == "__main__":

    #TODO: pull latest from master

    process = subprocess.run(["git","pull"], capture_output=True, text=True)
    if process.returncode != 0:
        print(f'error: {process.stderr}')
        sys.exit(process.returncode)
    else:
        print(process.stdout)
        # process = subprocess.run(["git","log"], capture_output=True, text=True)
        #TODO: git log last 24 hr commits



    

    #TODO: parse git comments

    #TODO: upload to dynamo
