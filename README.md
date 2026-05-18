# Apple整備済製品 監視ツール

Apple公式の整備済製品ページを定期監視し、対象モデルが追加・売り切れになったらLINEに通知するツールです。

## 動作概要

- GitHub Actionsが5分毎（24時間365日）に自動実行
- `config.yml` で監視対象モデルを自由に設定
- 新規入荷・売り切れをLINEに通知（自分だけにPush送信）
- `state.json` で通知済み状態を管理し、重複通知を防止

---

## セットアップ手順

### STEP 1｜LINE Messaging APIの設定

#### 1-1. プロバイダーを作成
1. [LINE Developers](https://developers.line.biz/) にアクセスしてログイン
2. 「プロバイダー」→「作成」をクリック
3. プロバイダー名を入力（例：`Apple監視`）→「作成」

#### 1-2. チャンネルを作成
1. 作成したプロバイダーを選択
2. 「チャンネル設定」→「チャンネル作成」→「Messaging API」を選択
3. 以下を入力して「作成」：
   - チャンネル名：`Apple整備品監視`（なんでもOK）
   - チャンネル説明：適当でOK
   - 大業種：個人 / 小業種：個人（その他）
4. 規約に同意

#### 1-3. チャンネルアクセストークンを発行
1. 作成したチャンネル →「Messaging API設定」タブ
2. 一番下「チャンネルアクセストークン（長期）」の「発行」をクリック
3. 表示されたトークンを**コピーしてメモ**

#### 1-4. あなたのユーザーIDを確認
1. 同じ「Messaging API設定」タブ内の「あなたのユーザーID」をコピーしてメモ
   - `Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` という形式

#### 1-5. 公式アカウントを友達追加
1. 同タブ内のQRコードをLINEで読み取り、友達追加

#### 1-6. アカウントを非公開にする（重要）
外部からの不正な友達追加を防ぐため、以下の設定をしてください。

1. [LINE Official Account Manager](https://manager.line.biz/) にログイン
2. 対象アカウントを選択 →「設定」→「アカウント設定」
3. 以下を設定：
   - **アカウントの公開設定**：「非公開」に変更
   - **検索結果に表示**：オフに変更
4. 「保存」をクリック

---

### STEP 2｜GitHubにリポジトリを作成

1. [GitHub](https://github.com) にログイン
2. 右上「+」→「New repository」
3. 以下を設定：
   - Repository name：`apple-refurbished-monitor`
   - **Public** を選択（無料で無制限に使うために必須）
   - 「Add a README file」にチェック
4. 「Create repository」をクリック

---

### STEP 3｜ファイルを配置

リポジトリページで「Add file」→「Create new file」を繰り返し、以下のファイルを作成します。

| ファイル名 | 内容 |
|---|---|
| `config.yml` | 監視設定ファイル |
| `monitor.py` | メイン監視スクリプト |
| `requirements.txt` | 依存パッケージ |
| `state.json` | 状態管理（初期値） |
| `.github/workflows/monitor.yml` | GitHub Actions設定 |

> **ポイント**：`.github/workflows/monitor.yml` はファイル名欄にそのまま入力するとフォルダが自動作成されます。

---

### STEP 4｜GitHub Secretsにトークンを登録

リポジトリの「Settings」→「Secrets and variables」→「Actions」→「New repository secret」で以下を登録：

| シークレット名 | 値 |
|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | STEP 1-3でメモしたトークン |
| `LINE_USER_ID` | STEP 1-4でメモしたユーザーID |

---

### STEP 5｜GitHub Actionsを有効化して動作確認

1. リポジトリの「Actions」タブを開く
2. 「I understand my workflows, go ahead and enable them」をクリック
3. 左メニューから「Apple整備済製品 監視」を選択
4. 「Run workflow」→「Run workflow」で手動実行
5. ログにエラーがなければ完了🎉

---

## 監視対象の設定方法

`config.yml` を編集して監視したいモデルを設定します。

```yaml
enabled: true  # false にすると監視停止

targets:
  - name: MacBook Pro 14インチ M5 24GB
    keywords:
      - "MacBook Pro"
      - "14"
      - "M5"
      - "24GB"

  # モデルを追加する場合はここにコピーして追記
  # - name: MacBook Pro 14インチ M5 Pro
  #   keywords:
  #     - "MacBook Pro"
  #     - "14"
  #     - "M5 Pro"
```

---

## 通知メッセージの例

**新規入荷時**
```
Apple整備品に「14インチMacBook Pro - M5チップ - 24GB」が追加しました！
価格：279800円
製品URL：https://www.apple.com/jp/shop/product/...
```

**売り切れ時**
```
Apple整備品「14インチMacBook Pro - M5チップ - 24GB」が売り切れました。
```

---

## 監視の一時停止

`config.yml` の `enabled` を `false` に変更してコミットするだけで停止できます。

---

## ファイル構成

```
.
├── .github/
│   └── workflows/
│       └── monitor.yml   # GitHub Actions設定
├── monitor.py            # メイン監視スクリプト
├── config.yml            # 監視設定（対象モデル・オンオフ）
├── state.json            # 状態管理（自動更新）
├── requirements.txt      # 依存パッケージ
└── README.md
```

---

## 注意事項

- AppleのページHTML構造が変わった場合、スクリプトの修正が必要になることがあります
- GitHub Actionsのスケジュール実行は数分の遅延が発生する場合があります
- LINE Messaging APIの無料枠は月200通です（在庫変動時のみ通知のため通常は余裕あり）
