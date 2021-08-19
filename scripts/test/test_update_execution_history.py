import unittest
from dataclasses import dataclass
from typing import Dict, List
import json
import warnings
from botocore import endpoint
from moto import mock_dynamodb2
import boto3
from botocore.exceptions import ClientError
import update_execution_history


@mock_dynamodb2
class TestUpdateExecutionHistory(unittest.TestCase):

    repo_t_tables = [
        {
            'table_name': 'Test_Repo_T_Gerrit_CPE_Branch_Details',
            'p_key': 'gerrit_branch_name'

        },
        {
            'table_name': 'Test_Repo_T_Execution_History',
            'p_key': 'build_number'
        }
    ]

    def setUp(self, dynamodb=None):
        warnings.filterwarnings(action='ignore', message='unclosed', category=ResourceWarning)
        if not dynamodb:
            dynamo_db = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')

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
        table = dynamo_db.Table(self.repo_t_tables[0]['table_name'])
        for item in items:
            table.put_item(Item=item)

    def tearDown(self, dynamodb=None):
        if not dynamodb:
            dynamo_db = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')

        for repo_t_table in self.repo_t_tables:
            table = dynamo_db.Table(repo_t_table['table_name'])
            table.delete()
        self.dynamodb = None

    def test_format_git_log(self):
        @dataclass
        class TestCase:
            name: str
            input: List[str]
            expected: str

        testcases = [
            TestCase(
                name='Happy Path', 
                input={'commit': 'e32b218', 'date': 'Mon Aug 16 08:44:51 2021 -0500', 
                       'summary': 'xhaven-5184: updated names', 
                       'author': {'name': 'rreed210', 'email': 'richard_reed@comcast.com'}},
                expected={'commit': 'e32b218', 'date': 'Mon Aug 16 08:44:51 2021 -0500', 
                          'summary': 'xhaven-5184: updated names', 'risk': 'NONE', 'package': '',
                          'author': {'name': 'rreed210', 'email': 'richard_reed@comcast.com'}, 
                          'filenames': []}
            )
        ]

        for case in testcases:
            actual = update_execution_history.format_git_log(case.input)
            self.assertEqual(
                case.expected,
                actual,
                f'failed test {case.name} expected {case.expected}, actual {actual}'
            )

    def test_regex_search(self):
        @dataclass
        class TestCase:
            name: str
            input: List[str]
            expected: str

        jira_regex = r'([a-zA-Z]+-\d+)\W'
        url_regex = r'https:\/\/(.+)'
        risk_regex = r':\s(.+)'
        testcases = [
            TestCase(
                name='RISK NOT IN LOGS', 
                input=[risk_regex, ''], 
                expected='NONE'
            ),
            TestCase(
                name='RISK', 
                input=[risk_regex, 'Risks: Very High'], 
                expected='Very High'
            ),
            TestCase(
                name='URL', 
                input=[url_regex, 'https://gerrit.teamccp.com/plugins/gitiles/rdk/components/cpc/zilker-client'], 
                expected='gerrit.teamccp.com/plugins/gitiles/rdk/components/cpc/zilker-client'
            ),
            TestCase(
                name='TWO JIRA IDS', 
                input=[jira_regex, 'XHFW-1565, XHFW-1566: Reference XHFW-1234'.upper()], 
                expected='XHFW-1565_XHFW-1566'
            ),
            TestCase(
                name='THREE JIRA IDS', 
                input=[jira_regex, 'XHFW-1565, XHFW-1566, XHFW-1567: Reference XHFW-1234'.upper()], 
                expected='XHFW-1565_XHFW-1566_XHFW-1567'
            ),
            TestCase(
                name='JIRA-ID: EMPTY SUBJECT', 
                input=[jira_regex, ''.upper()], 
                expected='NONE'
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
                expected='NONE'
            ),
            TestCase(
                name='JIRA-ID: PARTIAL JIRA ID', 
                input=[jira_regex, 'XH1245: This is a test'.upper()], 
                expected='NONE'
            ),
            TestCase(
                name='JIRA-ID: NO COLON', 
                input=[jira_regex, 'XHFW-1234 This is a test'.upper()],
                expected='XHFW-1234'
            )
        ]

        for case in testcases:
            actual = update_execution_history.regex_search(case.input[0], case.input[1])
            self.assertEqual(
                case.expected,
                actual,
                f'failed test {case.name} expected {case.expected}, actual {actual}'
            )

    def test_get_item_from_dynamodb(self):
        @dataclass
        class TestCase:
            name: str
            input: dict
            expected: dict
        
        testcases = [
            TestCase(
                name='HAPPY PATH',
                input={'table_name': self.repo_t_tables[0]['table_name'], 
                       'primary_key': self.repo_t_tables[0]['p_key'], 
                       'pkey_value': 'release/10.7'
                       },
                expected={'build_version': '10.07.00.000000', 
                          'developers': ['John Elderton', 'Weston Boyd', 'Thomas Lea'],
                          'gerrit_branch_name': 'release/10.7',
                          'gerrit_url': 'https://rdkgerrithub.stb.r53.xcal.tv/a/xhfw/core',
                          'inventory_board': 'Onsite_Rack_8_Board_3',
                          'nexus_url': 'https://nexus.comcast.com/nexus/service/rest/repository/browse/cpe-snapshots'
                          }
            )
        ]

        for case in testcases:
            actual = update_execution_history.get_item_from_dynamodb(
                case.input['table_name'], 
                case.input['primary_key'], 
                case.input['pkey_value'])
            self.assertEqual(
                case.expected,
                actual,
                f'failed test {case.name} expected {case.expected}, actual {actual}'
            )

    def test_build_db_item(self):
        @dataclass
        class TestCase:
            name: str
            input: list
            expected: list

        testcases = [
            TestCase(
                name='2 DEVELOPERS, 1 JIRA ID', 
                input=[
                    [
                        {
                            'author': {
                                'email': 'weston_boyd@comcast.com',
                                'name': 'Weston Boyd'
                            },
                            'commit': '8a6f24a21',
                            'date': 'Mon Aug 9 18:45:20 2021 -0500',
                            'filenames': [
                                'source/utils/networkUtil/CMakeLists.txt',
                                'source/utils/networkUtil/src/main.c'
                            ],
                            'package': '',
                            'risk': 'Low',
                            'summary': 'XHFW-1018 : xhNetworkUtil no custom DNS for Flex'
                        },
                        {
                            'author': {
                                'email': 'thoas_lea@comcast.com',
                                'name': 'Thomas Lea'
                            },
                            'commit': '8a6f24a51',
                            'date': 'Mon Aug 9 18:31:20 2021 -0500',
                            'filenames': [
                                'source/utils/networkUtil/CMakeLists.txt',
                                'source/utils/networkUtil/src/main.c'
                            ],
                            'package': '',
                            'risk': 'Low',
                            'summary': 'XHFW-1018 : xhNetworkUtil no custom DNS for Flex'
                        }
                    ],
                    {   
                        'build_version': '10.07.00.000000',
                        'developers': ['John Elderton', 'Weston Boyd', 'Thomas Lea'],
                        'gerrit_branch_name': 'release/10.7',
                        'gerrit_url': 'https://rdkgerrithub.stb.r53.xcal.tv/a/xhfw/core',
                        'inventory_board': 'Onsite_Rack_8_Board_3',
                        'nexus_url': 'https://nexus.comcast.com/nexus/service/rest/repository/browse/cpe-snapshots'
                    }
                ],
                expected=[
                    {
                        'branch_name': 'release/10.7', 
                        'build_number': '10.07.00.000000', 
                        'components': [], 
                        'inventory_board': 'Onsite_Rack_8_Board_3', 
                        'nexus_url': 'https://nexus.comcast.com/nexus/service/rest/repository/browse/cpe-snapshots',
                        'developers': ['Weston Boyd', 'Thomas Lea'],
                        'pagination': {'current_page': 0, 'page_size': 0, 'total_pages': 0, 'total_test_cases': ''}, 
                        'test_cycle': '', 'test_result': {
                            'failed_test_cases': '', 'passed_test_cases': '', 'unexecuted_test_cases': ''}, 
                        'jira_id': 'XHFW-1018', 
                        'git_logs': [
                            {
                                'author': {'email': 'weston_boyd@comcast.com', 'name': 'Weston Boyd'}, 
                                'commit': '8a6f24a21', 
                                'date': 'Mon Aug 9 18:45:20 2021 -0500', 
                                'filenames': ['source/utils/networkUtil/CMakeLists.txt', 
                                              'source/utils/networkUtil/src/main.c'], 
                                'package': '', 
                                'risk': 'Low', 
                                'summary': 'XHFW-1018 : xhNetworkUtil no custom DNS for Flex'
                            }, 
                            {
                                'author': {'email': 'thoas_lea@comcast.com', 'name': 'Thomas Lea'}, 
                                'commit': '8a6f24a51', 
                                'date': 'Mon Aug 9 18:31:20 2021 -0500', 
                                'filenames': ['source/utils/networkUtil/CMakeLists.txt', 
                                              'source/utils/networkUtil/src/main.c'], 
                                'package': '', 
                                'risk': 'Low', 
                                'summary': 'XHFW-1018 : xhNetworkUtil no custom DNS for Flex'
                            }
                        ]
                    }
                ]
            ),
            TestCase(
                name='2 DEVELOPERS, 2 JIRA IDS', 
                input=[
                    [
                        {
                            'author': {
                                'email': 'weston_boyd@comcast.com',
                                'name': 'Weston Boyd'
                            },
                            'commit': '8a6f24a21',
                            'date': 'Mon Aug 9 18:45:20 2021 -0500',
                            'filenames': [
                                'source/utils/networkUtil/CMakeLists.txt',
                                'source/utils/networkUtil/src/main.c'
                            ],
                            'package': '',
                            'risk': 'Low',
                            'summary': 'XHFW-1018 : xhNetworkUtil no custom DNS for Flex'
                        },
                        {
                            'author': {
                                'email': 'thoas_lea@comcast.com',
                                'name': 'Thomas Lea'
                            },
                            'commit': '8a6f24a51',
                            'date': 'Mon Aug 9 18:31:20 2021 -0500',
                            'filenames': [
                                'source/utils/networkUtil/CMakeLists.txt',
                                'source/utils/networkUtil/src/main.c'
                            ],
                            'package': '',
                            'risk': 'Very High',
                            'summary': 'XHFW-1080 : xhNetworkUtil no custom DNS for Flex'
                        }
                    ],
                    {   
                        'build_version': '10.07.00.000000',
                        'developers': ['John Elderton', 'Weston Boyd', 'Thomas Lea'],
                        'gerrit_branch_name': 'release/10.7',
                        'gerrit_url': 'https://rdkgerrithub.stb.r53.xcal.tv/a/xhfw/core',
                        'inventory_board': 'Onsite_Rack_8_Board_3',
                        'nexus_url': 'https://nexus.comcast.com/nexus/service/rest/repository/browse/cpe-snapshots'
                    }
                ],
                expected=[
                    {
                        'branch_name': 'release/10.7', 
                        'build_number': '10.07.00.000000', 
                        'components': [], 
                        'inventory_board': 'Onsite_Rack_8_Board_3', 
                        'nexus_url': 'https://nexus.comcast.com/nexus/service/rest/repository/browse/cpe-snapshots',
                        'developers': ['Weston Boyd'],
                        'pagination': {'current_page': 0, 'page_size': 0, 'total_pages': 0, 'total_test_cases': ''}, 
                        'test_cycle': '', 'test_result': {
                            'failed_test_cases': '', 'passed_test_cases': '', 'unexecuted_test_cases': ''}, 
                        'jira_id': 'XHFW-1018', 
                        'git_logs': [
                            {
                                'author': {'email': 'weston_boyd@comcast.com', 'name': 'Weston Boyd'}, 
                                'commit': '8a6f24a21', 
                                'date': 'Mon Aug 9 18:45:20 2021 -0500', 
                                'filenames': ['source/utils/networkUtil/CMakeLists.txt', 
                                              'source/utils/networkUtil/src/main.c'], 
                                'package': '', 
                                'risk': 'Low', 
                                'summary': 'XHFW-1018 : xhNetworkUtil no custom DNS for Flex'
                            }
                        ]
                    },
                    {
                        'branch_name': 'release/10.7', 
                        'build_number': '10.07.00.000000', 
                        'components': [], 
                        'inventory_board': 'Onsite_Rack_8_Board_3', 
                        'nexus_url': 'https://nexus.comcast.com/nexus/service/rest/repository/browse/cpe-snapshots',
                        'developers': ['Thomas Lea'],
                        'pagination': {'current_page': 0, 'page_size': 0, 'total_pages': 0, 'total_test_cases': ''}, 
                        'test_cycle': '', 'test_result': {
                            'failed_test_cases': '', 'passed_test_cases': '', 'unexecuted_test_cases': ''}, 
                        'jira_id': 'XHFW-1080', 
                        'git_logs': [
                            {
                                'author': {'email': 'thoas_lea@comcast.com', 'name': 'Thomas Lea'}, 
                                'commit': '8a6f24a51', 
                                'date': 'Mon Aug 9 18:31:20 2021 -0500', 
                                'filenames': ['source/utils/networkUtil/CMakeLists.txt', 
                                              'source/utils/networkUtil/src/main.c'], 
                                'package': '', 
                                'risk': 'Very High', 
                                'summary': 'XHFW-1080 : xhNetworkUtil no custom DNS for Flex'
                            }
                        ]
                    }
                ]
            )
        ]
        
        for case in testcases:
            actual = update_execution_history.build_db_item(case.input[0], case.input[1])
            self.assertEqual(
                case.expected,
                actual,
                f'failed test {case.name} expected {case.expected}, actual {actual}'
            )

    def test_get_filenames(self):
        pass

    def test_build_dynamodb_payload(self):
        pass

    def test_update_dynamodb_table(self):
        @dataclass
        class TestCase:
            name: str
            input: list
            expected: str

        testcases = [
            TestCase(
                name='NO PAYLOAD',
                input=[],
                expected='Nothing to update'
            ),
            TestCase(
                name='VALID PAYLOAD - 1 ITEM', 
                input=[
                    {
                        "branch_name": "release/10.7",
                        "build_number": "10.07.00.000000",
                        "components": [

                        ],
                        "developers": [
                            "Weston Boyd"
                        ],
                        "git_logs": [
                            {
                            "author": {
                                "email": "weston_boyd@comcast.com",
                                "name": "Weston Boyd"
                            },
                            "commit": "8a6f24a21",
                            "date": "Mon Aug 9 18:45:20 2021 -0500",
                            "filenames": [
                                "source/utils/networkUtil/CMakeLists.txt",
                                "source/utils/networkUtil/src/main.c"
                            ],
                            "package": "",
                            "risk": "Low",
                            "summary": "XHFW-1018 : xhNetworkUtil no custom DNS for Flex"
                            }
                        ],
                        "inventory_board": "Onsite_Rack_8_Board_3",
                        "jira_id": "XHFW-1018",
                        "nexus_url": "https://nexus.comcast.com/nexus/service/rest/repository/browse/cpe-snapshots",
                        "pagination": {
                            "current_page": 0,
                            "page_size": 0,
                            "total_pages": 0,
                            "total_test_cases": ""
                        },
                        "test_cycle": "",
                        "test_result": {
                            "failed_test_cases": "",
                            "passed_test_cases": "",
                            "unexecuted_test_cases": ""
                        }
                    }
                ], 
                expected=f'Successfully added 1 item(s) to {self.repo_t_tables[1]["table_name"]} table.'
            ),
            TestCase(
                name='VALID PAYLOAD - 2 ITEMS', 
                input=[
                    {
                        "branch_name": "release/10.7",
                        "build_number": "10.07.00.000000",
                        "components": [

                        ],
                        "developers": [
                            "Weston Boyd"
                        ],
                        "git_logs": [
                            {
                            "author": {
                                "email": "weston_boyd@comcast.com",
                                "name": "Weston Boyd"
                            },
                            "commit": "8a6f24a21",
                            "date": "Mon Aug 9 18:45:20 2021 -0500",
                            "filenames": [
                                "source/utils/networkUtil/CMakeLists.txt",
                                "source/utils/networkUtil/src/main.c"
                            ],
                            "package": "",
                            "risk": "Low",
                            "summary": "XHFW-1018 : xhNetworkUtil no custom DNS for Flex"
                            }
                        ],
                        "inventory_board": "Onsite_Rack_8_Board_3",
                        "jira_id": "XHFW-1018",
                        "nexus_url": "https://nexus.comcast.com/nexus/service/rest/repository/browse/cpe-snapshots",
                        "pagination": {
                            "current_page": 0,
                            "page_size": 0,
                            "total_pages": 0,
                            "total_test_cases": ""
                        },
                        "test_cycle": "",
                        "test_result": {
                            "failed_test_cases": "",
                            "passed_test_cases": "",
                            "unexecuted_test_cases": ""
                        }
                    },
                    {
                        "branch_name": "release/10.7",
                        "build_number": "10.07.00.000000",
                        "components": [

                        ],
                        "developers": [
                            "Micah Koch"
                        ],
                        "git_logs": [
                            {
                            "author": {
                                "email": "micah_koch@comcast.com",
                                "name": "Micah Koch"
                            },
                            "commit": "8a6f24b21",
                            "date": "Mon Aug 12 18:45:20 2021 -0500",
                            "filenames": [
                                "source/utils/networkUtil/src/main.c"
                            ],
                            "package": "",
                            "risk": "High",
                            "summary": "XHFW-1080 : xhNetworkUtil no custom DNS for Flex"
                            }
                        ],
                        "inventory_board": "Onsite_Rack_8_Board_3",
                        "jira_id": "XHFW-1080",
                        "nexus_url": "https://nexus.comcast.com/nexus/service/rest/repository/browse/cpe-snapshots",
                        "pagination": {
                            "current_page": 0,
                            "page_size": 0,
                            "total_pages": 0,
                            "total_test_cases": ""
                        },
                        "test_cycle": "",
                        "test_result": {
                            "failed_test_cases": "",
                            "passed_test_cases": "",
                            "unexecuted_test_cases": ""
                        }
                    }
                ], 
                expected=f'Successfully added 2 item(s) to {self.repo_t_tables[1]["table_name"]} table.'
            )
        ]
        
        for case in testcases:
            actual = update_execution_history.update_dynamodb_table('Test_Repo_T_Execution_History', case.input)
            self.assertEqual(
                case.expected,
                actual,
                f'failed test {case.name} expected {case.expected}, actual {actual}'
            )

    
if __name__ == '__main__':
    unittest.main()
