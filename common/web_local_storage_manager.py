from selenium.webdriver.remote.webdriver import WebDriver

class WebLocalStorageManager:
    """
    A class for interacting with the local storage of a web application.
    """

    def __init__(self, driver: WebDriver):
        self.driver = driver

    def __len__(self):
        return self.driver.execute_script("return window.localStorage.length;")

    def items(self):
        """
        Returns a dictionary containing all items stored in the local storage of the web browser.

        :return: A dictionary with key-value pairs representing the items in the local storage.
        :retype: dict
        """
        return self.driver.execute_script(
            "var ls = window.localStorage, items = {}; "
            "for (var i = 0, k; i < ls.length; ++i) "
            "  items[k = ls.key(i)] = ls.getItem(k); "
            "return items; "
        )

    def keys(self) -> list[str]:
        """
        Returns a list of keys stored in the local storage of the web browser.

        :return: A list of keys stored in the local storage.
        :retype: list
        """
        return self.driver.execute_script(
            "var ls = window.localStorage, keys = []; "
            "for (var i = 0; i < ls.length; ++i) "
            "  keys[i] = ls.key(i); "
            "return keys; "
        )

    def get(self, key):
        """
        Retrieves the value associated with the given key from the local storage.

        Args:
            key (str): The key of the value to retrieve.

        Returns:
            Any: The value associated with the given key in the local storage.
        """
        return self.driver.execute_script(
            "return window.localStorage.getItem(arguments[0]);", key
        )

    def set(self, key, value):
        """
        Sets a value in the local storage of the web browser.

        Parameters:
        - key (str): The key of the value to be set.
        - value (str): The value to be set.

        Returns:
        None
        """
        self.driver.execute_script(
            "window.localStorage.setItem(arguments[0], arguments[1]);", key, value
        )

    def has(self, key):
        return key in self.keys()

    def remove(self, key):
        self.driver.execute_script("window.localStorage.removeItem(arguments[0]);", key)

    def clear(self):
        self.driver.execute_script("window.localStorage.clear();")

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

def get_access_token_from_local_storage(storage: WebLocalStorageManager) -> str:
    """
    Retrieve the access token from the local storage.
    Args:
        storage (LocalStorage): The local storage object to search for the access token.
    Returns:
        str: The access token if found, otherwise None.
    """

    for item in storage.items():
        if "accessToken" in item:
            return storage.get(item)


def get_id_token_from_local_storage(storage: WebLocalStorageManager) -> str:
    """
    Retrieves the ID token from the local storage.
    Args:
        storage (LocalStorage): The local storage object to search for the ID token.
    Returns:
        str: The ID token if found, otherwise None.
    """

    for item in storage.items():
        if "idToken" in item:
            return storage.get(item)

