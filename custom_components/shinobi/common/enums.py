from homeassistant.backports.enum import StrEnum


class MonitorState(StrEnum):
    STOPPING = "stopping"
    STARTING = "starting"
    RECORDING = "recording"
    WATCHING = "watching"
    STOPPED = "stopped"
    DIED = "died"

    @staticmethod
    def get_list() -> list[str]:
        return list(MonitorMode)

    @staticmethod
    def is_online(state: str) -> bool:
        monitor_state = MonitorState(state.lower())
        is_online = monitor_state in [MonitorState.WATCHING, MonitorState.RECORDING]

        return is_online

    @staticmethod
    def is_recording(state: str) -> bool:
        monitor_state = MonitorState(state.lower())
        is_recording = monitor_state in [MonitorState.RECORDING]

        return is_recording


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
