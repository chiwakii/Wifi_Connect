# 機能: access_points.jsonからSSIDを選び、テキストファイルのパスワードで接続する。
# 入力: access_points.jsonのAP情報、接続番号、wifi_password.txtの内容。
# 出力: Wi-Fi接続の成否をコンソールへ表示する。
# 使用ライブラリ: pathlib（ファイル操作）、connect_from_json（JSON読み込みと接続処理）。
from pathlib import Path
import pywifi

from connect_from_json import (
    connect_to_access_point,
    get_previous_connection,
    load_access_points,
    reconnect_to_previous_ssid,
)


PASSWORD_FILE = Path(__file__).with_name("wifi_password.txt")


def load_password():
    if not PASSWORD_FILE.exists():
        raise FileNotFoundError(
            f"パスワードファイルが見つかりません: {PASSWORD_FILE.name}"
        )

    password = PASSWORD_FILE.read_text(encoding="utf-8").strip()
    if not password:
        raise ValueError("パスワードファイルが空です")
    return password


def main():
    access_points = load_access_points()
    if not access_points:
        raise RuntimeError("接続候補がJSONにありません")

    interface = pywifi.PyWiFi().interfaces()[0]
    previous_ssid, previous_profile = get_previous_connection(interface)
    password = load_password()
    while True:
        for index, access_point in enumerate(access_points, start=1):
            signal = access_point.get("signal", "不明")
            signal_level = access_point.get("signal_level", "不明")
            print(
                f"{index}: {access_point['ssid']} "
                f"[{signal_level}, {signal} dBm] "
                f"({access_point.get('security', '不明')})"
            )
        print("0: プログラムを終了")

        try:
            choice = int(input("接続する番号を入力してください: ")) - 1
            if choice == -1:
                reconnect_to_previous_ssid(interface, previous_ssid, previous_profile)
                print("プログラムを終了します。")
                return
            if choice < 0 or choice >= len(access_points):
                raise ValueError
        except ValueError:
            print("番号が正しくありません。もう一度入力してください。")
            continue

        selected = access_points[choice]
        print(f"「{selected['ssid']}」に接続を試みています…")
        if connect_to_access_point(selected, password, restore_previous=False):
            print(f"{selected['ssid']} に接続しました")
            return

        print(f"「{selected['ssid']}」に接続できませんでした。")
        print("別の番号を選択するか、0で終了してください。")

if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError, RuntimeError) as error:
        print(f"接続に失敗しました: {error}")
