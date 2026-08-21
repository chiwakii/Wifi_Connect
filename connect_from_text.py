# 機能: access_points.jsonからSSIDを選び、テキストファイルのパスワードで接続する。
# 入力: access_points.jsonのAP情報、接続番号、wifi_password.tctの内容。
# 出力: Wi-Fi接続の成否をコンソールへ表示する。
# 使用ライブラリ: pathlib（ファイル操作）、connect_from_json（JSON読み込みと接続処理）。
from pathlib import Path

from connect_from_json import connect_to_access_point, load_access_points


PASSWORD_FILE = Path(__file__).with_name("wifi_password.txt")
counter=0

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
        
    pass_file = open(PASSWORD_FILE,"r",encoding="utf-8")
    #password = load_password()
    for index, access_point in enumerate(access_points, start=1):
            print(f"{index}: {access_point['ssid']} ({access_point.get('security', '不明')})")
    while True:
        # for index, access_point in enumerate(access_points, start=1):
        #     print(f"{index}: {access_point['ssid']} ({access_point.get('security', '不明')})")

        # try:
        #     choice = int(input("接続する番号を入力してください: ")) - 1
        #     if choice < 0 or choice >= len(access_points):
        #         raise ValueError
        # except ValueError:
        #     print("番号が正しくありません。もう一度入力してください。")
        #     continue
        #######
        password = pass_file.read().strip()
        if not password:
            print("パスワードファイルが空です。終了します。")
            break    
        choice = 3
        ########
        selected = access_points[choice]
        if connect_to_access_point(selected, password):
            print(f"{selected['ssid']} に接続しました")
            return

        # print(f"{selected['ssid']} に接続できませんでした。別の番号を選択してください。")
        print("|",password,end=" ")
    print("")

if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError, RuntimeError) as error:
        print(f"接続に失敗しました: {error}")
