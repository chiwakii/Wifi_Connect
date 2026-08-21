# 機能: pywifiで周辺のアクセスポイントを検索し、一覧を表示する。
# 入力: 無線LANアダプターから取得したスキャン結果。
# 出力: コンソールへの一覧表示と、同じフォルダーのaccess_points.jsonへの保存。
# 使用ライブラリ: pywifi、json、time、datetime、pathlib。
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pywifi


AUTH_DESCRIPTIONS = {
	pywifi.const.AUTH_ALG_OPEN: "オープン認証（認証なし）",
	pywifi.const.AUTH_ALG_SHARED: "共有キー認証",
}

AKM_DESCRIPTIONS = {
	pywifi.const.AKM_TYPE_NONE: "鍵管理なし",
	pywifi.const.AKM_TYPE_WPA: "WPA",
	pywifi.const.AKM_TYPE_WPAPSK: "WPA-PSK",
	pywifi.const.AKM_TYPE_WPA2: "WPA2",
	pywifi.const.AKM_TYPE_WPA2PSK: "WPA2-PSK",
}

CIPHER_DESCRIPTIONS = {
	pywifi.const.CIPHER_TYPE_NONE: "暗号化なし",
	pywifi.const.CIPHER_TYPE_WEP: "WEP",
	pywifi.const.CIPHER_TYPE_TKIP: "TKIP",
	pywifi.const.CIPHER_TYPE_CCMP: "CCMP（AES）",
}

JSON_FILE = Path(__file__).with_name("access_points.json")


def describe_value(value, descriptions, unknown_text):
	values = value if isinstance(value, list) else [value]
	described_values = [
		descriptions.get(item, f"{unknown_text}（{item}）")
		for item in values
		if item is not None
	]
	return ", ".join(described_values) or unknown_text


def load_saved_passwords():
	if not JSON_FILE.exists():
		return {}
	try:
		with JSON_FILE.open(encoding="utf-8") as json_file:
			saved_access_points = json.load(json_file)
	except (OSError, json.JSONDecodeError):
		return {}

	passwords = {}
	for access_point in saved_access_points:
		password = access_point.get("password", "")
		if password:
			if access_point.get("bssid"):
				passwords[("bssid", access_point["bssid"])] = password
			if access_point.get("ssid"):
				passwords[("ssid", access_point["ssid"])] = password
	return passwords


def scan_access_points():
	wifi = pywifi.PyWiFi()
	interfaces = wifi.interfaces()
	if not interfaces:
		raise RuntimeError("無線LANインターフェースが見つかりません")

	interface = interfaces[0]
	interface.scan()
	time.sleep(2)

	access_points = {}
	for result in interface.scan_results():
		ssid = result.ssid or "<SSID非公開>"
		current = access_points.get(ssid)
		if current is None or result.signal > current.signal:
			access_points[ssid] = result

	print(f"{'SSID':<32} {'信号強度':>8}  {'暗号方式'}")
	print("-" * 60)
	json_access_points = []
	saved_passwords = load_saved_passwords()
	scan_time = datetime.now(timezone.utc).isoformat()
	for ssid, result in sorted(
		access_points.items(), key=lambda item: item[1].signal, reverse=True
	):
		auth = getattr(result, "auth", None)
		akm_types = list(getattr(result, "akm", []))
		cipher = getattr(result, "cipher", None)
		auth_description = describe_value(auth, AUTH_DESCRIPTIONS, "不明な認証方式")
		akm_description = [
			describe_value(akm, AKM_DESCRIPTIONS, "不明な鍵管理方式")
			for akm in akm_types
		]
		cipher_description = describe_value(cipher, CIPHER_DESCRIPTIONS, "不明な暗号方式")
		security = ", ".join(akm_description) or "オープン（暗号化なし）"
		bssid = getattr(result, "bssid", None)
		password = saved_passwords.get(
			("bssid", bssid), saved_passwords.get(("ssid", ssid), "")
		)
		print(f"{ssid[:32]:<32} {result.signal:>5} dBm  {security}")
		json_access_points.append(
			{
				"scan_time": scan_time,
				"ssid": ssid,
				"password": password,
				"bssid": bssid,
				"signal": result.signal,
				"frequency_mhz": getattr(result, "freq", None),
				"auth": auth,
				"auth_description": auth_description,
				"akm": akm_types,
				"akm_description": akm_description,
				"cipher": cipher,
				"cipher_description": cipher_description,
				"security": security,
			}
		)

	with JSON_FILE.open("w", encoding="utf-8") as json_file:
		json.dump(json_access_points, json_file, ensure_ascii=False, indent=2)

	print("アクセスポイント一覧を access_points.json に保存しました。")


if __name__ == "__main__":
	try:
		scan_access_points()
	except Exception as error:
		print(f"スキャンに失敗しました: {error}")
