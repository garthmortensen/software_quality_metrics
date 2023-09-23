import sqlite3
import os
import json
import getpass  # db field
from datetime import datetime  # timestamp
import subprocess  # to run rscript

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
print(ascii)
print("  The orchestra commences!\n")
line_seperator = "  " + 26 * "~"

print(line_seperator)
effective = datetime.now().strftime("%Y%m%d%H%M%S")
print(f"  effective: {effective}")

all_models = [
    "r_energy.R",
    "r_concrete.R",
    "r_lumber.R",
    "r_paint.R",
    "r_shingles.R",
    "r_steel.R",
    "r_calculate.R",
]


def get_relative_cwd() -> str:
    """find script directory"""
    current_working_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_working_dir)

    return parent_dir


def increment_group_id(database_name, table: str) -> int:
    """get the next group id as max(group_id)+1, in order to create unique counter"""
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()
    query = f"select distinct max(group_id) from {table}"
    cursor.execute(query)
    result = cursor.fetchone()[0]  # fetch first row
    conn.close()
    result += 1
    print(f"  incremented group_id = {result}")
    return result


def get_user_specified_models(file_path: str) -> list:
    """read coordinated_data.json to find which models to include in the group run"""
    with open(file_path, "r") as file:
        json_data = json.load(file)

    # get all models to run
    included = json_data["group_run"]["include"]
    included_models = []
    for key, value in included.items():
        if value:
            included_models.append(key)

    return included_models


def insert_queued_models(
    database_name: str,
    table: str,
    next_group_id: int,
    effective: str,
    model_status: str,
    included_models: list,
) -> None:
    """after pulling from coordinated_data.json, we populate coordinate table"""
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()

    whoami = "dog"  # getpass.getuser()
    today = datetime.today().strftime("%Y-%m-%d")

    for included_model in included_models:
        query = f"""
            insert into {table} (group_id, date, model, effective, whoami, status) values
            ({next_id}, '{today}', '{included_model}', '{effective}', '{whoami}', '{model_status}')
        """
        cursor.execute(query)

    conn.commit()
    conn.close()


def update_queued_model_as_complete(
    database_name: str,
    table: str,
    group_id: int,
    effective: str,
    model: str,
    model_status: str,
) -> None:
    """after pulling from setup.json, we update coordinate table"""

    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()

    whoami = "dog"  # getpass.getuser()

    query = f"""
        update {table}
        set status = '{model_status}'
        where group_id = {group_id} and model = '{model}'
    """
    cursor.execute(query)

    conn.commit()
    conn.close()


def group_models_inserted_into_database(
    database_name: str, next_id: int, table: str
) -> list:
    """select distinct models based on group_id and whoami conditions"""
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()

    whoami = "dog"  # getpass.getuser()

    query = f"""
        select distinct model
        from {table}
        where group_id = {next_id}
        and whoami = '{whoami}'
    """
    cursor.execute(query)
    distinct_models = [row[0] for row in cursor.fetchall()]  # fetch all rows
    conn.close()

    return distinct_models


# increment group_id
rel_cwd = get_relative_cwd()
db_path = os.path.join(rel_cwd, "standup_db", "costs.db")
next_id = increment_group_id(db_path, "coordinated")

# get models to include in run from json array
coordinated_data_path = os.path.join(
    rel_cwd, "data", "coordinated", "coordinated_data.json"
)
included_models = get_user_specified_models(coordinated_data_path)

# insert queued models into db table
insert_queued_models(
    db_path, "coordinated", next_id, effective, "queued", included_models
)

# get models included in run
distinct_models = group_models_inserted_into_database(db_path, next_id, "coordinated")
print(f"  SELECT grouped models: {distinct_models}")

print(line_seperator)

for distinct_model in distinct_models:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    whoami = "dog"  # getpass.getuser()

    # get grouped model status to ensure it hasnt run yet
    query_coord = f"""
        select status
        from coordinated
        where 1=1
            and model = '{distinct_model}'
            and effective = '{effective}'
            and whoami = '{whoami}'
    """

    cursor.execute(query_coord)
    row = cursor.fetchone()
    # check if row exists before accessing value
    model_status = row[0] if row else None
    print(f"\n  {distinct_model}: {model_status}")

    if model_status == "completed":
        print(f"  Model distinct_model status: {model_status}")
    elif model_status == "queued":
        # kick off model
        model_path = os.path.join(rel_cwd, "scripts", f"r_{distinct_model}.R")
        print(f"  Rscript {model_path}")

        # process = subprocess.Popen(["Rscript", model_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        process = subprocess.Popen(
            ["Rscript", model_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=rel_cwd,
            universal_newlines=True,
        )
        for line in process.stdout:
            print(line.strip())

        # now that model is complete, update coordinate table
        update_queued_model_as_complete(
            db_path, "coordinated", next_id, effective, distinct_model, "complete"
        )
        print(f"\n  {distinct_model}: complete!")
    else:
        # unexpected event
        update_queued_model_as_complete(
            db_path, "coordinated", next_id, effective, distinct_model, "error"
        )

print("\n  The orchestra concludes.")
print(line_seperator)
print("\n")


# NEXT SCOURGIFY!!!
