import unittest
from dataclasses import dataclass
from typing import List
import parse_repo


class TestParseRepo(unittest.TestCase):
    """Tests for 'parse_repo.py'."""
    def test_search_git_log(self):
        @dataclass
        class TestCase:
            name: str
            input: List[str]
            expected: str

        regex = r'([a-zA-Z]+-\d+)'
        testcases = [
            TestCase(name='Empty subject', input=[regex, ''], expected=''),
            TestCase(name='Title Jira ID', input=[regex, 'Xhfw-1234: This is a test'], expected='XHFW-1234'),
            TestCase(name='lower Jira ID', input=[regex, 'xhfw-1234: This is a test'], expected='XHFW-1234'),
            TestCase(name='UPPER Jira ID', input=[regex, 'XHFW-1234: This is a test'], expected='XHFW-1234'),
            TestCase(name='no Jira ID', input=[regex, 'unit test file'], expected=''),
            TestCase(name='Partial Jira ID', input=[regex, 'XH1245 - unit test file'], expected=''),
            TestCase(name='No colon', input=[regex, 'XHFW-1234 unit test file'], expected='XHFW-1234'),
        ]

        for case in testcases:
            actual = parse_repo.search_git_log(case.input[0], case.input[1]).upper()
            self.assertEqual(
                case.expected,
                actual,
                f'failed test {case.name} expected {case.expected}, actual {actual}'
            )
