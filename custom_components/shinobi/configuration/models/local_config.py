from __future__ import annotations


class LocalConfig:
    use_original_stream: bool

    def __init__(self):
        self.use_original_stream = False

    @staticmethod
    def from_dict(obj: dict):
        data = LocalConfig()

        if obj is not None:
            data.use_original_stream = obj.get("useOriginalStream", False)

        return data

    def to_dict(self):
        obj = {
            "useOriginalStream": self.use_original_stream
        }

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string
