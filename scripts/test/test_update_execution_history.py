import unittest
from dataclasses import dataclass
from typing import Dict, List
import json
import warnings
from moto import mock_dynamodb2
import boto3
from botocore.exceptions import ClientError
import update_execution_history


@mock_dynamodb2
class TestUpdateExecutionHistory(unittest.TestCase):
    table_item = {}
    branch_name = ""

    repo_t_tables = [
        {
            'table_name': 'Repo_T_Gerrit_CPE_Branch_Details_Test',
            'p_key': 'gerrit_branch_name'

        },
        {
            'table_name': 'Repo_T_Execution_History_Test',
            'p_key': 'build_number'
        }
    ]

    def setUp(self, dynamodb=None):
        warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)
        if not dynamodb:
            dynamo_db = boto3.resource('dynamodb', region_name='us-east-2')
        
        for repo_t_table in self.repo_t_tables:
            try:
                table = dynamo_db.create_table(
                    TableName=repo_t_table['table_name'],
                    KeySchema=[
                        {
                            'AttributeName': repo_t_table['p_key'],
                            'KeyType': 'HASH'
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': repo_t_table['p_key'],
                            'AttributeType': 'S'
                        }
                    ],
                    ProvisionedThroughput={
                        'ReadCapacityUnits': 1,
                        'WriteCapacityUnits': 1
                    }
                )
            except Exception as e:
                print(f'{e}')

        with open('test/data/test.json') as json_file:
            items = json.load(json_file)
            self.table_item = items
        self.branch_name = self.table_item[self.repo_t_tables[0]['p_key']]
        table = dynamo_db.Table(self.repo_t_tables[0]['table_name'])
        table.put_item(Item=items)

    def tearDown(self, dynamodb=None):
        if not dynamodb:
            dynamo_db = boto3.resource('dynamodb', region_name='us-east-2')

        for repo_t_table in self.repo_t_tables:
            table = dynamo_db.Table(repo_t_table['table_name'])
            table.delete()
        self.dynamodb = None

    def test_format_git_logs(self):
        @dataclass
        class TestCase:
            name: str
            input: List[str]
            expected: str

        testcases = [
            TestCase(
                name='Happy Path', 
                input={"commit": "e32b218", "date": "Mon Aug 16 08:44:51 2021 -0500", "subject": "xhaven-5184: updated names", "body": "", "author": {"name": "rreed210", "email": "richard_reed@comcast.com"}},
                expected={'commit': 'e32b218', 'date': 'Mon Aug 16 08:44:51 2021 -0500', 'subject': 'xhaven-5184: updated names', 'body': '', 'author': {'name': 'rreed210', 'email': 'richard_reed@comcast.com'}, 'jira_id': 'XHAVEN-5184', 'filenames': ['scripts/parse_repo.py', 'scripts/test/test_parse_repo.py']}
            )
        ]

        for case in testcases:
            actual = update_execution_history.format_git_logs(case.input)
            self.assertEqual(
                case.expected,
                actual,
                f'failed test {case.name} expected {case.expected}, actual {actual}'
            )

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
            actual = update_execution_history.search_git_log(case.input[0], case.input[1])
            self.assertEqual(
                case.expected,
                actual,
                f'failed test {case.name} expected {case.expected}, actual {actual}'
            )

    # def test_get_item_from_dynamodb(self):
    #     actual_output = update_execution_history.get_item_from_dynamodb(self.repo_t_tables[0]['table_name'],
    #                                                                     self.repo_t_tables[0]['p_key'], 'release/1.0') 
                                                                        #self.table_item[self.repo_t_tables[0]['p_key']])
        # self.assertEqual(actual_output, self.table_item)

    # def test_build_dynamodb_item(self):
    #     @dataclass
    #     class TestCase:
    #         name: str
    #         input: Dict
    #         expected: Dict

    #     testcases = [
    #         TestCase(
    #             name='HAPPY PATH', 
    #             input={
    #                 'commit': '38974ba', 
    #                 'date': 'Sun Aug 8 15:46:01 2021 -0500', 
    #                 'subject': 'xhaven-5184: dynamodb tests', 
    #                 'body': '', 
    #                 'author': 
    #                 {
    #                     'name': 'rreed210', 
    #                     'email': 'richard_reed@comcast.com'
    #                 }
    #             },
    #             expected={
    #                 'commit': '38974ba', 
    #                 'date': 'Sun Aug 8 15:46:01 2021 -0500', 
    #                 'subject': 'xhaven-5184: dynamodb tests', 
    #                 'body': '', 
    #                 'author': 
    #                 {
    #                     'name': 'rreed210', 
    #                     'email': 'richard_reed@comcast.com'
    #                 }, 
    #                 'jira_id': 'XHAVEN-5184', 
    #                 'filenames': ['scripts/test/test_update_execution_history.py']
    #             }
    #         )
    #     ]
        
    #     for case in testcases:
    #         actual = update_execution_history.build_dynamodb_item(case.input)
    #         self.assertEqual(
    #             case.expected,
    #             actual,
    #             f'failed test {case.name} expected {case.expected}, actual {actual}'
    #         )

    # def test_update_dynamodb(self):
    #     @dataclass
    #     class TestCase:
    #         name: str
    #         input: List[str]
    #         expected: str

    #     testcases = [
    #         TestCase(
    #             name='VALID PAYLOAD', 
    #             input=[
    #                 {
    #                     "git_logs": {
    #                         "commit": "be84c43", 
    #                         "date": "Sat Aug 7 16:24:40 2021 -0500", 
    #                         "subject": "xhaven-5184: clean up test table", 
    #                         "body": "", 
    #                         "author": {
    #                             "name": "rreed210", 
    #                             "email": "richard_reed@comcast.com"
    #                         }, 
    #                         "jira_id": "XHAVEN-5184", 
    #                         "filenames": ["scripts/test/test_update_execution_history.py"]
    #                     }
    #                 }, 
    #                 {
    #                     "git_logs": {
    #                         "commit": "4065637", 
    #                         "date": "Sat Aug 7 16:22:33 2021 -0500", 
    #                         "subject": "xhaven-5184 : removed helper method", 
    #                         "body": "", 
    #                         "author": {
    #                             "name": "rreed210", 
    #                             "email": "richard_reed@comcast.com"
    #                         }, 
    #                         "jira_id": "XHAVEN-5184", 
    #                         "filenames": ["scripts/update_execution_history.py"]
    #                     }
    #                 }
    #             ], 
    #             expected='Repo_T_Execution_History table updated with most recent logs.'
    #         )
    #     ]
        
    #     for case in testcases:
    #         actual = update_execution_history.update_dynamodb(json.dumps(case.input), self.build_number)
    #         self.assertEqual(
    #             case.expected,
    #             actual,
    #             f'failed test {case.name} expected {case.expected}, actual {actual}'
    #         )

    
if __name__ == '__main__':
    unittest.main()
