# https://learn.microsoft.com/en-us/visualstudio/code-quality/code-metrics-values?view=vs-2022

import os
import pandas as pd
from tabulate import tabulate  # for pretty print
import datetime  # for timestamp
import math  # for halstead

target_codepath = r"G:\My Drive\github\software_quality_metrics\scripts"  # update as needed
directories_to_skip = ["venv", "conda", "git", "renv"]  # update as needed
handled_extensions = (".py", ".r", ".sql")
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
module_directory = os.path.dirname(os.path.abspath(__file__))
code_metrics = {}

def read_and_strip_file(filepath):
    with open(filepath, 'r') as file:
        lines = file.readlines()

        # remove blank lines and lower case
        stripped_lines = []
        for line in lines:
            stripped_line = line.strip().lower()
            if stripped_line:
                stripped_lines.append(stripped_line)

    filename = os.path.basename(filepath).lower()
    file_extension = os.path.splitext(filename)[1].lower()
    
    # return a dictionary
    file_and_contents = {
        "filename": filename,
        "file_extension": file_extension,
        "lines": stripped_lines,
    }
    
    return file_and_contents


def split_into_code_lines_and_comment_lines(lines, file_extension):
    # code can be condensed to many lines, so line count isnt everything
    # readability matters!

    if file_extension == ".py":  # ISSUE: recognizes multiline strings as comments
        comment_indicator = ("#")
        comment_block_start = ("'''", '"""')
        comment_block_stop = ("'''", '"""')
    elif file_extension == ".r":
        comment_indicator = ("#")
        comment_block_start = ("'''", '"""')
        comment_block_stop = ("'''", '"""')
    elif file_extension == ".sql":
        comment_indicator = ("--")
        comment_block_start = ("/*")
        comment_block_stop = ("*/")
    else:
        print("Unhandled file extension")
        exit

    code_lines = []
    comment_lines = []
    in_comment_block = False
    previous_line = None  # placeholder before being called in loop

    for line in lines:
        # parsing python is difficult due to whitespace, no returns, many docstrings, etc. so wishy washy...
        # check for start of docstring
        if (previous_line is not None
            and "def " in previous_line 
            and (line == "'''" or line == '"""')):  # line contains only ''' appearing after def, we assume docstring begins
            in_comment_block = True
            comment_lines.append(line)
            continue
        # check for only triple quote appearing on line, not following a def statement
        elif (line == "'''" or line == '"""'):  # line contains only ''' appearing NOT after def, we ASSUME docstring ends
            in_comment_block = False
            comment_lines.append(line)
            continue
        # check for single line comment block
        elif line.startswith(comment_block_start) and line.endswith(comment_block_start):  # '''hello''' single line docstring
            in_comment_block = False
            comment_lines.append(line)
            continue
        # check for comment block start
        elif line.startswith(comment_block_start):
            in_comment_block = True
            comment_lines.append(line)
        # check for comment block end
        if in_comment_block:
            # which start and stop with the same string
            if line.endswith(comment_block_stop):
                in_comment_block = False
                # this prevents double appending a multiline comment blocks 
                # with starts AND ends with a multiline comments, e.g. /* hello world */
                if line not in comment_lines:
                    comment_lines.append(line)
            else:
                # this prevents double appending a multiline comment blocks 
                # with starts AND ends with a multiline comments, e.g. /* hello world */
                if line not in comment_lines:
                    comment_lines.append(line)
            continue

        # if not in a comment block, categorize as code or comment line
        if line.startswith(comment_indicator):
            comment_lines.append(line)
        elif line:
            code_lines.append(line)

        previous_line = line

    return code_lines, comment_lines


def extract_functions_py(lines):
    """shortcoming: the final function will include all following top level lines of code."""
    functions = []
    current_function = None
    current_function_lines = []

    for line in lines:  # the whole program
        # this whole block only captures function name
        if line.startswith("def "):

            # when first reaches def, None and skips this...
            if current_function:
                functions.append({
                    "function_name": current_function,
                    "function_lines": current_function_lines,
                })

            # ...then picks up function name
            current_function = line[4:].split("(")[0]  # transform "def meow(name: str) -> meow_name:" to "meow"
            current_function_lines = [line]
        elif current_function:
            current_function_lines.append(line)

    if current_function:
        functions.append({
            "function_name": current_function,
            "function_lines": current_function_lines,
        })

    return functions


def extract_functions_r(lines):
    functions = []
    current_function = None
    current_function_lines = []

    for line in lines:  # the whole program
        # this whole block only captures function name
        if ("function(" in line and "{" in line):

            # when first reaches def, None and skips this...
            if current_function:
                functions.append({
                    "function_name": current_function,
                    "function_lines": current_function_lines,
                })

            # ...then picks up function name
            current_function = line.split("<-")[0].strip()  # transform "meow <- function(name) {" to "meow"
            current_function_lines = [line]
        elif current_function:
            current_function_lines.append(line)

    if current_function:
        functions.append({
            "function_name": current_function,
            "function_lines": current_function_lines,
        })

    return functions


def extract_functions_sql(lines):
    functions = []

    functions.append({
        "function_name": "none",
        "function_lines": lines,
    })

    return functions


def extract_top_level_code(lines):
    top_level_code = {
        "function_name": "_FILE_TOTAL",  # _ so that it appears first after df sort
        "function_lines": lines,
    }
    return [top_level_code]


def count_lines_of_code(lines, file_extension):
    """
    loc_total excludes empty lines.
    loc_code includes first function assignment line, as well as returns.
    loc_comments includes code block start and end lines.
    """
    loc_total = len(lines)  # get total lines
    code_lines, comment_lines = split_into_code_lines_and_comment_lines(lines, file_extension)

    # handle for when functions are all comments (eg code stubs)
    if code_lines is None:
        loc_code = 0
    else:
        loc_code = len(code_lines)

    # handle for when functions are all code
    if comment_lines is None:
        comment_lines = 0
    else:
        loc_comments = len(comment_lines)

    loc = {
        "loc_total": loc_total,
        "loc_code": loc_code,
        "loc_comments": loc_comments,
    }
    print(loc)

    return loc


def calc_cyclomatic_complexity(lines, file_extension):
    # flat is better. Rotate python code 90 degrees counter clockwise, and the mountain range indicates challenge
    # check gitblame to see why complications are added
    # interpretation: https://radon.readthedocs.io/en/latest/commandline.html
    code_lines, comment_lines = split_into_code_lines_and_comment_lines(lines, file_extension)

    cyclomatic_complexity = 1  # base complexity

    # conditionally search for language specific control flow keywords
    if file_extension == ".py":
        # TODO: improve according to https://radon.readthedocs.io/en/latest/intro.html#cyclomatic-complexity
        control_flow_keywords = ("if ", "elif ", "for ", "while ", "except", "with ", 
                                 "assert ", "comprehension ", "and ", "or " "map(", "lambda ")
    elif file_extension == ".r" or file_extension == ".rmd": 
        control_flow_keywords = ("if ", "else if ", "while ", "for ")
    elif file_extension == ".sql":
        control_flow_keywords = ("select ", "from ", "where ", "join ", "inner join ", "left join ", "right join ", "outer join ", "union ", "except ", "intersect ")
    else:
        decision_points = ()

    for line in code_lines:

        decision_points = 0
        for control_flow_keyword in control_flow_keywords:
            decision_points += line.count(control_flow_keyword)

        cyclomatic_complexity += decision_points

    return cyclomatic_complexity

    
def calc_halstead_metrics(lines, file_extension):
    # halstead metrics been around 50 years
    # source: https://www.geeksforgeeks.org/software-engineering-halsteads-software-metrics/

    # operands = sum(values) + sum(variables)
    # operators = sum(operators)
    # length = operands + operators
    # vocabulary = distinct(operands) + distinct(operators)
    # volume = length x log2(vocab) = better than loc
    # difficulty = (distinct(operators) / 2) x (distinct(operands) / sum(operands)) = calulation of how youd reuse code and how much code you used to solve it
    # effort = volume x difficulty?

    N1_operators_total = list()
    N2_operands_total = list()  # lists are not distinct (total), which halstead equation requires

    operators = ['+', '-', '*', '/', '%', '=',  # arithmetic
                '==', '!=', '<', '>', '<=', '>=',  # comparisons
                'and ', '& ', 'or ', '| ',  'not ', '!',  # logic
                'if ', 'else ', 'while ', 'for ', 'def ', 'function ', 'return ',]  # keywords

    code_lines, comment_lines = split_into_code_lines_and_comment_lines(lines, file_extension)  # halstead ignores comments
    for line in code_lines:
        tokens = line.split()
        for token in tokens:
            if token in operators:
                N1_operators_total.append(token)
            elif token.isalnum():
                N2_operands_total.append(token)
            else:
                continue

    # use set to make distinct
    n1_operators_distinct = set(N1_operators_total)
    n2_operands_distinct = set(N2_operands_total)

    n_program_vocab = len(n1_operators_distinct) + len(n2_operands_distinct)  # total distinct
    N_program_len = len(N1_operators_total) + len(N2_operands_total)  # total
    v_volume = int(N_program_len * math.log(n_program_vocab, 2)) if n_program_vocab > 0 else 0  # does this indicate filesize?
    d_difficulty = (len(n1_operators_distinct) / 2) * (len(N2_operands_total) / len(n2_operands_distinct)) if len(n2_operands_distinct) > 0 else 0
    e_effort = int(d_difficulty * v_volume)  # good
    implement_time_t = int(e_effort / 18)  # good
    bugs_deliver_b = int((e_effort ** 2) / 3000)  # good

    halstead_metrics = {
        # total count of all operators, including duplicates
        # how many times operators are used overall in the code
        "n1_operators_distinct": len(n1_operators_distinct),
        # total count of all operands used in the code, including duplicates
        # how many times operands (variables or values) are used overall 
        "n2_operands_distinct": len(n2_operands_distinct),
        # count of unique operators (e.g., +, -, =, if)
        # how many different types of operations or actions are performed
        "N1_operators_total": len(N1_operators_total),
        # count of unique operands (e.g., variables, constants)
        # how many different variables, values, or data elements are used
        "N2_operands_total": len(N2_operands_total),
        # total length of the code, calculated as the sum of distinct operators and operands
        # total number of unique elements (operators and operands)
        "N_program_len": N_program_len,
        # total count of unique elements, calculated as the sum of distinct operators and operands
        # total number of different things (operators and operands)
        "n_program_vocab": n_program_vocab,
        # measure of the "size" or "complexity"
        # combines code length and the variety of elements used, giving an idea of code size
        "v_volume": v_volume,
        # complexity of understanding the code
        # how hard it is to understand the code based on the mix of unique operators and operands
        "d_difficulty": d_difficulty,
        # effort required to write or understand the code
        # work needed to deal with or create the code based on its complexity and size
        "e_effort": e_effort,
        # time to develop the code, typically measured in hours, days, or weeks
        "implement_time_t": implement_time_t,
        # number of defects/issues present in the code
        "bugs_deliver_b": bugs_deliver_b,
    }

    return halstead_metrics

def calc_maintainability(v_volume, cyclomatic_complexity, loc):
    A = 171
    B = 5.2
    C = 0.23
    D = 16.2

    # MS research
    # 00-25  = unmaintainable - single responsibility principal. no code should try to do everything. 
    # 25-30  = concerning
    # 50-75  = needs improvements. common in the real world
    # 75-100 = excellent

    # based on halstead metrics
    # more syntax/variables, more nesting, more code = unmaintainable
    # fewer syntax/vafiables, flat code, shorter code = maintainable
    maintainability_index = max(0, (A
                                    - (B * math.log(v_volume)) 
                                    - (C * cyclomatic_complexity) 
                                    - (D * math.log(loc))
                                    ) * 100 / A)

    # simplify bc who cares
    maintainability_index = int(maintainability_index)

    return maintainability_index


def extract_functions(file_contents, file_extension):
    """Extract functions from scripts, given file extension."""
    if file_extension == ".py":
        return extract_functions_py(file_contents)
    elif file_extension == ".r":
        return extract_functions_r(file_contents)
    elif file_extension == ".sql":
        return extract_functions_sql(file_contents)
    else:
        print(f"unhandled extension: {file_extension}")
        return []


def skippable_directory(directory_name):
    return directory_name in directories_to_skip


def collect_code_metrics(directory):

    code_metrics = []
    for root, dirs, files in os.walk(directory):

        # remove unwanted dirs from code scan
        filtered_dirs = []
        for dir in dirs:
            if dir not in directories_to_skip:
                filtered_dirs.append(dir)
        dirs[:] = filtered_dirs  # does not replace dirs, but rather updates it
        # this way, as os.walk continues traversal, it uses updates dirs list

        for each_file in files:
            if each_file.lower().endswith(handled_extensions):  # often you find .R, .SQL in the wild
                full_filepath = os.path.join(root, each_file)
                file_and_contents = read_and_strip_file(full_filepath)
                functions = extract_functions(file_and_contents["lines"], file_and_contents["file_extension"])

                for each_function in functions:
                    loc = count_lines_of_code(each_function["function_lines"], file_and_contents["file_extension"])
                    complexity = calc_cyclomatic_complexity(each_function["function_lines"], file_and_contents["file_extension"])
                    halstead_metrics = calc_halstead_metrics(each_function["function_lines"], file_and_contents["file_extension"])
                    maintainability_index =  calc_maintainability(halstead_metrics["v_volume"], complexity, loc["loc_code"])

                    code_metrics.append({
                        "run_timestamp": timestamp,
                        "filepath": os.path.dirname(full_filepath),
                        "file_extension": file_and_contents["file_extension"],
                        "filename": file_and_contents["filename"],
                        "function_name": each_function["function_name"],
                        **loc,  # this is called "dict unpacking"
                        "cyclocomplexity": complexity,
                        **halstead_metrics,
                        "maintainability_index": maintainability_index,
                    })

                # metrics for code not found inside functions, aka global or top level code
                top_level_code = extract_top_level_code(file_and_contents["lines"])
                loc_module = count_lines_of_code(top_level_code[0]["function_lines"], file_and_contents["file_extension"])
                complexity_module = calc_cyclomatic_complexity(top_level_code[0]["function_lines"], file_and_contents["file_extension"])
                halstead_metrics_module = calc_halstead_metrics(top_level_code[0]["function_lines"], file_and_contents["file_extension"])
                maintainability_index_module = calc_maintainability(halstead_metrics_module["v_volume"], complexity_module, loc_module["loc_code"])

                # this will append a fina row per script for top_level_code metrics
                code_metrics.append({
                    "run_timestamp": timestamp,
                    "filepath": os.path.dirname(full_filepath),
                    "file_extension": file_and_contents["file_extension"],
                    "filename": file_and_contents["filename"],
                    "function_name": top_level_code[0]["function_name"],
                    **loc_module,
                    "cyclocomplexity": complexity_module,
                    **halstead_metrics_module,
                    "maintainability_index": maintainability_index_module,
                })

    return code_metrics


code_metrics = collect_code_metrics(target_codepath)

# create df of metrics
df = pd.DataFrame.from_records(code_metrics)
desired_order = ["filepath", "file_extension", "filename", "function_name"]
df.sort_values(by=desired_order, inplace=True)
df.reset_index(drop=True, inplace=True)

print(tabulate(df, headers="keys", tablefmt="fancy_grid"))
output_path = os.path.join(module_directory, "output.csv")
df.to_csv(output_path, index=False)
