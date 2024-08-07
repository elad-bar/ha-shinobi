from enum import Enum, StrEnum


class MonitorMode(StrEnum):
    STOP = "stop"
    START = "start"
    RECORD = "record"

    @staticmethod
    def get_list() -> list[str]:
        return list(MonitorMode)

    @staticmethod
    def get_icon(mode: str):
        icons = {
            str(MonitorMode.STOP): "mdi:cctv-off",
            str(MonitorMode.START): "mdi:cctv",
            str(MonitorMode.RECORD): "mdi:record-rec",
        }

        return icons.get(mode)


class RequestType(Enum):
    JSON = 0
    RESOURCE_CHECK = 1
    BYTES = 2
