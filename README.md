# Wi-Fi ツール

更新履歴は [CHANGELOG.md](CHANGELOG.md) に記録しています。

## 構成

- `wifi_scanner.py`: 周辺 AP をスキャンして `access_points.json` に保存します。
- `wifi_connection.py`: Wi‑Fi の接続実行、切断、接続状態確認、復帰を担当します。
- `wifi_probe.py`: パスワード候補を順に試し、進捗表示・再接続・失敗ログを管理します。
- `access_points.json`: スキャン結果と接続候補の保存先です。

## 必要条件

Windows の PowerShell または cmd で実行してください。

```powershell
py -m pip install pywifi comtypes
```

WSL2 では Wi‑Fi の制御 API が使えないため、実行環境は Windows 側が前提です。

## Quick Start

### 1. AP を収集する

```powershell
cd .\Wifi_Connect
py .\wifi_scanner.py
```

### 2. 一覧から接続する

```powershell
py .\wifi_connection.py
```

### 3. ワードリストで候補を試す

```powershell
py .\wifi_probe.py --wordlist ..\wordlist\wordlist_5.txt --limit 5
```

SSID を直接指定して一覧選択を省略できます。以下の `<TARGET_SSID>` は実際の SSID に置き換えてください。

```powershell
py .\wifi_probe.py --ssid "<TARGET_SSID>" --limit 10 --quiet
```

## 主要オプション

- `--wordlist`: 候補ファイルのパス
- `--limit`: 試す件数。`0` は範囲内の全件を実行
- `--start` / `--end`: 範囲指定
- `--ssid`: 対象 SSID を直接指定。部分一致対応
- `--preset`: `fast` / `balanced` / `safe`
- `--connect-timeout`: 接続待ちの秒数
- `--status-interval`: 接続確認の間隔
- `--log-failed`: 失敗候補をファイルに保存

例:

```powershell
py .\wifi_probe.py --wordlist ..\wordlist\wordlist_5.txt --start 1000 --end 2000
py .\wifi_probe.py --ssid "<TARGET_SSID>" --limit 10 --preset fast
py .\wifi_probe.py --ssid "<TARGET_SSID>" --limit 10 --log-failed .\failed.txt
```

## 挙動

- 接続試行中は進捗バーと残り時間を表示します。
- 成功しても失敗しても、最後に元の接続先へ戻そうとします。
- 失敗した候補は `--log-failed` を使って保存できます。
- 文字列の中身は最小限にして、SSID などの個人情報を表示しないようにしています。

## 注意事項

- `access_points.json` に平文パスワードを保存しないでください。
- Wi‑Fi のテストは実環境で行ってください。
- WSL2 ではこのツール群を実行しても Wi‑Fi 制御ができません。

Wi‑Fi のスキャン結果からパスワードを取得することはできません。
