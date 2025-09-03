"""
This file is the frontend driver for the Fenrir project.
It is used to interact with the frontend of a web application.
"""

import logging
from enum import Enum
import time


from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains


class MaxElementRetriesException(Exception):
    """
    Raised when the maximum number of retries is reached.
    """

    ...


# Important: If adding more actions in the FrontendDriver class,
#  add them to the FrontendAction enum class
class FrontendActionsEnum(Enum):
    SCROLL_TO_TOP = "scroll_to_top"
    SCROLL_TO_BOTTOM = "scroll_to_bottom"
    FIND_ELEMENT = "find_element"
    FIND_ELEMENTS = "find_elements"
    SCROLL_INTO_VIEW = "scroll_into_view"
    CLICK = "click"
    INPUT_TEXT = "input_text"


class ScrollOptionsEnum(Enum):
    """
    NOTES:
        The block option determines the vertical alignment of the element inside its
        visible area within the scrollable ancestor.

        The inline option determines the horizontal alignment of the element inside its
        visible area within the scrollable ancestor.
    """

    START = "start"
    CENTER = "center"
    END = "end"
    NEAREST = "nearest"


class SeleniumController:
    """
    The DriverService class represents a driver for
    interacting with the frontend of a web application.

    Args:
    :param:
        driver (WebDriver | None): The WebDriver instance to use for interacting with the web application.
    :param:
        retry (int, optional): The number of times to retry an operation if it fails. Defaults to 3.
    :param:
        timeout (int, optional): The maximum time to wait for an element to be visible or present. Defaults to 10.
    :param:
        log (logging.Logger, optional): The logger instance to use for logging. Defaults to logging.getLogger(__name__).
    :param:
        driver (WebDriver | None): The WebDriver instance to use for interacting with the web application.
    :param:
        retry (int, optional): The number of times to retry an operation if it fails. Defaults to 3.
    :param:
        timeout (int, optional): The maximum time to wait for an element to be visible or present. Defaults to 10.
    :param:
        log (logging.Logger, optional): The logger instance to use for logging. Defaults to logging.getLogger(__name__).
    """

    def __init__(
        self,
        driver: WebDriver | None,
        log: logging.Logger = logging.getLogger(__name__),
        retry: int = 2,
        timeout: int = 2,
        wait_time=0.25,
    ):
        self.driver = driver
        self.retry = retry
        self.timeout = timeout
        self.log = log
        if self.driver is not None:
            self.driver.implicitly_wait(2)
        self.wait_time = wait_time

    def get(self, url: str) -> str:
        """
        Overridden get method to log the URL before getting it.
        """
        self.driver.get(url)
        loading_done: bool = (
            lambda complete: self.driver.execute_script("return document.readyState")
            == complete
        )
        try:
            WebDriverWait(self.driver, timeout=self.timeout).until(
                expected_conditions.url_contains(url)
            )
            while not loading_done("complete"):
                time.sleep(self.wait_time)
        except TimeoutException:
            self.log.warning(f"TimeoutException caught while waiting for URL: {url}")
        return self.driver.current_url

    def quit(self) -> None:
        """
        Overridden quit method to log the title before quitting the driver.
        """
        self.log.info(self.driver.title)
        self.driver.quit()
        self.log.info("Driver quit!")

    def scroll_to_top(self) -> None:
        """
        Scrolls to the top of the page.
        """
        scroll = "window.scroll(0, 0);"
        self.log.info(f"Scrolling to bottom of page with script: {scroll}")
        self.driver.execute_script(scroll)

    def scroll_to_bottom(self) -> None:
        """
        Scrolls to the bottom of the page.
        """
        scroll = "window.scrollTo(0,document.body.scrollHeight)"
        self.log.info(f"Scrolling to bottom of page with script: {scroll}")
        self.driver.execute_script(scroll)

    def scroll_into_view(
        self,
        element: WebElement,
        block: ScrollOptionsEnum = ScrollOptionsEnum.START,
        inline: ScrollOptionsEnum = ScrollOptionsEnum.START,
    ) -> None:
        """
        Scrolls the element into view.
        """
        self.driver.execute_script(
            f"arguments[0].scrollIntoView({{behavior: 'auto', block: '{block.value}', inline: '{inline.value}'}});",
            element,
        )

    def find_element(self, by: By, value: str) -> WebElement:
        """
        Contains timeout and catch StaleElementReference Exceptions
        because that exception is more of an interference than a helpful error.

        :Param: by: By - from selenium.webdriver.common.by import By
        :Param: selector: str - Should be the selector for your element.

        When looking for non-present element, use the built-in Selenium method.
        """
        time.sleep(0.020)
        _attempt = 0
        while _attempt < self.retry:
            try:
                self.log.info(f"Fenrir Find Element: \n {by} - {value} - {_attempt}")
                if WebDriverWait(self.driver, timeout=self.timeout).until(
                    expected_conditions.visibility_of_element_located((str(by), value))
                ):
                    element = self.driver.find_element(by, value)
                    break
            except TimeoutException:
                _attempt += 1
                if _attempt < self.retry:
                    self.log.warning(f"TimeoutException caught, retrying...{_attempt}")
            except StaleElementReferenceException:
                _attempt += 1
                if _attempt < self.retry:
                    self.log.warning(
                        f"StaleElementReferenceException caught, retrying...{_attempt}"
                    )
            except NoSuchElementException:
                _attempt += 1
                if _attempt < self.retry:
                    self.log.warning(
                        f"NoSuchElementException caught, retrying...{_attempt}"
                    )
            except ElementClickInterceptedException:
                _attempt += 1
                if _attempt < self.retry:
                    self.log.warning(
                        f"ClickElementInterceptException caught, retrying...{_attempt}"
                    )
        else:
            raise MaxElementRetriesException(
                f"Max Retries reached for finding element by: {by} with Selector: {value}"
            )
        return element

    def find_elements(self, by: By, value: str) -> list[WebElement]:
        """
        :param: by: By - from selenium.webdriver.common.by import By
        :param: selector: str - Should be the selector for your element.
        When looking for non-present elements, use the built-in SE method.
        """
        time.sleep(0.020)
        _attempt = 0
        while _attempt < self.retry:
            try:
                self.log.info(f"\n Finding Element by: {by} with Selector: {value}")
                if WebDriverWait(driver=self.driver, timeout=self.timeout).until(
                    expected_conditions.presence_of_all_elements_located((str(by), value))
                ):
                    elements = self.driver.find_elements(by=by, value=value)
                    break
            except TimeoutException:
                _attempt += 1
                if _attempt < self.retry:
                    self.log.warning(f"TimeoutException caught, retrying...{_attempt}")
            except StaleElementReferenceException:
                _attempt += 1
                if _attempt < self.retry:
                    self.log.warning(
                        f"StaleElementReferenceException caught, retrying...{_attempt}"
                    )
            except NoSuchElementException:
                _attempt += 1
                if _attempt < self.retry:
                    self.log.warning(
                        f"NoSuchElementException caught, retrying...{_attempt}"
                    )
        else:
            raise MaxElementRetriesException(
                f"Max Retries reached for finding element by: {by} with Selector: {value}"
            )
        return elements

    def click(self, element: WebElement, corner: str = "center") -> None:
        """
        Clicks the element at a specific corner using JavaScript.

        Args:
            element (WebElement): The element to click.
            corner (str): The corner to click on. Options are "top-left", "top-right",
                          "bottom-left", "bottom-right", or "center". Defaults to "center".
        """
        corners = {
            "top-left": {"x": 1, "y": 1},
            "top-right": {"x": element.size["width"] - 1, "y": 1},
            "bottom-left": {"x": 1, "y": element.size["height"] - 1},
            "bottom-right": {
                "x": element.size["width"] - 1,
                "y": element.size["height"] - 1,
            },
            "center": {"x": element.size["width"] // 2, "y": element.size["height"] // 2},
        }

        if corner not in corners:
            raise ValueError(
                f"Invalid corner '{corner}'. Valid options are: {list(corners.keys())}"
            )

        offset = corners[corner]
        WebDriverWait(self.driver, self.timeout).until(
            expected_conditions.element_to_be_clickable(element)
        )
        self.driver.execute_script(
            "const rect = arguments[0].getBoundingClientRect();"
            "const x = rect.left + arguments[1];"
            "const y = rect.top + arguments[2];"
            "const el = document.elementFromPoint(x, y);"
            "if (el) { el.click(); }",
            element,
            offset["x"],
            offset["y"],
        )

    def click_element_at_viewport_location(self, element: WebElement):
        """
        Clicks at the location of the given WebElement in the viewport.

        :param element: The WebElement to click.
        """
        location = element.location_once_scrolled_into_view
        size = element.size
        x = location["x"] + size["width"] // 2
        y = location["y"] + size["height"] // 2
        self.driver.driver.execute_script(
            "window.scrollTo(arguments[0], arguments[1]);", x, y
        )
        actions = ActionChains(self.driver)
        actions.move_by_offset(x, y).click().perform()

    def clear_text(self, element: WebElement) -> str | bool:
        """
        Attempts to clear the text from an element.
        """
        text = ""
        try:
            element_value = element.get_dom_attribute("value") or element.text
            self.log.info(f"Clearing element value: {element_value}")
            for _ in range(len(element_value)):
                time.sleep(0.020)
                element.send_keys(Keys.BACKSPACE)
            if not element.get_dom_attribute("value"):
                return True
            if element.get_dom_attribute("value"):
                element.clear()
            if element.get_dom_attribute("title"):
                element.__setattr__("title", "")
            if element.text == "" or element.text is None:
                text = element.text
        except Exception:
            time.sleep(self.wait_time)
        time.sleep(self.wait_time)
        return text

    def input_text(self, element: WebElement, text: str) -> str:
        """
        Inputs text into an element and returns the value of the element.
        """
        element.send_keys(text)
        return element.get_dom_attribute("value")

    def get_table_row_by_index(self, index: int) -> WebElement:
        """
        Get the table row by index.
        """
        amount_of_table_rows = len(self.find_elements(By.XPATH, "//tbody//tr"))
        if index < 0:
            raise ValueError("Row index must be greater than or equal to 0")
        if index > amount_of_table_rows:
            raise ValueError(
                "Row index must be less than the number of rows in the table"
            )
        return self.find_element(By.XPATH, f"//tbody//tr[{index}]")

    def get_table_header_by_index(self, index: int) -> WebElement:
        """
        Get the table header by index.
        """
        amount_of_table_headers = len(self.find_elements(By.XPATH, "//thead//th"))
        if index < 0:
            raise ValueError("Header index must be greater than or equal to 0")
        if index > amount_of_table_headers:
            raise ValueError(
                "Header index must be less than the number of headers in the table"
            )
        return self.find_element(By.XPATH, f"//thead//th[{index}]")

    def get_table_column_length(self) -> int:
        """
        Get the length of the table column.
        """
        return len(self.find_elements(By.XPATH, "//thead//th"))

    def get_table_column_index_by_header_text(self, column_text: str) -> int:
        """
        Get the data from a table based on the column header text.
        """
        amount_of_table_headers = self.get_table_column_length()
        header_index = 1
        while header_index <= amount_of_table_headers:
            header = self.find_element(By.XPATH, f"//thead//th[{header_index}]")
            if header.text == column_text:
                return header_index
            header_index += 1
        else:
            raise ValueError(f"Column with text '{column_text}' not found")

    def get_table_data_by_column_index(
        self, table_row_index: int, column_index: int = 1
    ) -> WebElement:
        """
        Get the table data element from a table row.
        """
        return self.find_element(
            By.XPATH, f"//tbody//tr[{table_row_index}]//td[{column_index}]"
        )

    def sort_table_column_by_aria_sort(
        self, element: WebElement, sort_string: str
    ) -> bool:
        """
        Sorts a table column by clicking on the header.
        """
        current_sort = element.get_dom_attribute("aria-sort")
        retry = 0
        while current_sort != sort_string or (retry <= self.retry):
            element.click()
            time.sleep(self.wait_time)
            current_sort = element.get_dom_attribute("aria-sort")
            if current_sort == sort_string:
                break
            retry += 1
        else:
            raise TimeoutException(
                f"TimeoutException: Could not sort table column by {sort_string}"
            )
        return current_sort == sort_string

    def wait_for_element_to_disappear(
        self, by: By, value: str, timeout: int = 20
    ) -> bool:
        """
        Waits for an element to disappear from the DOM or times out after the specified time.

        Args:
            by (By): The method to locate the element (e.g., By.ID, By.XPATH).
            selector (str): The selector string to locate the element.
            timeout (int): The maximum time to wait for the element to disappear. Defaults to 60 seconds.

        Returns:
            bool: True if the element disappears, False otherwise.
        """
        try:
            WebDriverWait(self.driver, timeout).until_not(
                expected_conditions.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            self.log.warning(
                f"Element with selector '{value}' did not disappear within {timeout} seconds."
            )
            return False


# Check if all the methods in the FrontendDriver class are in the FrontendActionsEnum
if __name__ == "__main__":
    drive = SeleniumController(driver=None, log=logging.getLogger(__name__))

    print(FrontendActionsEnum.__members__)
