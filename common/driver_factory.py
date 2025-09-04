import logging
import os
from datetime import datetime

from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxDriver
from selenium.webdriver.edge.webdriver import WebDriver as EdgeDriver
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver

from common.selenium_controller import SeleniumController
from common.fenrir_enums import BrowserEnum, DriverLocationEnum


class InvalidWebdriverException(Exception):
    pass


def add_browser_options(browser: str) -> ChromeOptions | FirefoxOptions | EdgeOptions:
    """
    Adds browser-specific options.
    """
    match browser:
        case BrowserEnum.CHROME.value:
            options = ChromeOptions()
        case BrowserEnum.FIREFOX.value:
            options = FirefoxOptions()
        case BrowserEnum.EDGE.value:
            options = EdgeOptions()
        case _:
            raise InvalidWebdriverException("Invalid Browser")
    return options


def driver_factory(
    browser: str, driver_location: DriverLocationEnum, headless=False
) -> SeleniumController:
    """
    browser: str - chrome
    driver_location: str - local-no-container
    """
    driver = None
    options = add_browser_options(browser)

    # NOTE:
    # Structural pattern matching with Enum members failed when duplicate Enum
    # classes were loaded under different module names (e.g., 'common.fenrir_enums'
    # and 'fts.common.fenrir_enums'), producing different identity objects. To
    # avoid brittle identity matching, we compare on the underlying .value
    # strings instead. This keeps behavior stable regardless of import path.

    loc_val = getattr(driver_location, "value", driver_location)
    browser_val = browser

    if (
        loc_val == DriverLocationEnum.LOCAL.value
        and browser_val == BrowserEnum.CHROME.value
    ):
        if headless:
            options.add_argument("--headless")
        driver = SeleniumController(
            driver=ChromeWebDriver(options=options), log=logging.getLogger(__name__)
        )
    if (
        loc_val == DriverLocationEnum.LOCAL.value
        and browser_val == BrowserEnum.FIREFOX.value
    ):
        driver = SeleniumController(
            driver=FirefoxDriver(options=options), log=logging.getLogger(__name__)
        )
    if (
        loc_val == DriverLocationEnum.LOCAL.value
        and browser_val == BrowserEnum.EDGE.value
    ):
        driver = SeleniumController(
            driver=EdgeDriver(options=options), log=logging.getLogger(__name__)
        )
    if loc_val == DriverLocationEnum.LOCAL_CONTAINER.value:
        driver = SeleniumController(
            driver=RemoteWebDriver(
                command_executor="http://localhost:4444", options=options
            ),
            log=logging.getLogger(__name__),
        )
    if loc_val == DriverLocationEnum.CLOUD.value:
        options.browser_version = "latest"
        options.platform_name = "Windows 11"
        sauce_options = {}
        sauce_options["build"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        sauce_options["name"] = os.getenv("TEST_TARGETS") or "Fenrir"
        options.set_capability("sauce:options", sauce_options)
        driver = SeleniumController(
            driver=RemoteWebDriver(
                command_executor=os.getenv("REMOTE_DRIVER_URL"), options=options
            ),
            log=logging.getLogger(__name__),
        )
    if not driver:
        raise InvalidWebdriverException(
            f"Invalid Webdriver: {browser}, {driver_location}"
        )
    return driver
