import os
import pandas as pd
import datetime  # for timestamp
import math  # for halstead

from tabulate import tabulate  # for pretty print


class FileReader:
    def read_and_strip_file(self, filepath: str) -> dict:
        """
        Reads a file, strips its lines, and returns a list of results.

        Args:
            filepath (str): The path to the file to be read.

        Returns:
            dict: A dictionary containing the following keys:
                - 'filename' (str): The lowercased name of the file.
                - 'file_extension' (str): The lowercased file extension.
                - 'lines' (list): A list of stripped and lowercased lines from the file.
        """
        with open(filepath, "r") as file:
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


class CodeSplitter:
    def split_into_code_lines_and_comment_lines(
        self, lines: list, file_extension: str
    ) -> tuple:
        """
        Analyzes a list of lines and categorizes them into code lines and comment lines
        based on the provided file extension. It supports various file extensions and handles both
        single-line and multi-line comments.

        Args:
            lines (list): The list of lines to be analyzed.
            file_extension (str): The file extension of the code to determine the comment style.

        Returns:
            tuple: A tuple containing two lists - code lines and comment lines.

        Example:
            splitter = CodeSplitter()
            code_lines, comment_lines = splitter.split_into_code_lines_and_comment_lines(file_lines, ".py")
        """
        # code can be condensed to many lines, so line count isnt everything
        # readability matters!

        if file_extension == ".py":  # ISSUE: recognizes multiline strings as comments
            comment_indicator = "#"
            comment_block_start = ("'''", '"""')
            comment_block_stop = ("'''", '"""')
        elif file_extension == ".r":
            comment_indicator = "#"
            comment_block_start = ("'''", '"""')
            comment_block_stop = ("'''", '"""')
        elif file_extension == ".sql":
            comment_indicator = "--"
            comment_block_start = "/*"
            comment_block_stop = "*/"
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
            if (
                previous_line is not None
                and "def " in previous_line
                and (line == "'''" or line == '"""')
            ):  # line contains only ''' appearing after def, we assume docstring begins
                in_comment_block = True
                comment_lines.append(line)
                continue
            # check for only triple quote appearing on line, not following a def statement
            elif (
                line == "'''" or line == '"""'
            ):  # line contains only ''' appearing NOT after def, we ASSUME docstring ends
                in_comment_block = False
                comment_lines.append(line)
                continue
            # check for single line comment block
            elif line.startswith(comment_block_start) and line.endswith(
                comment_block_start
            ):  # '''hello''' single line docstring
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


class FunctionExtractor:
    def extract_functions(self, lines: list, file_extension: str):
        """
        Extracts functions from the given lines based on the file extension.

        Args:
            lines (list): The list of lines to extract functions from.
            file_extension (str): The file extension used to determine the programming language.

        Returns:
            A list of dictionaries, each containing:
                - 'function_name' (str): The name of the extracted function.
                - 'function_lines' (list): The lines of code belonging to the function.

        Example:
            extractor = FunctionExtractor()
            functions = extractor.extract_functions(lines, ".py")

        Note:
            Returns an empty list for unsupported file extensions.
        """
        if file_extension == ".py":
            return self.extract_functions_py(lines)
        elif file_extension == ".r":
            return self.extract_functions_r(lines)
        elif file_extension == ".sql":
            return self.extract_functions_sql(lines)
        else:
            return []

    def extract_top_level_code(self, lines):
        top_level_code = {
            "function_name": "_FILE_TOTAL",  # _ so that it appears first after df sort
            "function_lines": lines,
        }
        return [top_level_code]

    def extract_functions_py(self, lines):
        """shortcoming: the final function will include all following top level lines of code."""
        functions = []
        current_function = None
        current_function_lines = []

        for line in lines:  # the whole program
            # this whole block only captures function name
            if line.startswith("def "):
                # when first reaches def, None and skips this...
                if current_function:
                    functions.append(
                        {
                            "function_name": current_function,
                            "function_lines": current_function_lines,
                        }
                    )

                # ...then picks up function name
                current_function = line[4:].split("(")[
                    0
                ]  # transform "def meow(name: str) -> meow_name:" to "meow"
                current_function_lines = [line]
            elif current_function:
                current_function_lines.append(line)

        if current_function:
            functions.append(
                {
                    "function_name": current_function,
                    "function_lines": current_function_lines,
                }
            )

        return functions

    def extract_functions_r(self, lines):
        functions = []
        current_function = None
        current_function_lines = []

        for line in lines:  # the whole program
            # this whole block only captures function name
            if "function(" in line and "{" in line:
                # when first reaches def, None and skips this...
                if current_function:
                    functions.append(
                        {
                            "function_name": current_function,
                            "function_lines": current_function_lines,
                        }
                    )

                # ...then picks up function name
                current_function = line.split("<-")[
                    0
                ].strip()  # transform "meow <- function(name) {" to "meow"
                current_function_lines = [line]
            elif current_function:
                current_function_lines.append(line)

        if current_function:
            functions.append(
                {
                    "function_name": current_function,
                    "function_lines": current_function_lines,
                }
            )

        return functions

    def extract_functions_sql(self, lines):
        functions = []

        functions.append(
            {
                "function_name": "none",
                "function_lines": lines,
            }
        )

        return functions


class CodeMetricsCalculator:
    def __init__(self):
        self.code_splitter = CodeSplitter()  # create an instance of CodeSplitter

    def count_lines_of_code(self, lines, file_extension):
        """
        loc_total excludes empty lines.
        loc_code includes first function assignment line, as well as returns.
        loc_comments includes code block start and end lines.
        """
        loc_total = len(lines)  # get total lines
        code_splitter = CodeSplitter()
        (
            code_lines,
            comment_lines,
        ) = self.code_splitter.split_into_code_lines_and_comment_lines(
            lines, file_extension
        )

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

    def calc_cyclomatic_complexity(self, lines, file_extension):
        # flat is better. Rotate python code 90 degrees counter clockwise, and the mountain range indicates challenge
        # check gitblame to see why complications are added
        # interpretation: https://radon.readthedocs.io/en/latest/commandline.html
        (
            code_lines,
            comment_lines,
        ) = self.code_splitter.split_into_code_lines_and_comment_lines(
            lines, file_extension
        )

        cyclomatic_complexity = 1  # base complexity

        # conditionally search for language specific control flow keywords
        if file_extension == ".py":
            # TODO: improve according to https://radon.readthedocs.io/en/latest/intro.html#cyclomatic-complexity
            control_flow_keywords = (
                "if ",
                "elif ",
                "for ",
                "while ",
                "except",
                "with ",
                "assert ",
                "comprehension ",
                "and ",
                "or " "map(",
                "lambda ",
            )
        elif file_extension == ".r" or file_extension == ".rmd":
            control_flow_keywords = ("if ", "else if ", "while ", "for ")
        elif file_extension == ".sql":
            control_flow_keywords = (
                "select ",
                "from ",
                "where ",
                "join ",
                "inner join ",
                "left join ",
                "right join ",
                "outer join ",
                "union ",
                "except ",
                "intersect ",
            )
        else:
            decision_points = ()

        for line in code_lines:
            decision_points = 0
            for control_flow_keyword in control_flow_keywords:
                decision_points += line.count(control_flow_keyword)

            cyclomatic_complexity += decision_points

        return cyclomatic_complexity

    def calc_halstead_metrics(self, lines, file_extension):
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
        N2_operands_total = (
            list()
        )  # lists are not distinct (total), which halstead equation requires

        operators = [
            "+",
            "-",
            "*",
            "/",
            "%",
            "=",  # arithmetic
            "==",
            "!=",
            "<",
            ">",
            "<=",
            ">=",  # comparisons
            "and ",
            "& ",
            "or ",
            "| ",
            "not ",
            "!",  # logic
            "if ",
            "else ",
            "while ",
            "for ",
            "def ",
            "function ",
            "return ",
        ]  # keywords

        (
            code_lines,
            comment_lines,
        ) = self.code_splitter.split_into_code_lines_and_comment_lines(
            lines, file_extension
        )  # halstead ignores comments
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

        n_program_vocab = len(n1_operators_distinct) + len(
            n2_operands_distinct
        )  # total distinct
        N_program_len = len(N1_operators_total) + len(N2_operands_total)  # total
        v_volume = (
            int(N_program_len * math.log(n_program_vocab, 2))
            if n_program_vocab > 0
            else 0
        )  # does this indicate filesize?
        d_difficulty = (
            round(
                (len(n1_operators_distinct) / 2)
                * (len(N2_operands_total) / len(n2_operands_distinct)),
                2,
            )
            if len(n2_operands_distinct) > 0
            else 0
        )
        e_effort = int(d_difficulty * v_volume)  # good
        implement_time_t = int(e_effort / 18)  # good
        bugs_deliver_b = int((e_effort**2) / 3000)  # good

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

    def calc_maintainability(self, v_volume, cyclomatic_complexity, loc):
        # https://learn.microsoft.com/en-us/visualstudio/code-quality/code-metrics-values?view=vs-2022

        # MS Research magic numbers
        A = 171
        B = 5.2
        C = 0.23
        D = 16.2

        # based on halstead metrics
        # more syntax/variables, more nesting, more code = unmaintainable
        # fewer syntax/vafiables, flat code, shorter code = maintainable
        maintainability_index = int(
            max(
                0,
                (
                    A
                    - (B * math.log(v_volume))
                    - (C * cyclomatic_complexity)
                    - (D * math.log(loc))
                )
                * 100
                / A,
            )
        )

        # 00-25  = unmaintainable - single responsibility principal. no code should try to do everything.
        # 25-30  = concerning
        # 50-75  = needs improvements. common in the real world
        # 75-100 = excellent
        return maintainability_index


class CodeAnalyzer:
    # instantiate
    def __init__(self, target_codepath, directories_to_skip, handled_extensions):
        self.target_codepath = target_codepath
        self.directories_to_skip = directories_to_skip
        self.handled_extensions = handled_extensions
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.module_directory = os.path.dirname(os.path.abspath(__file__))
        self.code_metrics = []
        # composition. this class is composed of many others. more flexible and maintainable than inheritance
        self.file_reader = FileReader()  # create an instance of FileReader
        self.function_extractor = (
            FunctionExtractor()
        )  # create an instance of FunctionExtractor
        self.code_metric_calculator = CodeMetricsCalculator()

    def extract_functions(self, file_contents, file_extension):
        """Extract functions from scripts, given file extension."""
        if file_extension == ".py":
            return self.function_extractor.extract_functions_py(file_contents)
        elif file_extension == ".r":
            return self.function_extractor.extract_functions_r(file_contents)
        elif file_extension == ".sql":
            return self.function_extractor.extract_functions_sql(file_contents)
        else:
            print(f"unhandled extension: {file_extension}")
            return []

    def skippable_directory(self, directory_name):
        return directory_name in directories_to_skip

    def collect_code_metrics(self, directory):
        code_metrics = []
        for root, dirs, files in os.walk(directory):
            filtered_dirs = self.filter_directories(dirs)
            dirs[:] = filtered_dirs

            for each_file in files:
                if each_file.lower().endswith(self.handled_extensions):
                    full_filepath = os.path.join(root, each_file)
                    file_and_contents = self.file_reader.read_and_strip_file(
                        full_filepath
                    )
                    functions = self.extract_functions(file_and_contents)

                    code_metrics.extend(
                        self.calculate_metrics(
                            full_filepath, file_and_contents, functions
                        )
                    )

        return code_metrics

    def filter_directories(self, dirs):
        return [dir for dir in dirs if dir not in self.directories_to_skip]

    def extract_functions(self, file_and_contents):
        return self.function_extractor.extract_functions(
            file_and_contents["lines"], file_and_contents["file_extension"]
        )

    def calculate_metrics(self, full_filepath, file_and_contents, functions):
        code_metrics = []

        for function in functions:
            loc = self.code_metric_calculator.count_lines_of_code(
                function["function_lines"], file_and_contents["file_extension"]
            )
            complexity = self.code_metric_calculator.calc_cyclomatic_complexity(
                function["function_lines"], file_and_contents["file_extension"]
            )
            halstead_metrics = self.code_metric_calculator.calc_halstead_metrics(
                function["function_lines"], file_and_contents["file_extension"]
            )
            maintainability_index = self.calculate_maintainability(
                halstead_metrics, complexity, loc
            )

            code_metrics.append(
                {
                    "run_timestamp": self.timestamp,
                    "filepath": os.path.dirname(full_filepath),
                    "file_extension": file_and_contents["file_extension"],
                    "filename": file_and_contents["filename"],
                    "function_name": function["function_name"],
                    **loc,
                    "cyclocomplexity": complexity,
                    **halstead_metrics,
                    "maintainability_index": maintainability_index,
                }
            )

        # code_metrics += self.calculate_top_level_metrics(full_filepath, file_and_contents)
        code_metrics.extend(
            self.calculate_top_level_metrics(full_filepath, file_and_contents)
        )
        return code_metrics

    def calculate_maintainability(self, halstead_metrics, complexity, loc):
        return self.code_metric_calculator.calc_maintainability(
            halstead_metrics["v_volume"], complexity, loc["loc_code"]
        )

    def calculate_top_level_metrics(self, full_filepath, file_and_contents):
        top_level_code = self.function_extractor.extract_top_level_code(
            file_and_contents["lines"]
        )
        loc_module = self.code_metric_calculator.count_lines_of_code(
            top_level_code[0]["function_lines"], file_and_contents["file_extension"]
        )
        complexity_module = self.code_metric_calculator.calc_cyclomatic_complexity(
            top_level_code[0]["function_lines"], file_and_contents["file_extension"]
        )
        halstead_metrics_module = self.code_metric_calculator.calc_halstead_metrics(
            top_level_code[0]["function_lines"], file_and_contents["file_extension"]
        )
        maintainability_index_module = self.calculate_maintainability(
            halstead_metrics_module, complexity_module, loc_module
        )

        return [
            {
                "run_timestamp": self.timestamp,
                "filepath": os.path.dirname(full_filepath),
                "file_extension": file_and_contents["file_extension"],
                "filename": file_and_contents["filename"],
                "function_name": top_level_code[0]["function_name"],
                **loc_module,
                "cyclocomplexity": complexity_module,
                **halstead_metrics_module,
                "maintainability_index": maintainability_index_module,
            }
        ]

    def run_analysis(self, target_codepath):
        code_metrics = self.collect_code_metrics(target_codepath)

        # create df
        df = pd.DataFrame.from_records(code_metrics)
        desired_order = ["filepath", "file_extension", "filename", "function_name"]
        df.sort_values(by=desired_order, inplace=True)
        df.reset_index(drop=True, inplace=True)

        # print and write to csv
        print(tabulate(df, headers="keys", tablefmt="fancy_grid"))
        output_path = os.path.join(self.module_directory, "output.csv")
        df.to_csv(output_path, index=False)


if __name__ == "__main__":
    target_codepath = (
        r"G:\My Drive\github\software_quality_metrics\scripts"  # update as needed
    )
    directories_to_skip = ["venv", "conda", "git", "renv"]  # update as needed
    handled_extensions = (".py", ".r", ".sql")

    analyzer = CodeAnalyzer(target_codepath, directories_to_skip, handled_extensions)
    analyzer.run_analysis(target_codepath)
