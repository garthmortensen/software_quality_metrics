from quality import strip_comments_and_blocks
# import pytest


def test_strip_comments_and_blocks():
    file_extension = ".py"

    sample_function_1 = """
def get_user_specified_models(file_path: str) -> list:
\"\"\"
read coordinated_data.json to find which models to include in the group run
and this\"\"\"
with open(file_path, "r") as file:
json_data = json.load(file)
# get all models to run
included = json_data["group_run"]["include"]
included_models = []
for key, value in included.items():
if value:
included_models.append(key)
return included_models
            """
    lines_list = sample_function_1.splitlines()

    sample_lines_of_code_1 = [
    'def get_user_specified_models(file_path: str) -> list:',
    'with open(file_path, "r") as file:',
    'json_data = json.load(file)',
    'included = json_data["group_run"]["include"]',
    'included_models = []',
    'for key, value in included.items():',
    'if value:',
    'included_models.append(key)',
    'return included_models',
    ]

    sample_lines_of_comment_1 = [
    '"""',
    'read coordinated_data.json to find which models to include in the group run',
    'and this"""',
    'with open(file_path, "r") as file:',
    'json_data = json.load(file)',
    '# get all models to run',
    ]


    assert strip_comments_and_blocks(lines_list, file_extension) == sample_lines_of_code_1, sample_lines_of_comment_1

