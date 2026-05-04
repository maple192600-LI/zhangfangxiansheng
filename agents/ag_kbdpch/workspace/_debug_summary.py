
import sys
sys.path.insert(0, '/workspace/skills/parse_boc')
import run as parser
import inspect

# Print _generate_summary source
print(inspect.getsource(parser._generate_summary))
print("\n=====\n")
print(inspect.getsource(parser._is_code))
print("\n=====\n")
print(inspect.getsource(parser._is_date_range))
