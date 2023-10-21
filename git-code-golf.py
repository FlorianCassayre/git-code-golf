import argparse
import datetime
from enum import Enum
import http.client
import json
import os
import shutil
import subprocess
import uuid

API_HOSTNAME = "code.golf"
API_ENDPOINT_EXPORT = "/golfer/export"

AUTHORIZATION_KEY = "__Host-session"

LANGUAGE_NAMES_EXTENSIONS = {
    "fish": ["><>", "fish"],
    "assembly": ["Assembly", "asm"],
    "awk": ["AWK", "awk"],
    "bash": ["Bash", "sh"],
    "basic": ["BASIC", "bas"],
    "Berry": ["Berry", "brr"],
    "brainfuck": ["Brainfuck", "bf"],
    "c": ["C", "c"],
    "c-sharp": ["C#", "cs"],
    "cpp": ["C++", "cpp"],
    "cobol": ["COBOL", "cob"],
    "crystal": ["Crystal", "cr"],
    "d": ["D", "d"],
    "dart": ["Dart", "dart"],
    "elixir": ["Elixir", "ex"],
    "f-sharp": ["F#", "fs"],
    "factor": ["Factor", "factor"],
    "forth": ["Forth", "fth"],
    "fortran": ["Fortran", "f"],
    "go": ["Go", "go"],
    "golfscript": ["GolfScript", "gs"],
    "haskell": ["Haskell", "hs"],
    "hexagony": ["Hexagony", "hxg"],
    "j": ["J", "ijs"],
    "janet": ["Janet", "janet"],
    "java": ["Java", "java"],
    "javascript": ["JavaScript", "js"],
    "julia": ["Julia", "jl"],
    "k": ["K", "k"],
    "lisp": ["Lisp", "lsp"],
    "lua": ["Lua", "lua"],
    "nim": ["Nim", "nim"],
    "ocaml": ["OCaml", "ml"],
    "pascal": ["Pascal", "pas"],
    "perl": ["Perl", "pl"],
    "php": ["PHP", "php"],
    "powershell": ["PowerShell", "ps1"],
    "prolog": ["Prolog", "pl"],
    "python": ["Python", "py"],
    "r": ["R", "r"],
    "raku": ["Raku", "raku"],
    "ruby": ["Ruby", "rb"],
    "rust": ["Rust", "rs"],
    "sed": ["sed", "sed"],
    "sql": ["SQL", "sql"],
    "swift": ["Swift", "swift"],
    "tcl": ["Tcl", "tcl"],
    "tex": ["TeX", "tex"],
    "v": ["V", "v"],
    "viml": ["VimL", "vim"],
    "wren": ["Wren", "wren"],
    "zig": ["Zig", "zig"]
}

DEFAULT_IGNORE_LIST = [".git", ".gitignore", ".github", "README.md", "LICENSE"]


class FileStructure(Enum):
    # javascript/fizz-buzz(-chars).js
    LANGUAGE_HOLE_EXTENSION = "lhe"
    # fizz-buzz/javascript(-chars).js
    HOLE_LANGUAGE_EXTENSION = "hle"
    # fizz-buzz/solution(-chars).js
    HOLE_SOLUTION_EXTENSION = "hse"
    # fizz-buzz(-chars).js
    HOLE_EXTENSION = "he"


def input_yes_no(prompt):
    while True:
        value = input(f"{prompt} [y/n]: ").lower()
        if value == "y" or value == "yes":
            return True
        elif value == "n" or value == "no":
            return False
        print("Please type [y]es or [n]o")


def is_valid_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


def get_solution_path(file_structure, hole_code, language_code, category):
    _, extension = LANGUAGE_NAMES_EXTENSIONS[language_code]
    category_suffix = f"-{category}" if category else ""
    if file_structure == FileStructure.LANGUAGE_HOLE_EXTENSION:
        return f"{language_code}/{hole_code}{category_suffix}.{extension}"
    elif file_structure == FileStructure.HOLE_LANGUAGE_EXTENSION:
        return f"{hole_code}/{language_code}{category_suffix}.{extension}"
    elif file_structure == FileStructure.HOLE_SOLUTION_EXTENSION:
        return f"{hole_code}/solution{category_suffix}.{extension}"
    elif file_structure == FileStructure.HOLE_EXTENSION:
        return f"{hole_code}{category_suffix}.{extension}"
    else:
        raise Exception


def export_data(authorization):
    if not is_valid_uuid(authorization):
        raise Exception(f"The provided authorization is not a valid UUID. Make sure that the value corresponds to '{AUTHORIZATION_KEY}'")
    connection = http.client.HTTPSConnection(API_HOSTNAME)
    headers = {
        "Cookie": f"{AUTHORIZATION_KEY}={authorization}",
    }
    connection.request("GET", API_ENDPOINT_EXPORT, headers=headers)
    response = connection.getresponse()
    if response.status == 200:
        response_data = response.read().decode("utf-8")
        return json.loads(response_data)
    else:
        print(f"Request failed with status code {response.status}")


def compute_final_state(file_structure, only_category, collapse_same_categories, data):
    solutions = data["solutions"]
    codes_per_solution = {}
    for solution in solutions:
        hole_code = solution["hole"]
        language_code = solution["lang"]
        code = solution["code"]
        key = (hole_code, language_code)
        if key not in codes_per_solution:
            codes_per_solution[key] = set()
        codes_per_solution[key].add(code)
    state = {}
    for solution in solutions:
        hole_code = solution["hole"]
        language_code = solution["lang"]
        category = solution["scoring"]
        date = solution["submitted"]
        code = solution["code"]
        unique = len(codes_per_solution[(hole_code, language_code)]) == 1
        if only_category is not None and only_category != category:
            continue
        path = get_solution_path(file_structure, hole_code, language_code, None if collapse_same_categories and unique and not only_category else category)
        if path in state and date <= state[path]["date"]:
            continue
        state[path] = {"content": code, "date": date}
    return state


def compute_changes(state, should_delete, output):
    to_delete = []
    files_to_update = []
    files_to_create = []
    directories_to_create = []

    def walk_recursive(current_directory, children):
        current_directory_files = os.listdir(current_directory) if os.path.exists(current_directory) else []

        explore = []

        needed = dict()
        for child in children:
            head = child["parts"][0]
            if head not in needed:
                needed[head] = []
            needed[head].append(child)
        all_files = sorted(set(current_directory_files).union(set(key for key in needed)))

        for file in all_files:
            file_path = os.path.join(current_directory, file)
            exists = os.path.exists(file_path)
            file_exists = os.path.isfile(file_path)
            directory_exists = os.path.isdir(file_path)
            is_needed = file in needed
            if is_needed:
                files_data = needed[file]
                is_directory = all(len(file_data["parts"]) > 1 for file_data in files_data)
                if is_directory:
                    if not exists:
                        directories_to_create.append(file_path)
                    elif not directory_exists:
                        if not should_delete:
                            raise Exception(f"{file_path} exists and is not a directory")
                        to_delete.append(file_path)
                        directories_to_create.append(file_path)
                    explore.append(file)
                else:
                    assert len(files_data) == 1
                    content = files_data[0]["content"]
                    entry = {"path": file_path, "content": content}
                    if not exists:
                        files_to_create.append(entry)
                    else:
                        if file_exists:
                            with open(file_path, "r") as f:
                                current_content = f.read()
                                if current_content != content:
                                    files_to_update.append(entry)
                        else:
                            if not should_delete:
                                raise Exception(f"{file_path} exists and is not a file")
                            to_delete.append(file_path)
                            files_to_create.append(entry)
            else:
                if should_delete and file not in DEFAULT_IGNORE_LIST:  # Can be improved
                    to_delete.append(file_path)

        for file in explore:
            walk_recursive(os.path.join(current_directory, file), [{**child, "parts": child["parts"][1:]} for child in needed[file]])

    walk_recursive(output, [{"parts": path.split("/"), "content": state[path]["content"]} for path in state])
    return {"to_delete": to_delete, "files_to_update": files_to_update, "files_to_create": files_to_create, "directories_to_create": directories_to_create}


def update_files(changes):
    to_delete = changes["to_delete"]
    files_to_update = changes["files_to_update"]
    files_to_create = changes["files_to_create"]
    directories_to_create = changes["directories_to_create"]

    for file in to_delete:
        if os.path.isdir(file):
            shutil.rmtree(file)  # Beware, can be dangerous if misused
        else:
            os.remove(file)
    for file in directories_to_create:
        os.mkdir(file)
    for file_data in files_to_update:
        with open(file_data["path"], "w") as f:
            f.write(file_data["content"])
    for file_data in files_to_create:
        with open(file_data["path"], "w") as f:
            f.write(file_data["content"])


def update_git(output):
    subprocess.run(["git", "add", "-A"], check=True, cwd=output)
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    commit_message = f"Update {current_date}"
    subprocess.run(["git", "commit", "-m", commit_message], check=True, cwd=output)


def main():
    parser = argparse.ArgumentParser(description="git-code-golf - version control your code.golf solutions")
    parser.add_argument("-a", "--authorization", required=True, help=f"Authorization ('{AUTHORIZATION_KEY}' cookie value)")
    parser.add_argument("-o", "--output", required=True, help="Output repository path")

    parser.add_argument("--structure", help="The file structure to use", type=FileStructure, choices=[e.value for e in FileStructure], default=FileStructure.LANGUAGE_HOLE_EXTENSION)
    parser.add_argument("--only-scoring", help="If set, only this scoring metric will be kept", choices=["bytes", "chars"], default=None)
    parser.add_argument("--no-scoring-name", help="Drop the scoring metric if there are no ambiguities", action=argparse.BooleanOptionalAction, default=False)

    parser.add_argument("--no-git", help="Disable version control (files will be modified but not committed)", action=argparse.BooleanOptionalAction, default=False)

    parser.add_argument("--no-delete", help="Disable the deletion of files", action=argparse.BooleanOptionalAction, default=False)

    parser.add_argument("--no-interactive", help="Disable confirmation prompts", action=argparse.BooleanOptionalAction, default=False)

    parser.add_argument("--dry-run", help="Preview the changes", action=argparse.BooleanOptionalAction, default=False)

    args = parser.parse_args()

    authorization = args.authorization
    output_path = args.output

    structure = args.structure
    only_scoring = args.only_scoring
    no_scoring_name = args.no_scoring_name
    no_git = args.no_git
    no_delete = args.no_delete
    no_interactive = args.no_interactive
    dry_run = args.dry_run

    if not no_git and not os.path.exists(os.path.join(output_path, ".git")):
        raise Exception(f"The root directory {output_path} doesn't appear to be a git repository")

    print("Exporting data...")
    data = export_data(authorization)
    print("Computing diff...")
    state = compute_final_state(structure, only_scoring, not no_scoring_name, data)
    changes = compute_changes(state, not no_delete, output_path)

    to_delete = changes["to_delete"]
    files_to_update = changes["files_to_update"]
    files_to_create = changes["files_to_create"]
    directories_to_create = changes["directories_to_create"]

    if len(to_delete) == 0 and len(files_to_update) == 0 and len(files_to_create) == 0 and len(directories_to_create) == 0:
        print("Everything is already up to date.")
    else:
        print("Files and directories that will be deleted:")
        print("\n".join(to_delete))
        print("Directories that will be created:")
        print("\n".join(directories_to_create))
        print("Files that will be updated:")
        print("\n".join(file["path"] for file in files_to_update))
        print("Files that will be created:")
        print("\n".join(file["path"] for file in files_to_create))

        if not no_interactive and not input_yes_no("Would you like to proceed?"):
            exit(1)

        print("Updating files...")
        if not dry_run:
            update_files(changes)

        if not no_git:
            print("Committing changes...")
            if not dry_run:
                update_git(output_path)

        print("Done.")


if __name__ == "__main__":
    main()
