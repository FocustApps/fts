import json
import base64
import logging
from typing import Iterable, List
from pathlib import Path
from urllib import response
from datetime import datetime

# Fenrir becomes /s/ in CI
PARENT_DIR_NAMES = ["Fenrir", "fenrir", "s", "FTS", "fts"]


def get_project_root(target_directory: str | None = None) -> Path:
    """
    Returns the Path to the Fenrir project root directory.
    """
    current_path = Path(__file__).resolve()
    if target_directory:
        for parent in current_path.parents:
            if parent.name == target_directory:
                return parent

    for parent in current_path.parents:
        if parent.name in PARENT_DIR_NAMES:
            return parent
    raise RuntimeError(f"Fenrir project root directory not found. \n {current_path}")


def get_subdirectories(
    directory: str = "tests",
    exclusions: List[str] = ["develop", "__pycache__", "test_data"],
) -> List[str]:
    dir_path = get_project_root() / directory
    subdirectories = [
        str(path.relative_to(dir_path))
        for path in dir_path.glob("*")
        if path.is_dir() and path.name not in exclusions
    ]
    return subdirectories


def get_files_from_dir(directory: str, test_dir: str = "tests") -> List[str]:
    """
    Get all files from a directory in the tests folder unless specified otherwise.
    Only finds files in the project root /fenrir/ and will only find files
    that start with "test_" and end with ".py"
    """
    tests_dir = get_project_root() / test_dir / directory
    file_tree = []
    logging.info("Getting files from: %s", tests_dir)
    for path in tests_dir.glob("**/*"):
        if path.is_file() and path.name.startswith("test_") and path.name.endswith(".py"):
            file_tree.append(str(path.relative_to(tests_dir)).rsplit("/", maxsplit=1))
    return file_tree


def find_file_path(file_name: str, test_dir: str = "tests"):
    """
    Find the path of a file in the tests directory.
    """
    tests_dir = get_project_root() / test_dir
    for path in tests_dir.glob("**/*"):
        if path.is_file() and path.name == file_name:
            return tests_dir / path.relative_to(tests_dir)
    raise FileNotFoundError(f"Could not find file: {file_name}")


def load_json_from_file(file_path: str) -> dict:
    """
    Load a JSON file from a file path.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def serialized_file_content(file_to_serialize: str) -> str:
    """
    Serialize a file into a string.
    """
    with open(file_to_serialize, "rb") as file:
        img = file.read()
    return base64.encodebytes(img).decode("utf-8")


# TODO:
# Make this function work for tests that fail.
def curl_output_request():
    req = response.request
    command = "curl -X {method} -H {headers} -d '{data}' '{uri}'"
    method = req.method
    uri = req.url
    data = req.body
    headers = ['"{0}: {1}"'.format(k, v) for k, v in req.headers.items()]
    headers = " -H ".join(headers)
    return command.format(method=method, headers=headers, data=data, uri=uri)


def reformat_date(
    date: str,
    current_format: str = "%Y-%m-%d",
    desired_format: str = "%m/%d/%Y",
) -> str:
    stripped_date = datetime.strptime(date, current_format)
    return stripped_date.strftime(desired_format)


def create_pdf_file(file_path: str, attachment_data: Iterable[bytes]) -> str:
    with open(file_path, "wb") as file:
        for chunk in attachment_data:
            file.write(chunk)
    return file_path
