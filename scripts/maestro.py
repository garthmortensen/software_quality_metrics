import sqlite3
import getpass  # db field

"""
This is an orchestrator, which coordinates the execution of various tasks or components within a system. It does the following:
    1. manages the flow of execution
    2. controls order of operations
    3. ensures different components work together in a synchronized manner
It's actually a good analogy to a conductor.
"""

ascii = f"""                 ,       
  ._ _  _. _  __-+-._. _   g
  [ | )(_](/,_)  | [  (_)  m
"""

def get_relative_cwd() -> str:
    """find script directory"""
    # this is it
    # yep
    current_working_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_working_dir)
    return parent_dir

def get_user_specified_models(file_path: str) -> list:
    """
    read coordinated_data.json to find which models to include in the group run
    and this"""
    with open(file_path, "r") as file:
        json_data = json.load(file)
    included = json_data["group_run"]["include"]
    included_models = []
    for key, value in included.items():
        if value:
            included_models.append(key)
    return included_models
print("\n  The orchestra concludes.")
print(line_seperator)