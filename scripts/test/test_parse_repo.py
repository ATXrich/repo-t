import re
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
            input: List[any]
            expected: str

        regex = r'([a-zA-Z]+-\d+)'
        testcases = [
            TestCase(name="Empty subject", input=[regex, {"commit": "a1254", "subject": "", "body": ""}], expected=""),
            # TestCase(name="Title Jira ID", input=[regex, {"subject": "Xhfw-1234: This is a test"}], expected="XHFW-1234"),
            # TestCase(name="lower Jira ID", input=[regex, {"subject": "xhfw-1234: This is a test"}], expected="XHFW-1234"),
            # TestCase(name="UPPER Jira ID", input=[regex, {"subject": "XHFW-1234: This is a test"}], expected="XHFW-1234"),
            # TestCase(name="no Jira ID", input=[regex, {"subject": "This is a test"}], expected=""),
        ]

        for case in testcases:
            actual = parse_repo.search_git_log(case.input[0], case.input[1])
            self.assertEqual(
                case.expected,
                actual,
                f'failed test {case.name} expected {case.expected}, actual {actual}'
            )