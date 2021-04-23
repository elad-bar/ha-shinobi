class APIRequestException(Exception):
    endpoint: str
    response: dict

    def __init__(self, endpoint, response):
        super().__init__(f"API Request failed")

        self.endpoint = endpoint
        self.response = response
