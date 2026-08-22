# 機能: access_points.jsonからアクセスポイントを選び、pywifiで接続する。
# 入力: access_points.jsonのAP情報、接続番号、必要な場合はWi-Fiパスワード。
# 出力: Wi-Fi接続の成否をコンソールへ表示する。
# 使用ライブラリ: pywifi、json、getpass、time、pathlib。
import getpass
import json
import subprocess
import time
from pathlib import Path

import pywifi
from pywifi import const


JSON_FILE = Path(__file__).with_name("access_points.json")
DISCONNECT_WAIT_SECONDS = 0.2
CONNECTION_TIMEOUT_SECONDS = 2.0
STATUS_CHECK_INTERVAL_SECONDS = 0.1


def load_access_points():
	with JSON_FILE.open(encoding="utf-8") as json_file:
		access_points = json.load(json_file)
	if not isinstance(access_points, list):
		raise ValueError("JSONの形式が正しくありません（配列が必要です）")
	return [access_point for access_point in access_points if access_point.get("ssid")]


def get_connected_ssid():
	try:
		result = subprocess.run(
			["netsh", "wlan", "show", "interfaces"],
			capture_output=True,
			text=True,
			encoding="utf-8",
			check=False,
		)
	except OSError:
		return None

	for line in result.stdout.splitlines():
		if line.strip().startswith("SSID") and "BSSID" not in line:
			return line.split(":", 1)[-1].strip()
	return None


def get_previous_connection(interface):
	previous_ssid = get_connected_ssid()
	previous_profiles = interface.network_profiles()
	previous_profile = next(
		(profile for profile in previous_profiles if profile.ssid == previous_ssid),
		None,
	)
	return previous_ssid, previous_profile


def reconnect_to_previous_ssid(interface, previous_ssid, previous_profile):
	if not previous_ssid:
		return False

	result = subprocess.run(
		["netsh", "wlan", "connect", f"name={previous_ssid}"],
		capture_output=True,
		text=True,
		encoding="utf-8",
		check=False,
	)
	if result.returncode != 0:
		detail = (result.stdout or result.stderr).strip()
		print(f"元の接続先「{previous_ssid}」への再接続に失敗しました。{detail}")
		return False

	deadline = time.monotonic() + CONNECTION_TIMEOUT_SECONDS
	while time.monotonic() < deadline:
		if interface.status() == const.IFACE_CONNECTED:
			print(f"元の接続先「{previous_ssid}」へ再接続しました。")
			return True
		time.sleep(STATUS_CHECK_INTERVAL_SECONDS)

	print(f"元の接続先「{previous_ssid}」への再接続を確認できませんでした。")
	return False


def connect_to_access_point(access_point, password="", restore_previous=True):
	wifi = pywifi.PyWiFi()
	interfaces = wifi.interfaces()
	if not interfaces:
		raise RuntimeError("無線LANインターフェースが見つかりません")

	interface = interfaces[0]
	previous_ssid, previous_profile = get_previous_connection(interface)
	interface.disconnect()
	time.sleep(DISCONNECT_WAIT_SECONDS)

	profile = pywifi.Profile()
	profile.ssid = access_point["ssid"]
	profile.auth = const.AUTH_ALG_OPEN
	profile.akm = []
	akm_types = access_point.get("akm", [])
	if not isinstance(akm_types, list):
		akm_types = [akm_types]

	if const.AKM_TYPE_WPA2PSK in akm_types:
		profile.akm.append(const.AKM_TYPE_WPA2PSK)
		profile.cipher = const.CIPHER_TYPE_CCMP
		profile.key = password
	elif const.AKM_TYPE_WPAPSK in akm_types:
		profile.akm.append(const.AKM_TYPE_WPAPSK)
		profile.cipher = const.CIPHER_TYPE_TKIP
		profile.key = password
	else:
		profile.akm.append(const.AKM_TYPE_NONE)
		profile.cipher = const.CIPHER_TYPE_NONE

	profile_id = interface.add_network_profile(profile)
	interface.connect(profile_id)
	deadline = time.monotonic() + CONNECTION_TIMEOUT_SECONDS
	while time.monotonic() < deadline:
		if interface.status() == const.IFACE_CONNECTED:
			return True
		time.sleep(STATUS_CHECK_INTERVAL_SECONDS)

	if restore_previous:
		reconnect_to_previous_ssid(interface, previous_ssid, previous_profile)
	return False


def main():
	access_points = load_access_points()
	if not access_points:
		raise RuntimeError("接続候補がJSONにありません")

	while True:
		for index, access_point in enumerate(access_points, start=1):
			signal = access_point.get("signal", "不明")
			signal_level = access_point.get("signal_level", "不明")
			print(
				f"{index}: {access_point['ssid']} "
				f"[{signal_level}, {signal} dBm] "
				f"({access_point.get('security', '不明')})"
			)

		try:
			choice = int(input("接続する番号を入力してください: ")) - 1
			if choice < 0 or choice >= len(access_points):
				raise ValueError
		except ValueError:
			print("番号が正しくありません。もう一度入力してください。")
			continue

		selected = access_points[choice]
		password = selected.get("password", "")
		if selected.get("akm") and not password:
			password = getpass.getpass("Wi-Fiパスワード: ")

		if connect_to_access_point(selected, password):
			print(f"{selected['ssid']} に接続しました")
			return

		print(f"{selected['ssid']} に接続できませんでした。別の番号を選択してください。")


if __name__ == "__main__":
	try:
		main()
	except (ValueError, OSError, RuntimeError) as error:
		print(f"接続に失敗しました: {error}")
