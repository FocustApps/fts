
echo "\n Downloading latest Docker Compose file"

cd "$(pwd)/services/containers/grid" || { echo "Failed to change directory"; exit 1; }

curl -o docker-compose-v3.yml https://raw.githubusercontent.com/SeleniumHQ/docker-selenium/trunk/docker-compose-v3.yml


python $(find $(pwd) -name compose_build.py) || exit 1


# Detect OS
OS_TYPE="$(uname -s)"

if [[ "$OS_TYPE" == "Darwin" ]]; then
    # macOS: use 'docker compose'
    echo "\n Starting Selenium Grid with Docker Compose (macOS)"
    docker compose rm -f docker-compose-v3-composite.yml down
    docker compose -f docker-compose-v3-composite.yml up
elif [[ "$OS_TYPE" == "Linux" ]]; then
    # Linux: use 'docker-compose'
    echo "\n Starting Selenium Grid with Docker Compose (Linux)"
    docker-compose rm -f docker-compose-v3-composite.yml down
    docker-compose -f docker-compose-v3-composite.yml up
elif [[ "$OS_TYPE" == *"MINGW"* || "$OS_TYPE" == *"MSYS"* || "$OS_TYPE" == *"CYGWIN"* ]]; then
    # Windows (Git Bash, etc.): use 'docker-compose'
    echo "\n Starting Selenium Grid with Docker Compose (Windows)"
    docker-compose rm -f docker-compose-v3-composite.yml down
    docker-compose -f docker-compose-v3-composite.yml up
else
    echo "Unsupported OS: $OS_TYPE"
    exit 1
fi