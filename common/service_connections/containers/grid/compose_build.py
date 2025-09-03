#!/usr/bin/env python3.12
import os
from typing import Dict, List
import yaml
import random
import string


TIMEOUT = f"session-timeout={os.getenv('SESSION_TIMEOUT', 45)}"
HUB_CONNECTION_STRING = f"hub={os.getenv('HUB', 'http://localhost')}"

def remove_specified(services: List[str], data: Dict) -> Dict:
    """
    Remove specified services from the docker-compose data.
    :param services: List of service names to remove.
    :param data: Dictionary containing the docker-compose services.
    :return: Dictionary with the remaining services.
    """
    if not services:
        raise ValueError("No services specified for removal.")
    for service in services:
        if service in data:
            del data[service]
    # Filter out the specified services
    return data


def duplicate_specified(service_name: str, data: Dict, replicas: int) -> Dict:
    """
    Duplicate a service in the docker-compose data.
    :param service_name: Name of the service to duplicate.
    :param data: Dictionary containing the docker-compose services.
    :return: Dictionary with the duplicated service.
    """
    if service_name not in data:
        raise ValueError(f"Service '{service_name}' not found in the provided data.")
    if replicas <= 0:
        raise ValueError("Number of replicas must be greater than 0.")
    if replicas > 8:
        raise ValueError("Number of replicas cannot exceed 8.")

    for _ in range(replicas):
        new_service = data[service_name].copy()
        copy_service = str(_ + 1)
        data[f"{service_name}-{copy_service}"] = new_service

    return data


if __name__ == "__main__":
    if not os.path.exists("docker-compose-v3.yml"):
        raise FileNotFoundError(
            "docker-compose-v3.yml file not found in the current directory."
        )

    # Load the base docker-compose file
    with open("docker-compose-v3.yml", "r") as f:
        data = yaml.safe_load(f)

    data = remove_specified(services=["edge", "firefox"], data=data["services"])

    data = duplicate_specified("chrome", data, replicas=2)

    data["selenium-hub"].update({"environment": [TIMEOUT, HUB_CONNECTION_STRING]})

    with open(f"{os.getcwd()}/docker-compose-v3-composite.yml", "w") as f:
        yaml.dump({"services": data}, f, default_flow_style=False, sort_keys=False)
