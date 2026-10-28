import os
import shutil
import subprocess
import sys

TIMEOUT_S = 10
TITLE_ENV = "TRUAPPLY_NOTICE_TITLE"
MESSAGE_ENV = "TRUAPPLY_NOTICE_MESSAGE"
POWERSHELL_ID = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe"
WINDOWS_TOAST = (
    "$n = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications,"
    " ContentType = WindowsRuntime];"
    " $t = $n::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
    " $x = $t.GetElementsByTagName('text');"
    f" $x.Item(0).InnerText = $env:{TITLE_ENV};"
    f" $x.Item(1).InnerText = $env:{MESSAGE_ENV};"
    f" $n::CreateToastNotifier('{POWERSHELL_ID}').Show("
    "[Windows.UI.Notifications.ToastNotification]::new($t))"
)


def _quoted(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _command(title: str, message: str) -> list[str] | None:
    if sys.platform == "win32":
        tool = shutil.which("powershell")
        return [tool, "-NoProfile", "-NonInteractive", "-Command", WINDOWS_TOAST] if tool else None
    if sys.platform == "darwin":
        tool = shutil.which("osascript")
        script = f"display notification {_quoted(message)} with title {_quoted(title)}"
        return [tool, "-e", script] if tool else None
    tool = shutil.which("notify-send")
    return [tool, title, message] if tool else None


def send(title: str, message: str) -> None:
    command = _command(title, message)
    if command is None:
        return
    try:
        subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            check=False,
            timeout=TIMEOUT_S,
            env={**os.environ, TITLE_ENV: title, MESSAGE_ENV: message},
        )
    except (OSError, subprocess.SubprocessError):
        return
