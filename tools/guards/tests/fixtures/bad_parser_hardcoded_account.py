# bad_parser_hardcoded_account.py
# Negative fixture: hardcoded DEFAULT_ACCOUNT_CODE and entity_code
# check_parser_hardcoding.py should reject this file.

DEFAULT_ACCOUNT_CODE = "A001"
DEFAULT_ENTITY_CODE = "E001"


def parse(wb, ctx):
    return [{"account_code": "A001", "entity_code": "E001"}]
