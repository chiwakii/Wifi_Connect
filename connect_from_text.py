# 機能: access_points.jsonからSSIDを選び、テキストファイルのパスワードで接続する。
# 入力: access_points.jsonのAP情報、接続番号、wifi_password.txtの内容。
# 出力: Wi-Fi接続の成否をコンソールへ表示する。
# 使用ライブラリ: pathlib（ファイル操作）、connect_from_json（JSON読み込みと接続処理）。
import argparse
import time
from pathlib import Path
import pywifi

from connect_from_json import (
    connect_to_access_point,
    get_previous_connection,
    load_access_points,
    reconnect_to_previous_ssid,
)


DEFAULT_WORDLIST_PATH = Path(__file__).resolve().parent.parent / "wordlist" / "wordlist_5.txt"
DEFAULT_PREVIEW_LIMIT = 5


def parse_args():
    parser = argparse.ArgumentParser(description="選択した AP に対して候補パスワードを順に試します。")
    parser.add_argument(
        "--wordlist",
        type=Path,
        default=DEFAULT_WORDLIST_PATH,
        help="読み込む候補パスワードのファイルパス（既定: wordlist/wordlist_5.txt）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_PREVIEW_LIMIT,
        help="1回に試す候補の最大件数（既定: 5）",
    )
    parser.add_argument(
        "--ssid",
        type=str,
        default=None,
        help="対象 SSID を直接指定して、一覧選択を省略します。部分一致にも対応します。",
    )
    parser.add_argument(
        "--log-failed",
        type=Path,
        default=None,
        help="失敗した候補をファイルに保存します（例: failed.txt）",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="接続候補の一覧表示を省略し、対象 SSID のみを試します。",
    )
    return parser.parse_args()


def load_passwords(wordlist_path, limit=None):
    if not wordlist_path.exists():
        raise FileNotFoundError(
            f"パスワードファイルが見つかりません: {wordlist_path}"
        )

    passwords = []
    with wordlist_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            password = line.strip()
            if not password:
                continue
            passwords.append(password)
            if limit is not None and len(passwords) >= limit:
                break

    if not passwords:
        raise ValueError("パスワードファイルが空です")
    return passwords


def redact(value):
    if value is None:
        return "<hidden>"
    text = str(value)
    if not text:
        return "<hidden>"
    return "***"


def main():
    args = parse_args()
    preview_limit = max(1, args.limit)
    wordlist_path = args.wordlist.resolve()
    log_failed_path = args.log_failed.resolve() if args.log_failed is not None else None

    access_points = load_access_points()
    if not access_points:
        raise RuntimeError("接続候補がJSONにありません")

    interface = pywifi.PyWiFi().interfaces()[0]
    previous_ssid, previous_profile = get_previous_connection(interface)
    passwords = load_passwords(wordlist_path, limit=preview_limit)
    print(f"候補ファイル: {wordlist_path.name}")
    print(f"試行件数: {preview_limit}")
    if log_failed_path is not None:
        print(f"失敗ログ: {log_failed_path.name}")

    if args.ssid is not None:
        matches = [
            ap for ap in access_points if args.ssid.lower() in ap.get("ssid", "").lower()
        ]
        if not matches:
            raise ValueError(f"SSID が見つかりません: {args.ssid}")
        access_point_list = matches
    else:
        access_point_list = access_points

    while True:
        if not args.quiet:
            for index, access_point in enumerate(access_point_list, start=1):
                signal = access_point.get("signal", "不明")
                signal_level = access_point.get("signal_level", "不明")
                ssid = redact(access_point.get('ssid'))
                print(
                    f"{index}: {ssid} "
                    f"[{signal_level}, {signal} dBm] "
                    f"({access_point.get('security', '不明')})"
                )
            if args.ssid is None:
                print("0: プログラムを終了")

        try:
            if args.ssid is not None:
                choice = 0
            else:
                choice = int(input("接続する番号を入力してください: ")) - 1
            if choice == -1:
                reconnect_to_previous_ssid(interface, previous_ssid, previous_profile)
                print("プログラムを終了します。")
                return
            if choice < 0 or choice >= len(access_point_list):
                raise ValueError
        except ValueError:
            if args.ssid is not None:
                return
            print("番号が正しくありません。もう一度入力してください。")
            continue

        selected = access_point_list[choice]
        preview_passwords = passwords[:preview_limit]
        total = len(preview_passwords)
        started_at = time.time()
        attempted = []
        print(f"\r対象 SSID: {redact(selected.get('ssid'))} に対して上から {total} 件の候補を試します…")
        matched = False
        try:
            for index, password in enumerate(preview_passwords, start=1):
                elapsed = time.time() - started_at
                percent = (index / total) * 100
                bar_width = 20
                filled = int(percent / 100 * bar_width)
                bar = "#" * filled + "." * (bar_width - filled)
                remaining_seconds = max(0.0, (elapsed / index) * (total - index)) if index > 0 else 0.0
                status = (
                    f"[{bar}] {index}/{total} ({percent:5.1f}%) "
                    f"経過 {elapsed:5.1f}s | 残り {remaining_seconds:5.1f}s | {password}"
                )
                print(f"\r{status}", end="", flush=True)

                if connect_to_access_point(selected, password, restore_previous=False):
                    print(f"\r対象 SSID {redact(selected.get('ssid'))} に接続しました: {password}")
                    matched = True
                    break

                attempted.append(password)
                print(f"\r{status} -> 失敗", end="", flush=True)
        finally:
            if reconnect_to_previous_ssid(interface, previous_ssid, previous_profile):
                print("\r元の接続先へ戻しました。", flush=True)
            else:
                print("\r元の接続先への復帰を試みました。", flush=True)

        if matched:
            print(f"\r対象 SSID {redact(selected.get('ssid'))} への接続試験を完了しました。")
            return

        elapsed = time.time() - started_at
        print()
        print(
            f"対象 SSID {redact(selected.get('ssid'))} で上から {total} 件の確認を終了しました。"
            f" (合計 {elapsed:.1f}s)"
        )
        if attempted:
            print("試行した候補: " + ", ".join(attempted))
            if log_failed_path is not None:
                log_failed_path.parent.mkdir(parents=True, exist_ok=True)
                log_failed_path.write_text(
                    "\n".join(attempted) + "\n",
                    encoding="utf-8",
                )
                print(f"失敗候補を保存しました: {log_failed_path}")
        if args.ssid is None:
            print("別の番号を選択するか、0で終了してください。")
        else:
            return

if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError, RuntimeError) as error:
        print(f"接続に失敗しました: {error}")
