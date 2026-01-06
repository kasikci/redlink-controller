from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EndpointConfig:
    base_url: str = "https://mytotalconnectcomfort.com"
    login_path: str = "/portal/"
    check_data_session_path: str = "/portal/Device/CheckDataSession/{device_id}"
    submit_control_changes_path: str = "/portal/Device/SubmitControlScreenChanges"
    get_schedule_path: Optional[str] = None
    submit_schedule_path: Optional[str] = None

    def url_for(self, path: str) -> str:
        if not path:
            raise ValueError("path is required")
        return self.base_url.rstrip("/") + "/" + path.lstrip("/")

    def check_data_session_url(self, device_id: str) -> str:
        return self.url_for(self.check_data_session_path.format(device_id=device_id))

    def submit_control_changes_url(self) -> str:
        return self.url_for(self.submit_control_changes_path)

    def get_schedule_url(self, device_id: str) -> Optional[str]:
        if not self.get_schedule_path:
            return None
        return self.url_for(self.get_schedule_path.format(device_id=device_id))

    def submit_schedule_url(self) -> Optional[str]:
        if not self.submit_schedule_path:
            return None
        return self.url_for(self.submit_schedule_path)
