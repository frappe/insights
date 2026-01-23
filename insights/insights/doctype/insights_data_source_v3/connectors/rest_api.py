from urllib.parse import parse_qs

import frappe


class RestAPIClient:
    def __init__(self, data_source):
        self.data_source = data_source
        self.base_url = data_source.api_base_url
        self.headers = frappe.parse_json(data_source.api_custom_headers) or {}
        self.auth_type = data_source.api_authentication_type
        self.username = data_source.api_username
        self._password = data_source.get_password("api_password")
        self._token = data_source.get_password("api_token")

        self.session = self._create_session()

    def _create_session(self):
        import requests

        session = requests.Session()
        session.headers.update(self.headers)

        if self.auth_type == "None":
            pass  # No authentication needed
        elif self.auth_type == "API Key / Bearer Token":
            session.headers.update({"Authorization": f"Bearer {self._token}"})
        elif self.auth_type == "Basic Authentication":
            session.auth = (self.username, self._password)

        return session

    def test_connection(self):
        try:
            self.get("")
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to API: {e}")

    def request(self, method, endpoint, **kwargs):
        url = f"{self.base_url}/{endpoint}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()

        response_type = response.headers.get("content-type", "")
        if response_type.startswith("application/") and "json" in response_type:
            return response.json()
        elif response_type == "text/plain; charset=utf-8":
            return parse_qs(response.text)
        elif response.text:
            return response.text

    def get(self, endpoint, params=None):
        return self.request("GET", endpoint, params=params)

    def post(self, endpoint, data=None, json=None):
        return self.request("POST", endpoint, data=data, json=json)

    def put(self, *args, **kwargs):
        raise NotImplementedError("Data Source of type API does not support PUT requests.")

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Data Source of type API does not support DELETE requests.")
