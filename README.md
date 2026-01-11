# Fenrir Testing System (FTS)

FTS serves as a central hub for integrating various tools to facilitate automated testing. By abstracting system connections, we can maintain organization and provide a comprehensive overview of what automated tests are required. Fenrir is designed to complement existing tools rather than replace them (for now), allowing users to seamlessly integrate and utilize different tools to create an efficient testing workflow.

There will be a README.md file in each directory of this project that will give a more detailed description that module provides.

*Much of the system is coupled to a single tool we will need to go through and add abstraction layer to the more customizable.*

:::mermaid
mindmap
    root(Fenrir))
        (Database)
        (Test Cases)
        (CI/CD)
        Test Runner(Containers)
        (Chat)
        (Reporting)
:::

List of abstractions needed:

1. Cloud-connections: Azure / Azure-Devops is currently the old cloud connection I have for test case tracking.
2. Database connection: Currently only using MSSQL in azure. TODO: Create a deployable database template.
3. Selenium: The current protocol is to run commands in code, this will need to be refactored to be more of a json

## Local Development Setup

- Install [Python 3.12](https://www.python.org/downloads/)+

- Enure that the installation is part of your PATH

- Install [UV](https://docs.astral.sh/uv/) to your global python installation, use it to create a venv then install all your package dependencies to that env.

---

### Environment

There are recommended VS code extensions in this repo please install them.
Located here ```/fenrir/.vscode/extensions.json```

A ```.env``` file is required to run tests as you will need to the Fenrir
database and the ability to connect is driven by environment variables. The ```example.env``` file should be copied.

```sh
# REQUIRED EN-VARS:
FENRIR_SERVER_NAME=some-db-server
FENRIR_DB_NAME=fenrir-qa-automation
DB_USERNAME=fenrir-user
DB_USER_PASSWORD=*********

TARGET_ENVIRONMENT=qa
BROWSER=chrome

# OPTIONAL ENV-VAR if you want to run tests remotely
REMOTE_DRIVER_URL=<connection-string>
```

### Database Connection Requirements

#### Postgres

By default this system will use postgres as the default database. It will require infrastructure to setup a database server for deployment but if you want to run this program locally there will be a container/volume that will spin up and connect for application testing. This will not solve the issue of running tests that need to connect to a database server for configuration data.

#### Microsoft SQL (Other DB Option)

This project can use PYODBC to connect to the database so you must have the
requisite database driver installed. [guide](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/install-microsoft-odbc-driver-sql-server-macos?view=sql-server-ver15)

If an import error happens check out this [article](https://stackoverflow.com/questions/59725631/change-where-pyodbc-expects-libodbc-2-dylib-to-live-changing-default-odbc-file)

---

### Running Tests

The ```/fenrir/tests/``` directory is where all tests are housed for all applications this does not exist in the base repository as tests are implemented as needed per software application.

Using pytest in the terminal or the Sidebar of VS code:

![VS Code sidebar](./docs/images/vscode_side_bar.png)

---

## Frontend Development (not needed for running tests)

### Azure CLI

Ensure that you have the Azure CLI installed.
[Install the CLI for your OS](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd?tabs=winget-windows%2Cscript-mac%2Cscript-linux&pivots=os-mac)

Mac Install:

``` shell
curl -fsSL https://aka.ms/install-azd.sh | bash 
```

### Windows Containerization

1. Enable UEFI in your BIOS settings.
2. Enable WSL2 Windows Subsystems for Linux in Windows settings.

> 1. Using Windows Subsystem for Linux (WSL):
> 2. Install WSL (Windows Subsystem for Linux):
> 3. Go to Settings > Update & Security > For Developers.
> 4. Check the Developer Mode radio button.
> 5. Search for “Windows Features” and choose “Turn Windows features on or off.”
> 6. Scroll down to find Windows Subsystem for Linux, check the box, and install it.
> 7. Reboot your system to complete the installation.

### Mac Containerization

1. Install Docker Desktop
2. In Setting ensure that Virtual Machine Options is set to Apple Virtualization framework
AND Use Rosetta for x86_64/amd64 emulation on Apple Silicon is Enabled.

### Container Startup

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) on your machine.
Follow the instructions for your operating systems.

Running selenium containers for this framework is recommended but, you can run tests without them with the cavitate being that your machine is unusable during execution time.

The following directories contain files that will work as the local runners:

#### Parallel testing

```cd /docker/grid_compose```

```sh grid-helpers.sh```

TODO: Create configurable way to run a grid with multiple nodes.

TODO: Write instructions here for grid

---

#### Single threaded testing

To run the standalone container execute the shell file and follow the instructions.

```shell
sh $(find $(pwd) -name stand-alone-helper.sh)
```

### Definitions

1. **Selenium:** The primary frontend testing framework we are using. Tests that are frontend will have API portions to them to allow the state of pages to change on refresh which will allow for testing of data state changes during integration/e2e testing.

2. **Test Execution:** Refers to any sort of runtime testing.

3. **Run Config** contains all the metadata required to run a test such as the environment, execution target, test files to run, and report target to write to after execution.

> KEYWORDS: SELENIUM, FRONTEND, SE, TESTS

### Fenrir API

The fenrir API can be ran by executing ```sh entrypoint.sh``` for local execution or ```sh run-fenrir-app.sh``` to run as a docker-compose stack. This will run on localhost:8080 the idea is to have a configurable way to run tests rather than having to utilize the commandline for specific test runs and variables.

IF LOCAL: The ODBC database is protected in Azure so you will probably not have access unless connected to the Azure VPN and/or your IP address is added to the list of permitted connections.

IF DOCKER-COMPOSE: Postgres

The fenrir database blocks IP addresses so if you see a connection error then you will need to add your IP to access it in Azure.

For app-layer contribution guidelines and AI agent rules, see `.github/app-instructions.md`.

### useful commands

```bash
#Restart only the fenrir app container after code changes

docker compose cp app/. fenrir:/fenrir/app/ && docker compose restart fenrir

```
