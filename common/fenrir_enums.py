from enum import Enum


class EnvironmentEnum(Enum):
    LOCAL = "local"
    DEV = "dev"
    QA = "qa"
    AUTO = "auto"
    UAT = "uat"
    PROD = "prod"

    @staticmethod
    def get_valid_environments():
        return [env.value for env in EnvironmentEnum]

    @staticmethod
    def is_valid_environment(env: str):
        return env in EnvironmentEnum.get_valid_environments()


class BrowserEnum(Enum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"

    @staticmethod
    def get_valid_browsers():
        return [browser.value for browser in BrowserEnum]

    @staticmethod
    def is_valid_browser(browser: str):
        return browser in BrowserEnum.get_valid_browsers()


class DriverLocationEnum(Enum):
    LOCAL = "local"
    LOCAL_CONTAINER = "local-container"
    CLOUD = "cloud"

    def get_valid_remote_drivers(self):
        return [driver.value for driver in DriverLocationEnum]


class CloudProviderEnum(Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    IBM = "ibm"
    ORACLE = "oracle"
    VMWARE = "vmware"
    OTHER = "other"

    @staticmethod
    def get_valid_providers():
        return [provider.value for provider in CloudProviderEnum]

    @staticmethod
    def is_valid_provider(provider: str):
        return provider in CloudProviderEnum.get_valid_providers()
