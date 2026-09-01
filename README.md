# myPython

更新履歴と作業メモは [CHANGELOG.md](CHANGELOG.md) に記録しています。

## ファイル構成

### Wi-Fi関連

- `wifi_scanner.py`: `pywifi` で周辺のアクセスポイントをスキャンし、SSID、BSSID、信号強度、信号レベル、周波数、認証方式、暗号方式などを表示します。結果は `access_points.json` に保存され、既存のパスワード情報は保持されます。
- `connect_from_json.py`: `access_points.json` の一覧からアクセスポイントを選択して接続します。パスワードがJSONにない場合は、実行時に非表示で入力します。
- `connect_from_text.py`: `access_points.json` の一覧からSSIDを選択し、候補パスワードのテキストファイルを順に試します。`--wordlist`、`--limit`、`--ssid`、`--quiet`、`--log-failed` を使って、候補の範囲や進捗を調整できます。
- `access_points.json`: スキャン結果と接続情報を保存するJSONファイルです。現在は空の配列で、スキャンすると内容が更新されます。
- `wordlist_5.txt`: 5桁の候補パスワードをまとめたテキストファイルです。大きな候補群を直接読むのではなく、先頭から必要件数だけ試すために使います。

### その他

- `kaggle_temp.py`: Kaggleの住宅価格データを使い、ランダムフォレスト回帰で予測します。入力は `../input/train.csv` と `../input/test.csv`、出力は `submission.csv` です。使用ライブラリは `pandas` と `scikit-learn` です。
- `test.py`: Hello World、正規表現、RSA暗号、拡張ユークリッド互除法を試す学習用スクリプトです。使用ライブラリは標準ライブラリの `re` と `pycryptodome` です。
- `cryptohack/Network_Attacks.py`: CryptoHackサーバーへ接続し、JSON形式のリクエストとレスポンスを送受信する学習用スクリプトです。使用ライブラリは `pwntools` と `json` です。

## Wi-Fiツールの準備

Windows側のPowerShellで必要なライブラリをインストールします。

```powershell
py -m pip install pywifi comtypes
```

WSL2では通常、Wi-Fiアダプターや `wpa_supplicant` を利用できません。Wi-Fi関連のスクリプトはWindows側のPythonで実行してください。

## Wi-Fiツールの使い方

まずアクセスポイントをスキャンしてJSONを作成します。

```powershell
cd .\Wifi_Connect
py wifi_scanner.py
```

次に、JSONからアクセスポイントを選択して接続します。

```powershell
py connect_from_json.py
```

候補ファイルからパスワードを読み込んで接続する場合は、まず対象の Wordlist を指定して実行します。

```powershell
py connect_from_text.py --wordlist ..\wordlist\wordlist_5.txt --limit 5
```

候補ファイルの途中から、または範囲を指定して実行することもできます。

```powershell
py connect_from_text.py --wordlist ..\wordlist\wordlist_5.txt --start 1000 --end 2000
py connect_from_text.py --wordlist ..\wordlist\wordlist_5.txt --start 1000 --limit 0
```

`--limit 0` は、その範囲内の全候補を実行します。ファイル全体をメモリに載せずに処理できるので、メモリ節約と全件網羅の両立が可能です。

SSID を直接指定して一覧選択を省略することもできます。

```powershell
py connect_from_text.py --ssid "JCOM" --limit 10 --quiet
```

速度と安定性を調整するには、`--preset` を使います。

```powershell
py connect_from_text.py --ssid "JCOM" --limit 10 --preset fast
py connect_from_text.py --ssid "JCOM" --limit 10 --preset balanced
py connect_from_text.py --ssid "JCOM" --limit 10 --preset safe
```

手動で詳細を指定する場合は、`--connect-timeout` と `--status-interval` を使います。

```powershell
py connect_from_text.py --ssid "JCOM" --limit 10 --preset fast --connect-timeout 0.3 --status-interval 0.01
```

失敗した候補を保存したい場合は、`--log-failed` を使います。

```powershell
py connect_from_text.py --ssid "JCOM" --limit 10 --log-failed .\failed.txt
```

### 実行例

`connect_from_text.py` では、候補ファイルの先頭から順にパスワードを試し、進捗バーと残り時間を表示します。接続が成功しても失敗しても、最後に元の接続先へ戻ります。

```text
PS ...\Wifi_Connect> py .\connect_from_text.py --ssid "JCOM" --limit 5 --quiet
候補ファイル: wordlist_5.txt
試行件数: 5
対象 SSID: *** に対して上から 5 件の候補を試します…
[##########............] 1/5 ( 20.0%) 経過  0.2s | 残り  0.8s | aaaaa
[##########............] 1/5 ( 20.0%) 経過  0.4s | 残り  0.6s | aaaaa -> 失敗
[################....] 2/5 ( 40.0%) 経過  0.7s | 残り  0.5s | aaaab
...
元の接続先へ戻しました。
```

### 推奨設定

- `fast`: 短時間で確認したいとき。候補数が少なく、雰囲気確認向け。
  ```powershell
  py .\connect_from_text.py --ssid "JCOM" --limit 10 --preset fast
  ```
- `balanced`: まずはこれを使うのが無難。速度と安定性のバランスが良い。
  ```powershell
  py .\connect_from_text.py --ssid "JCOM" --limit 10 --preset balanced
  ```
- `safe`: 安定重視。接続判定が厳しくなり、誤判定を減らしやすい。
  ```powershell
  py .\connect_from_text.py --ssid "JCOM" --limit 10 --preset safe
  ```

### 速さの目安

- `fast`: 1候補あたり 0.3〜0.5 秒程度を狙う
- `balanced`: 0.6〜1.0 秒程度を目安にする
- `safe`: 1.0 秒超で安定することが多い

実際の値は環境や Wi‑Fi アダプターの性能に依存するため、最初は `balanced` で開始し、必要なら `fast` または `safe` に調整するのが安全です。

`access_points.json` の `password` に値を設定すると、そのパスワードが接続に使用されます。空欄の場合は、接続時にパスワードを入力します。パスワードをJSONに保存する場合は平文になるため、ファイルを共有・公開しないでください。

`--wordlist` で候補ファイルを切り替え、`--limit` で試す件数を制御できます。`--ssid` を使えば一覧から選ばずに対象 SSID を直接指定できます。`--quiet` は一覧表示を省略し、`--log-failed` は失敗候補をログファイルに保存します。

Wi-Fiのスキャン結果からパスワードを取得することはできません。
