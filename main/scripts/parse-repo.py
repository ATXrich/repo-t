# # !/usr/bin/env python3

import sys, subprocess


if __name__ == "__main__":

    #TODO: pull latest from master

    # subprocess.run(["git","pull"])
    process = subprocess.run(["ls","-l"], capture_output=True, text=True)
    if process.returncode != 0:
        print('error: failed to pull latest from repo')
        sys.exit(process.returncode)
    else:
        process = subprocess.run(["git","log"], capture_output=True, text=True)
        #TODO: git log last 24 hr commits



    

    #TODO: parse git comments

    #TODO: upload to dynamo
