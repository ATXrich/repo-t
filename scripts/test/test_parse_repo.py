import unittest
from dataclasses import dataclass
from typing import List
import parse_repo


class TestParseRepo(unittest.TestCase):
    def test_search_git_log(self):
        @dataclass
        class TestCase:
            name: str
            input: List[str]
            expected: str

        jira_regex = r'([a-zA-Z]+-\d+)'
        build_regex = r'release/(\d.+\d)'
        branch_regex = r'branch\s(.+)'
        testcases = [
            TestCase(
                name='JIRA-ID: EMPTY SUBJECT', 
                input=[jira_regex, ''.upper()], 
                expected=''
            ),
            TestCase(
                name='JIRA-ID: TITLE JIRA ID', 
                input=[jira_regex, 'Xhfw-1234: This is a test'.upper()], 
                expected='XHFW-1234'
            ),
            TestCase(
                name='JIRA-ID: LOWER JIRA ID', 
                input=[jira_regex, 'xhfw-1234: This is a test'.upper()], 
                expected='XHFW-1234'
            ),
            TestCase(
                name='JIRA-ID: UPPER JIRA ID', 
                input=[jira_regex, 'XHFW-1234: This is a test'.upper()], 
                expected='XHFW-1234'
            ),
            TestCase(
                name='JIRA-ID: NO JIRA ID', 
                input=[jira_regex, 'This is a test'.upper()], 
                expected=''
            ),
            TestCase(
                name='JIRA-ID: PARTIAL JIRA ID', 
                input=[jira_regex, 'XH1245: This is a test'.upper()], 
                expected=''
            ),
            TestCase(
                name='JIRA-ID: NO COLON', 
                input=[jira_regex, 'XHFW-1234 This is a test'.upper()],
                expected='XHFW-1234'
            ),
            TestCase(
                name='BUILD NUMBER 10.6', 
                input=[build_regex, 'On branch release/10.6'], 
                expected='10.6'
            ),
            TestCase(
                name='BUILD NUMBER 10.6.1', 
                input=[build_regex, 'On branch release/10.6.1'], 
                expected='10.6.1'
            ),
            TestCase(
                name='BUILD NUMBER 10.10.10', 
                input=[build_regex, 'On branch release/10.10.10'], 
                expected='10.10.10'
            ),
            TestCase(
                name='BUILD NUMBER NONE', 
                input=[build_regex, 'On branch release'], 
                expected=''
            ),
            TestCase(
                name='BRANCH RELEASE/10.6', 
                input=[branch_regex, 'On branch release/10.6'], 
                expected='release/10.6'
            ),
            TestCase(
                name='BRANCH RELEASE/10.6.1', 
                input=[branch_regex, 'On branch release/10.6.1'], 
                expected='release/10.6.1'
            ),
            TestCase(
                name='BRANCH RELEASE/10.10.10', 
                input=[branch_regex, 'On branch release/10.10.10'], 
                expected='release/10.10.10'
            ),
            TestCase(
                name='BRANCH NONE', 
                input=[branch_regex, 'On branch '], 
                expected=''
            )
        ]

        for case in testcases:
            actual = parse_repo.search_git_log(case.input[0], case.input[1])
            self.assertEqual(
                case.expected,
                actual,
                f'failed test {case.name} expected {case.expected}, actual {actual}'
            )
