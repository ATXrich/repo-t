import re
import unittest
import parse_repo

class SearchGitLogTestCase(unittest.TestCase):
    """Tests for 'parse_repo.py'."""

    # git_log_complete = {"commit": "554517a", 
    #                 "date": "Mon Aug 2 13:30:10 2021 -0500", 
    #                 "subject": "XHAVEN-1234: building payload list", 
    #                 "body": "", 
    #                 "author": {"name": "rreed210", "email": "richard_reed@comcast.com"}}
    
    # git_log_jira_lowercase = {"commit": "554517a", 
    #                 "date": "Mon Aug 2 13:30:10 2021 -0500", 
    #                 "subject": "xhaven-5184: building payload list", 
    #                 "body": "", 
    #                 "author": {"name": "rreed210", "email": "richard_reed@comcast.com"}}
    
    # git_log_no_jira_id = {"commit": "554517a", 
    #                     "date": "Mon Aug 2 13:30:10 2021 -0500", 
    #                     "subject": "xhaven-5184: building payload list", 
    #                     "body": "", 
    #                     "author": {"name": "rreed210", "email": "richard_reed@comcast.com"}}

    # git_log_complete = {"commit": "554517a", 
    #                     "date": "Mon Aug 2 13:30:10 2021 -0500", 
    #                     "subject": "xhaven-5184: building payload list", 
    #                     "body": "", 
    #                     "author": {"name": "rreed210", "email": "richard_reed@comcast.com"}}

    # missing_jira_id
    # missing_build

    def test_jira_id(self):
        regex = r'([a-zA-Z]+-\d+)'
        git_log_complete = {"commit": "554517a", 
                    "date": "Mon Aug 2 13:30:10 2021 -0500", 
                    "subject": "XHAVEN-1234: building payload list", 
                    "body": "", 
                    "author": {"name": "rreed210", "email": "richard_reed@comcast.com"}}
        result = parse_repo.search_git_log(regex, git_log_complete)
        self.assertEqual(result, "XHAVEN-1234")

