#!/usr/bin/env python3
"""
This file will update the static files used by the API. It will download the specified
versions of htmx, jQuery, and Bootstrap based on the environment variables set in the
system PLUS the config/app.json file. In order to run this script, you must update the
app.json file with the versions of the static files you want to use AND the envars.
I wanted to use double verification ensure that updates will not happen on accident.
"""

import os
from typing import List
import requests
import zipfile

from app.config import get_base_app_config, BaseAppConfig
from app.utils import get_project_root

BASE_APP_CONFIG = get_base_app_config()


def update_file(url: str, target_dir, file_name: str):
    # Make the request to download the file
    try:
        response = requests.get(url)
        response.raise_for_status()  # Ensure we notice bad responses
    except requests.exceptions.RequestException as e:
        print(f"Failed to download {url}: {e}")
        exit(1)

    # Save the file to a temporary location
    try:
        with open(f"{get_project_root()}/{target_dir}/{file_name}", "wb") as file:
            file.write(response.content)
    except Exception as e:
        print(f"Failed to save {file_name}: {e}")
        exit(1)


def update_bootstrap_dependency(bootstrap_version: str):
    url = f"https://github.com/twbs/bootstrap/releases/download/v{bootstrap_version}/bootstrap-{bootstrap_version}-dist.zip"
    file_name = "bootstrap.zip"
    temp_file_path = f"{get_project_root()}/{file_name}"

    target_js_dir = "/app/static/js"
    target_css_dir = "/app/static/css"

    def download_bootstrap_zip():
        # Make the request to download the file
        try:
            response = requests.get(url)
            response.raise_for_status()  # Ensure we notice bad responses
        except requests.exceptions.RequestException as e:
            print(f"Failed to download {url}: {e}")
            exit(1)

        # Save the file to a temporary location
        try:
            with open(temp_file_path, "wb") as file:
                file.write(response.content)
        except Exception as e:
            print(f"Failed to save {file_name}: {e}")
            exit(1)

    def extract_and_remove():
        # Unzip the file
        try:
            with zipfile.ZipFile(temp_file_path, "r") as zip_ref:
                print(f"Extracting to {temp_file_path}")
                zip_ref.extractall(f"{get_project_root()}")
        except Exception as e:
            print(f"Failed to unzip {file_name}: {e}")
            exit(1)
        finally:
            os.remove(temp_file_path)

    def get_bootstrap_directory():
        for root, dirs, files in os.walk(get_project_root()):
            for dir_name in dirs:
                if "bootstrap" in dir_name:
                    print(f"Found Bootstrap directory: {dir_name}")
                    return os.path.join(root, dir_name)

    def move_files(
        current_dir: str, sub_dir: str, target_dir: str, file_extensions: List[str]
    ):
        directory = os.path.join(current_dir + sub_dir)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(tuple(file_extensions)):
                    source_file = os.path.join(root, file)
                    target_file = os.path.join(target_dir, file)
                    try:
                        os.rename(source_file, target_file)
                        print(f"Moved {source_file} to {target_file}")
                    except Exception as e:
                        print(f"Failed to move {source_file} to {target_file}: {e}")

    def delete_dir(directory: str):
        try:
            for root, dirs, files in os.walk(directory, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(directory)
            print(f"Removed directory {directory}")
        except Exception as e:
            print(f"Failed to remove directory {directory}: {e}")

    download_bootstrap_zip()

    extract_and_remove()

    bootstrap_directory = get_bootstrap_directory()

    move_files(
        current_dir=bootstrap_directory,
        sub_dir="/css",
        target_dir=f"{get_project_root()}{target_css_dir}",
        file_extensions=[".min.css", ".min.css.map"],
    )

    move_files(
        current_dir=bootstrap_directory,
        sub_dir="/js",
        target_dir=f"{get_project_root()}{target_js_dir}",
        file_extensions=[".min.js", ".min.js.map"],
    )

    delete_dir(bootstrap_directory)


def main():
    _current_static_file_versions = BaseAppConfig()

    deployed_versions = get_base_app_config()

    if _current_static_file_versions.htmx_version != deployed_versions.htmx_version:
        htmx_url = f"https://unpkg.com/htmx.org@{deployed_versions.htmx_version}/dist/htmx.min.js"
        target_dir = f"/app/static/js"
        file_name = "htmx.min.js"

        update_file(url=htmx_url, target_dir=target_dir, file_name=file_name)
    else:
        print(f"htmx is already up to date at version {deployed_versions.htmx_version}")

    if _current_static_file_versions.jquery_version != deployed_versions.jquery_version:
        jquery_url = (
            f"https://code.jquery.com/jquery-{deployed_versions.jquery_version}.min.js"
        )
        target_dir = f"/app/static/js"
        file_name = "jquery.min.js"

        update_file(url=jquery_url, target_dir=target_dir, file_name=file_name)
    else:
        print(
            f"jQuery is already up to date at version {deployed_versions.jquery_version}"
        )

    if (
        _current_static_file_versions.bootstrap_version
        != deployed_versions.bootstrap_version
    ):
        update_bootstrap_dependency(bootstrap_version=deployed_versions.bootstrap_version)
    else:
        print(
            f"Bootstrap is already up to date at version {deployed_versions.bootstrap_version}"
        )


if __name__ == "__main__":
    main()
