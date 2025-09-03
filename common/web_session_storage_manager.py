
import json
import time

from selenium.webdriver.remote.webdriver import WebDriver

class WebSessionStorageManager:
    """
    A class for interacting with the session storage of a web application.
    """

    def __init__(self, driver: WebDriver):
        self.driver = driver

    def __len__(self):
        return self.driver.execute_script("return window.sessionStorage.length;")

    def get_storage(self):
        """
        Gets the session storage.
        """
        return self.driver.execute_script("return window.sessionStorage;")

    def items(self):
        """
        Gets the items in the session storage.
        """
        return self.driver.execute_script(
            """
                function deepCopy(obj) {
                if (typeof obj !== 'object' || obj === null) {
                    return obj; // Base case: return primitive values directly
                }
                const result = Array.isArray(obj) ? [] : {}; // Create a new object or array
                for (const key in obj) {
                    if (Object.prototype.hasOwnProperty.call(obj, key)) {
                    result[key] = deepCopy(obj[key]); // Recursively copy nested properties
                    }
                }
                return result;
                }
                return deepCopy(window.sessionStorage);"""
        )

    def keys(self):
        """
        Returns a list of keys stored in the session storage of the web driver.

        :return: A list of keys.
        """
        keys = self.driver.execute_script(
            "var ls = window.sessionStorage, keys = []; "
            "for (var i = 0; i < ls.length; ++i) "
            "  keys[i] = ls.key(i); "
            "return keys; "
        )
        return keys

    def get(self, key):
        """
        Retrieves the value associated with the given key from the window session storage.
        Parameters:
        - key (str): The key of the value to retrieve.
        Returns:
        - str: The value associated with the given key.
        """
        return self.driver.execute_script(
            "return window.sessionStorage.getItem(arguments[0]);", key
        )

    def set(self, key, value):
        """
        Sets a value in the session storage of the web browser.
        Parameters:
            key (str): The key of the item to be set.
            value (str): The value to be set.
        Returns:
            None
        """
        self.driver.execute_script(
            "window.sessionStorage.setItem(arguments[0], arguments[1]);", key, value
        )

    def has(self, key):
        """
        Check if the given key exists in the keys of the frontend driver.
        Parameters:
        - key: The key to check for existence.
        Returns:
        - True if the key exists in the keys of the frontend driver, False otherwise.
        """

        return key in self.keys()

    def remove(self, key):
        """
        Remove an item from the session storage.
        Parameters:
        - key (str): The key of the item to be removed.
        Returns:
        None
        """

        self.driver.execute_script("window.sessionStorage.removeItem(arguments[0]);", key)

    def clear(self):
        """
        Clears the session storage of the current browser window.

        This method executes a JavaScript command to clear the session storage of the current browser window.

        Parameters:
            None

        Returns:
            None
        """
        self.driver.execute_script("window.sessionStorage.clear();")

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        self.set(key, value)

    def __contains__(self, key):
        return key in self.keys()

    def __iter__(self):
        return self.items().__iter__()

    def __repr__(self):
        return self.items().__str__()


def get_access_token_from_session_storage(storage: WebSessionStorageManager) -> str:
    """
    Retrieve the access token from the session storage.
    This function attempts to retrieve an access token from the provided
    session storage. It retries up to 5 times, waiting 1 second between
    each attempt, before raising a KeyError if no access token is found.
    Args:
        storage (SessionStorage): The session storage object containing
                                  the items to search for the access token.
    Returns:
        str: The access token retrieved from the session storage.
    Raises:
        KeyError: If no access token is found in the session storage after
                  5 attempts.
    """

    retry = 0

    def get_access_token():
        """
        Get Access Token from the session storage.
        """
        for item in storage.items():
            if item.__contains__("accessToken"):
                return storage.get(item)
            if item.__contains__("accesstoken"):
                return json.loads(storage.get(item))["secret"]

    while retry < 5:
        token = get_access_token()
        if token:
            break
        time.sleep(1)
        retry += 1
    else:
        raise KeyError("No access token found in session storage")
    return token


def get_refresh_token_from_session_storage(storage: WebSessionStorageManager) -> str:
    """
    Retrieves the refresh token from the session storage.
    This function attempts to retrieve a refresh token from the provided session storage.
    It will retry up to 5 times if the token is not immediately found, waiting 1 second
    between each retry.
    Args:
        storage (SessionStorage): The session storage object to search for the refresh token.
    Returns:
        str: The refresh token found in the session storage.
    Raises:
        KeyError: If no refresh token is found in the session storage after 5 retries.
    """

    retry = 0

    def get_refresh_token() -> str:
        """
        Retrieves the refresh token from the session storage.
        """
        for item in storage.items():
            if item.__contains__("refresh"):
                return storage.get(item)
            if item.__contains__("refresh"):
                return json.loads(storage.get(item))["secret"]
        else:
            raise KeyError("No refresh token found in session storage")

    while retry < 5:
        refresh_token = get_refresh_token()
        if refresh_token:
            break
        time.sleep(1)
        retry += 1
    else:
        raise KeyError("No access token found in session storage")
    return refresh_token


def get_access_token_from_cookies(driver: WebDriver) -> str:
    """
    Retrieves the access token from the cookies of the given WebDriver instance.

    Args:
        driver (WebDriver): The WebDriver instance to retrieve the access token from.

    Returns:
        str: The access token value.

    Raises:
        KeyError: If no access token is found in the cookies.
    """
    retry = 0
    token = None

    def get_access_token() -> str:
        cookies = driver.get_cookies()
        for cookie in cookies:
            if cookie["name"].__contains__("accessToken"):
                return cookie["value"]

    while retry < 5:
        token = get_access_token()
        if token:
            break
        time.sleep(2)
        retry += 1
    else:
        raise KeyError("No access token found in cookies")

    return token