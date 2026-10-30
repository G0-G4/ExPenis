"""Controls only the temporary emulator and separate telemetrytest app."""

import os
import re
import sys
from shutil import which
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

ADB = (
    os.getenv("EXPENIS_E2E_ADB")
    or which("adb")
    or str(Path.home() / "Library/Android/sdk/platform-tools/adb")
)
SERIAL = "emulator-5580"
PACKAGE = "ru.g0g4.expenis.telemetrytest"
STATE = Path("/private/tmp/expenis-observability-e2e")


def adb(*args):
    return subprocess.check_output([ADB, "-s", SERIAL, *args], text=True)


def tree():
    adb("shell", "uiautomator", "dump", "/sdcard/expenis-e2e.xml")
    return ET.fromstring(adb("exec-out", "cat", "/sdcard/expenis-e2e.xml"))


def tap(node):
    x1, y1, x2, y2 = map(int, re.findall(r"\d+", node.attrib["bounds"]))
    adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))


def tap_label(label):
    for node in tree().iter("node"):
        value = node.get("content-desc", "") or node.get("text", "")
        if (value == label or value.startswith(label + "\n")) and node.get("clickable") == "true":
            tap(node)
            return
    raise AssertionError("Missing clickable test control: " + label)


def logs(query):
    response = httpx.get(
        "http://127.0.0.1:19428/select/logsql/query",
        params={"query": query},
        timeout=5,
        trust_env=False,
    )
    response.raise_for_status()
    return response.text


def main():
    if "--errors-only" not in sys.argv:
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
        for hint, value in [("Username", "telemetrye2e"), ("Password", "testpass123")]:
            node = next(n for n in tree().iter("node") if n.get("hint") == hint)
            tap(node)
            adb("shell", "input", "keyevent", "123", *(["67"] * 32))
            time.sleep(0.3)
            adb("shell", "input", "text", value)
            actual = next(n for n in tree().iter("node") if n.get("hint") == hint)
            if hint == "Username":
                assert actual.get("text") == value, "Synthetic username input mismatch"
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        tap_label("Login")
        for _ in range(10):
            time.sleep(1)
            if any(
                "Transactions" in (n.get("content-desc", "") + n.get("text", ""))
                for n in tree().iter("node")
            ):
                break
        else:
            raise AssertionError("Android login did not open transactions")
        time.sleep(4)  # the isolated backend uses 3-second access tokens
        tap_label("Accounts")
        time.sleep(2)
        (STATE / "database-unavailable").touch()
        try:
            tap_label("Categories")
            time.sleep(2)
            assert (
                httpx.get("http://127.0.0.1:18000/api/health/ready", trust_env=False).status_code
                == 503
            )
        finally:
            (STATE / "database-unavailable").unlink(missing_ok=True)
    for _ in range(30):
        time.sleep(1)
        output = logs("environment:=test origin:=client platform:=android")
        expected = (
            ("client_framework", "client_unhandled", "client_http")
            if "--errors-only" in sys.argv
            else ("client_http",)
        )
        if all(code in output for code in expected):
            break
    else:
        raise AssertionError("Expected Android error reports did not arrive")
    assert "testpass123" not in output and "telemetrye2e" not in output
    (STATE / "android.png").write_bytes(
        subprocess.check_output([ADB, "-s", SERIAL, "exec-out", "screencap", "-p"])
    )
    print(
        "PASS Android "
        + (
            "framework/unhandled error delivery"
            if "--errors-only" in sys.argv
            else "UI login, refresh/retry and handled 500"
        )
        + ", privacy canaries"
    )


if __name__ == "__main__":
    main()
