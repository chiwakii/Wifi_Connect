# myPython

更新履歴と作業メモは [CHANGELOG.md](CHANGELOG.md) に記録しています。

## ファイル構成

### Wi-Fi関連

- `wifi_scanner.py`: `pywifi` で周辺のアクセスポイントをスキャンし、SSID、BSSID、信号強度、信号レベル、周波数、認証方式、暗号方式などを表示します。結果は `access_points.json` に保存され、既存のパスワード情報は保持されます。
- `connect_from_json.py`: `access_points.json` の一覧からアクセスポイントを選択して接続します。パスワードがJSONにない場合は、実行時に非表示で入力します。
- `connect_from_text.py`: `access_points.json` の一覧からSSIDを選択し、`wifi_password.tct` の内容をパスワードとして接続します。
- `access_points.json`: スキャン結果と接続情報を保存するJSONファイルです。現在は空の配列で、スキャンすると内容が更新されます。
- `wifi_password.tct`: `connect_from_text.py` が読み込むパスワードファイルです。1つのパスワードだけを記載します。

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
cd "C:\Users\admin\OneDrive\src\myPython"
py wifi_scanner.py
```

次に、JSONからアクセスポイントを選択して接続します。

```powershell
py connect_from_json.py
```

テキストファイルからパスワードを読み込んで接続する場合は、`wifi_password.tct` にパスワードを記載してから実行します。

```powershell
py connect_from_text.py
```

`access_points.json` の `password` に値を設定すると、そのパスワードが接続に使用されます。空欄の場合は、接続時にパスワードを入力します。パスワードをJSONに保存する場合は平文になるため、ファイルを共有・公開しないでください。

Wi-Fiのスキャン結果からパスワードを取得することはできません。
