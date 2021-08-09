import unittest
from dataclasses import dataclass
from typing import Dict, List
import json
import boto3
from moto import mock_dynamodb2
from botocore.exceptions import ClientError
import parse_repo


@mock_dynamodb2
class TestParseRepo(unittest.TestCase):
    table_item = {}
    build_number = ""

    def setUp(self, dynamodb=None):
        if not dynamodb:
            dynamo_db = boto3.resource('dynamodb', region_name='us-east-2')
        table_name = 'Repo_T_Execution_History_Test_Table'
        self.table = dynamo_db.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'build_number',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'build_number',
                    'AttributeType': 'S'
                }
            ])

        with open('test/data/data.json') as json_file:
            data = json.load(json_file)
            self.table_item = data
            self.build_number = data["build_number"]
        self.table.put_item(Item=data)

    def tearDown(self):
        self.table.delete()
        self.dynamodb = None

    def test_search_git_log(self):
        @dataclass
        class TestCase:
            name: str
            input: List[str]
            expected: str

        jira_regex = r'([a-zA-Z]+-\d+)'
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
            )
        ]

        for case in testcases:
            actual = parse_repo.search_git_log(case.input[0], case.input[1])
            self.assertEqual(
                case.expected,
                actual,
                f'failed test {case.name} expected {case.expected}, actual {actual}'
            )

    def test_get_value_from_dynamodb(self):
        actual_output = parse_repo.get_value_from_dynamodb(self.build_number, 'developers')
        self.assertEqual(actual_output, self.table_item['developers'])   # may not work everywhere

    def test_build_dynamodb_item(self):
        @dataclass
        class TestCase:
            name: str
            input: Dict
            expected: Dict

        testcases = [
            TestCase(
                name='HAPPY PATH', 
                input={'commit': '38974ba', 'date': 'Sun Aug 8 15:46:01 2021 -0500', 'subject': 'xhaven-5184: dynamodb tests', 'body': '', 'author': {'name': 'rreed210', 'email': 'richard_reed@comcast.com'}},
                expected={'git_logs': {'commit': '38974ba', 'date': 'Sun Aug 8 15:46:01 2021 -0500', 'subject': 'xhaven-5184: dynamodb tests', 'body': '', 'author': {'name': 'rreed210', 'email': 'richard_reed@comcast.com'}, 'jira_id': 'XHAVEN-5184', 'filenames': ['scripts/test/test_parse_repo.py']}}
            )
        ]
        
        for case in testcases:
            actual = parse_repo.build_dynamodb_item(case.input)
            self.assertEqual(
                case.expected,
                actual,
                f'failed test {case.name} expected {case.expected}, actual {actual}'
            )

    def test_update_dynamodb(self):
        @dataclass
        class TestCase:
            name: str
            input: List[str]
            expected: str

        testcases = [
            TestCase(
                name='VALID PAYLOAD', 
                input=[{"git_logs": {"commit": "be84c43", "date": "Sat Aug 7 16:24:40 2021 -0500", "subject": "xhaven-5184: clean up test table", "body": "", "author": {"name": "rreed210", "email": "richard_reed@comcast.com"}, "jira_id": "XHAVEN-5184", "filenames": ["scripts/test/test_parse_repo.py"]}}, {"git_logs": {"commit": "4065637", "date": "Sat Aug 7 16:22:33 2021 -0500", "subject": "xhaven-5184 : removed helper method", "body": "", "author": {"name": "rreed210", "email": "richard_reed@comcast.com"}, "jira_id": "XHAVEN-5184", "filenames": ["scripts/parse_repo.py"]}}, {"git_logs": {"commit": "71b91fa", "date": "Sat Aug 7 15:46:12 2021 -0500", "subject": "xhaven-5184: adding helper func to show db update", "body": "", "author": {"name": "rreed210", "email": "richard_reed@comcast.com"}, "jira_id": "XHAVEN-5184", "filenames": ["scripts/parse_repo.py"]}}, {"git_logs": {"commit": "7f6887b", "date": "Sat Aug 7 15:34:50 2021 -0500", "subject": "XHAVEN-5184: adding git log by dev", "body": "", "author": {"name": "rreed210", "email": "richard_reed@comcast.com"}, "jira_id": "XHAVEN-5184", "filenames": ["scripts/parse_repo.py"]}}], 
                expected='Repo_T_Execution_History table updated with most recent logs.'
            )
        ]
        
        for case in testcases:
            actual = parse_repo.update_dynamodb(json.dumps(case.input), self.build_number)
            self.assertEqual(
                case.expected,
                actual,
                f'failed test {case.name} expected {case.expected}, actual {actual}'
            )

    
if __name__ == '__main__':
    unittest.main()
