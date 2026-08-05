from PySide2.QtCore import QSettings


class SettingsManager:
    def __init__(self):
        self.settings = QSettings("MyDevTools", "SimpleGitClient")

    def load(self) -> dict:
        return {
            "last_repo_path": self.settings.value("last_repo_path", ""),
            "remote_url": self.settings.value("remote_url", ""),
            "token": self.settings.value("token", ""),
        }

    def save(self, repo_path: str, remote_url: str, token: str):
        self.settings.setValue("last_repo_path", repo_path)
        self.settings.setValue("remote_url", remote_url)
        self.settings.setValue("token", token)
