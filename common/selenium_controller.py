"""
This file is the frontend driver for the Fenrir project.
It is used to interact with the frontend of a web application.
"""

import logging
from enum import Enum
import time
from typing import Tuple

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
    The SeleniumController class provides a wrapper around Selenium WebDriver
    with built-in retry logic, timeouts, and common web automation utilities.

    Args:
        driver (WebDriver | None): The WebDriver instance to use for interacting with the web application.
        log (logging.Logger, optional): The logger instance to use for logging. Defaults to logging.getLogger(__name__).
        retry (int, optional): The number of times to retry an operation if it fails. Defaults to 2.
        timeout (int, optional): The maximum time to wait for an element to be visible or present. Defaults to 2.
        wait_time (float, optional): The time to wait between operations. Defaults to 0.25 seconds.
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
        Navigate to the specified URL and wait for the page to load completely.

        Args:
            url (str): The URL to navigate to.

        Returns:
            str: The current URL after navigation.

        Raises:
            TimeoutException: If the URL doesn't load within the timeout period.
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
        Log the current page title and quit the WebDriver instance.

        Returns:
            None
        """
        self.log.info(self.driver.title)
        self.driver.quit()
        self.log.info("Driver quit!")

    def scroll_to_top(self) -> None:
        """
        Scrolls to the top of the page.

        Returns:
            None
        """
        scroll = "window.scroll(0, 0);"
        self.log.info(f"Scrolling to bottom of page with script: {scroll}")
        self.driver.execute_script(scroll)

    def scroll_to_bottom(self) -> None:
        """
        Scrolls to the bottom of the page.

        Returns:
            None
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
        Scrolls the specified element into view within the viewport.

        Args:
            element (WebElement): The element to scroll into view.
            block (ScrollOptionsEnum, optional): Vertical alignment option. Defaults to ScrollOptionsEnum.START.
            inline (ScrollOptionsEnum, optional): Horizontal alignment option. Defaults to ScrollOptionsEnum.START.

        Returns:
            None
        """
        self.driver.execute_script(
            f"arguments[0].scrollIntoView({{behavior: 'auto', block: '{block.value}', inline: '{inline.value}'}});",
            element,
        )

    def find_element(self, by: By, value: str) -> WebElement:
        """
        Find a single element with built-in retry logic and timeout handling.

        This method contains timeout and catches StaleElementReferenceException,
        TimeoutException, NoSuchElementException, and ElementClickInterceptedException
        with automatic retry logic.

        Args:
            by (By): The method to locate the element (e.g., By.ID, By.XPATH, By.CSS_SELECTOR).
            value (str): The selector value for locating the element.

        Returns:
            WebElement: The located web element.

        Raises:
            MaxElementRetriesException: If the element cannot be found after maximum retry attempts.

        Note:
            When looking for potentially non-present elements, use the built-in Selenium method instead.
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
        Find multiple elements with built-in retry logic and timeout handling.

        Args:
            by (By): The method to locate the elements (e.g., By.ID, By.XPATH, By.CSS_SELECTOR).
            value (str): The selector value for locating the elements.

        Returns:
            list[WebElement]: A list of located web elements.

        Raises:
            MaxElementRetriesException: If the elements cannot be found after maximum retry attempts.

        Note:
            When looking for potentially non-present elements, use the built-in Selenium method instead.
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
            corner (str, optional): The corner to click on. Options are "top-left", "top-right",
                          "bottom-left", "bottom-right", or "center". Defaults to "center".

        Returns:
            None

        Raises:
            ValueError: If an invalid corner option is provided.
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

    def click_element_at_viewport_location(self, element: WebElement) -> None:
        """
        Clicks at the location of the given WebElement in the viewport using ActionChains.

        Args:
            element (WebElement): The WebElement to click at its viewport location.

        Returns:
            None
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
        Attempts to clear the text from an input element using multiple methods.

        Args:
            element (WebElement): The input element to clear text from.

        Returns:
            str | bool: Returns True if successfully cleared, or the remaining text content.
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
        Inputs text into an element and returns the element's current value.

        Args:
            element (WebElement): The input element to send text to.
            text (str): The text to input into the element.

        Returns:
            str: The current value of the element after inputting text.
        """
        element.send_keys(text)
        return element.get_dom_attribute("value")

    def get_table_row_by_index(self, index: int) -> WebElement:
        """
        Get a table row element by its index position.

        Args:
            index (int): The 1-based index of the table row to retrieve.

        Returns:
            WebElement: The table row element at the specified index.

        Raises:
            ValueError: If index is negative or exceeds the number of table rows.
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
        Get a table header element by its index position.

        Args:
            index (int): The 1-based index of the table header to retrieve.

        Returns:
            WebElement: The table header element at the specified index.

        Raises:
            ValueError: If index is negative or exceeds the number of table headers.
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
        Get the number of columns in the table.

        Returns:
            int: The total number of table header columns.
        """
        return len(self.find_elements(By.XPATH, "//thead//th"))

    def get_table_column_index_by_header_text(self, column_text: str) -> int:
        """
        Get the column index by matching the header text content.

        Args:
            column_text (str): The text content of the column header to find.

        Returns:
            int: The 1-based index of the column with matching header text.

        Raises:
            ValueError: If no column with the specified text is found.
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
        Get a table data element from a specific row and column.

        Args:
            table_row_index (int): The 1-based index of the table row.
            column_index (int, optional): The 1-based index of the table column. Defaults to 1.

        Returns:
            WebElement: The table data element at the specified row and column intersection.
        """
        return self.find_element(
            By.XPATH, f"//tbody//tr[{table_row_index}]//td[{column_index}]"
        )

    def sort_table_column_by_aria_sort(
        self, element: WebElement, sort_string: str
    ) -> bool:
        """
        Sorts a table column by clicking on the header until the desired sort order is achieved.

        Args:
            element (WebElement): The table header element to click for sorting.
            sort_string (str): The desired aria-sort value (e.g., "ascending", "descending").

        Returns:
            bool: True if the sort order was successfully achieved.

        Raises:
            TimeoutException: If the desired sort order cannot be achieved within retry limits.
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
        self, locator: Tuple[str, str], timeout: float = 10
    ) -> bool:
        """
        Waits for an element to disappear from the DOM within the specified timeout.

        Args:
            locator (Tuple[str, str]): A tuple containing the locator strategy and value
                (e.g., (By.ID, "element-id")).
            timeout (float, optional): Maximum time to wait in seconds. Defaults to 10.

        Returns:
            bool: True if the element disappeared within the timeout, False otherwise.
        """
        by, value = locator
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
