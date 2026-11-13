# Outlook to Teams PoC

クラシックOutlookの指定フォルダーに追加されたメールを、Teamsチャネルの
メールアドレスへ転送するPythonのPoCです。振り分け条件はOutlookのルールで設定します。
本文・添付ファイルはOutlookの転送機能に引き継がせます。

## 前提条件

- WindowsとPython 3.12、[uv](https://docs.astral.sh/uv/)。
- **クラシックOutlook**のデスクトップ版。新しいOutlookは対象外です。
  メールを送受信できるプロファイルを設定し、起動・サインインしておいてください。
- Teamsチャネルで「メールアドレスを取得」が利用でき、メール受信が許可されていること。
  Teams側の許可された送信元や、組織のメール転送ポリシーも確認してください。
- 監視するメールボックス・フォルダーへのアクセス権限。
  共有メールボックスを監視する場合は、Exchange / Microsoft 365上の共有受信トレイと
  対象サブフォルダーの読み取り権限が必要です。配布リストや別名アドレスだけでは、
  独立した共有メールボックスとして開けません。
- 送信に使用する個人用アカウントを、同じOutlookプロファイルに登録しておくこと。
  SMTPアドレスで送信アカウントを明示的に選びます。共有アドレスからの代理送信や
  「差出人として送信」は使用しません。

## 準備

PowerShellで、リポジトリのルートから実行します。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
uv sync --locked
```

実行ポリシーにより有効化できない場合は、組織の方針に従ってください。
有効化せず実行する場合も、`uv run`はプロジェクトの`.venv`を使用します。

## 設定と実行

Outlookで「受信トレイ」の下に「Teams転送」フォルダーを作成し、
転送したいメールをそのフォルダーへ移動するルールを設定します。
`outlook_to_teams.py`の先頭にある定数を編集してください。
転送先は**チャンネルIDではなく、Teamsチャネルで取得したメールアドレス**です。

個人メールボックスなど、Outlook左ペインの最上位に表示される受信箱を監視する設定です。

```python
OUTLOOK_MAILBOX = "Outlookに表示されるメールボックス名"
SHARED_MAILBOX_EMAIL = ""
OUTLOOK_FOLDER = ("受信トレイ", "Teams転送")
SENDER_EMAIL = "personal@example.com"
TEAMS_CHANNEL_EMAIL = "channel@example.com"
```

`OUTLOOK_MAILBOX`にはOutlook左ペインの最上位の表示名を、
`OUTLOOK_FOLDER`にはその配下から監視フォルダーまでの名前を階層順に指定します。
最上位直下なら`("Teams転送",)`です。末尾のカンマを付けてください。
`SENDER_EMAIL`は送信元の個人用アカウントのSMTPアドレス、
`TEAMS_CHANNEL_EMAIL`は実際のチャネルのメールアドレス1件に置き換えてください。
必須の設定が空のままの場合は、起動時にエラーになります。
認証情報の入力や`.env`の作成は不要です。

共有メールボックスのメールを個人用アカウントから転送する場合は、次のように設定します。

```python
OUTLOOK_MAILBOX = ""
SHARED_MAILBOX_EMAIL = "shared@example.com"
OUTLOOK_FOLDER = ("Teams転送",)
SENDER_EMAIL = "personal@example.com"
TEAMS_CHANNEL_EMAIL = "channel@example.com"
```

`SHARED_MAILBOX_EMAIL`を指定すると、表示名ではなく共有アドレスを解決して、
その共有受信トレイを開きます。`OUTLOOK_MAILBOX`は使用しません。
この場合の`OUTLOOK_FOLDER`は**共有受信トレイからの相対階層**で、
`"受信トレイ"`は含めません。共有受信トレイ自体を監視する場合は`()`にします。
共有受信トレイ以外のフォルダーを指定したい場合は、Outlookに追加済みの
メールボックスを`OUTLOOK_MAILBOX`で指定する方式を使用してください。
1回の起動で監視するフォルダーは1つです。個人用と共有の両方を同時に監視する場合は、
異なる対象フォルダーを指定した別プロセスで実行します。

設定後は引数なしで実行できます。

```powershell
uv run python .\outlook_to_teams.py
```

必要な場合は、コマンドライン引数で各定数の値を上書きできます。

```powershell
uv run python .\outlook_to_teams.py `
  --mailbox "Outlookに表示されるメールボックス名" `
  --folder "受信トレイ" "Teams転送" `
  --sender-email "personal@example.com" `
  --teams-email "チャネルのメールアドレスに置き換えてください"
```

共有受信トレイ配下の例です。

```powershell
uv run python .\outlook_to_teams.py `
  --shared-mailbox "shared@example.com" `
  --folder "Teams転送" `
  --sender-email "personal@example.com" `
  --teams-email "channel@example.com"
```

共有受信トレイ自体を監視する場合は、`--folder`の直後に名前を付けず、
次のオプションへ進みます。共有の定数設定を通常の監視へ戻す場合は、
`SHARED_MAILBOX_EMAIL = ""`に戻し、`OUTLOOK_MAILBOX`と階層も設定し直してください。

`--teams-email`には実際のメールアドレスを1件だけ指定してください。
`--mailbox`にはOutlook左ペインの最上位の表示名を指定します。
`--folder`には、その配下から監視フォルダーまでの名前を階層順に渡します。
最上位直下のフォルダーなら`--folder "Teams転送"`です。
名前に空白がある場合も、階層ごとに引用符で囲んでください。
認証情報の入力や`.env`の作成は不要です。

## 動作と制限

- 起動時のメールを記録した後、約10秒間隔で確認します。
  **起動時に既にあるメールは転送しません。停止中に追加されたメールも、
  再起動時には既存メールとして除外します。**
- 起動後に追加されたメールのみを転送します。**元メールは監視フォルダーに残し、
  移動・削除や転送済みフォルダーの作成は行いません。**
  送信依頼が成功したメールのEntryIDをメモリに記録し、起動中の重複送信を防ぎます。
  記録はファイルに保存しません。再起動時は、その時点の全既存メールを除外します。
  予定や会議出席依頼など、通常のメール以外は転送しません。
- `Ctrl+C`で終了します。PCのスリープ中は処理できません。
  Outlookを起動したまま、同じWindowsユーザーの対話セッションで利用し、
  **同じフォルダーを監視するプログラムを多重起動しないでください。**
- Outlookのセキュリティ設定によっては送信確認が表示されます。
  ポリシーを無断で変更せず、管理者へ確認してください。
- 指定した個人用の送信アカウントが見つからない場合や、共有アドレスを解決できない場合、
  共有受信トレイへアクセスできない場合は停止します。別の受信箱や既定の送信元に
  自動で切り替えることはありません。別のOutlookプロファイルへの切り替えは対象外です。
- `Send()`はOutlookへの送信依頼であり、Teamsへの配信完了ではありません。
  オフライン時は送信トレイに残ることがあります。送信トレイ・送信済みアイテム・
  配信不能通知・Teamsの投稿を別途確認してください。
- 設定不備やCOM操作の失敗はエラーを表示して停止します。自動再試行は行いません。
  送信中の障害では送信成否が不明になることがあります。
  再起動時には未送信メールも既存メールとして除外され、自動再送されません。
  コピーやフォルダー移動でEntryIDが変わると別メールとして転送される可能性があるため、
  手動で再投入する際は未送信か確認してください。厳密な一度限りの配信保証はありません。
- ポーリングの間に追加・削除されたメールは検出できません。
  専用の監視フォルダーを使用し、運転中の手動移動は避けてください。
  フォルダー全体を確認する小規模PoCで、大量メールの処理や常駐サービス化は対象外です。
- Teamsの受信制限により、添付ファイルの種類やサイズなどによって配信されない場合があります。
  機密メールを転送しないよう、OutlookルールとTeamsチャネルの閲覧権限を確認してください。

## 検証

Outlookを使用しない単体テストと規約・構文チェックです。

```powershell
uv run python -m unittest discover -s tests -v
uv run ruff check .
uv run ruff format --check .
uv run python -m compileall -q outlook_to_teams.py tests
```

実機での疎通確認では、テスト用メールボックス・チャネルを使用してください。
起動前に監視フォルダーへテストメールを1件置き、起動後に別のテストメールを追加します。
起動後のメールだけがTeamsへ届き、起動前後のどちらの元メールも監視フォルダーに残ること、
本文と添付ファイルが期待どおりであることを確認してください。
そのまま複数回の監視間隔を待ち、二重投稿されないことも確認します。
停止中に追加したメールが再起動後も対象外になることを確認してください。
個人メールボックスと共有メールボックスの両方で確認し、共有メールの転送でも
差出人が`SENDER_EMAIL`の個人用アドレスになっていることを確認してください。
共有受信箱の読み取り権限がない場合や送信元が未登録の場合に停止することも確認します。
単体テストはCOMをモックしており、実際のOutlook送信やTeams配信の成功は保証しません。

---

# copilot-harness-template
GitHub Copilot のハーネスのテンプレート

## ひな形

新しいリポジトリへコピーし、角括弧で囲まれた項目と対象パスをプロジェクトに合わせて編集してください。
既存の実例はそのまま残し、用途別のひな形は `.github/templates/` にまとめています。

| 用途 | ひな形 | 主に記載すること |
| --- | --- | --- |
| リポジトリ共通の指示 | [copilot-instructions.md](.github/templates/copilot-instructions.md) | 前提、規約、検証方法、禁止事項 |
| パス別の指示 | [path.instructions.md](.github/templates/path.instructions.md) | `applyTo` の対象パスと、その範囲だけの規約 |
| 専門Agent | [agent.agent.md](.github/templates/agent.agent.md) | 役割、対象範囲、手順、制約、成果物 |
| 繰り返し使う依頼 | [prompt.prompt.md](.github/templates/prompt.prompt.md) | 入力変数、依頼内容、期待する出力 |
| 再利用する作業手順 | [SKILL.md](.github/templates/skill/SKILL.md) | 使用条件、手順、完了基準、出力 |

各ひな形は単独でも利用できます。実際に読み込まれる配置先は後述の機能一覧を、front matter の形式は各ひな形を参照してください。

## 3つのエンジニアリングの違い

| 領域 | 設計対象 |
|--------|--------|
| プロンプトエンジニアリング | 今回の依頼 |
| コンテキストエンジニアリング | 判断材料 |
| ハーネスエンジニアリング | 任せ方全体 |

---

### 1. プロンプトエンジニアリング

AIへの指示文を設計する。

#### 例

```text
顧客管理システムに
ログイン機能を追加してください。
```

---

### 2. コンテキストエンジニアリング

AIへ渡す情報を設計する。

#### 例

```text
要件定義書
設計書
コーディング規約
既存ソースコード
関連Issue
```

---

### 3. ハーネスエンジニアリング

AIへ仕事をどう任せるかを設計する。

#### 例

```text
要件分析Agent
    ↓
設計Agent
    ↓
実装Agent
    ↓
レビューAgent
    ↓
テストAgent
```

また、

```text
レビュー
テスト
ガードレール
メモリ
証跡管理
```

なども含みます。

---

## GitHub Copilotのハーネス

> custom-instructions / AGENT / SKILL / PROMPT

- Copilot全体 / Agent毎 / スキル毎 / 依頼毎の情報をまとめる
- 適切なレイヤーに適切な情報を置き、Agentの挙動を統制

| 機能 | ファイル / 場所 | ここに書くべき情報 | 読み込まれるタイミング |
|--------|--------|--------|--------|
| Custom instructions | `.github/copilot-instructions.md` | リポジトリ共通の前提・コーディング規約・ビルドテスト手順・「やってはいけないこと」。コードから読み取れない事項だけを簡潔に。 | リポジトリをコンテキストに含めたとき |
| Path-specific instructions | `.github/instructions/*.instructions.md` | 特定ディレクトリ/言語だけのルール（API規約、DBルール等）。front matter の `applyTo` で対象パスを指定。 | `applyTo` のパスに一致したとき |
| Prompt files | `.github/prompts/*.prompt.md` | 繰り返し使う依頼のテンプレート（PRレビュー、テスト生成、移行手順）。入力変数を持たせる。 | `/コマンド` で明示的に呼び出したとき |
| Custom agents | `.github/agents/AGENT-NAME.agent.md`<br>（org / enterprise / ユーザー単位も可） | 専門ペルソナの定義・役割・守らせる手順・使用可能ツールの制限・参照コンテキスト | チャットでそのAgentを選択したとき |
| Agent skills | `.github/skills/<skill-name>/SKILL.md`<br>（＋スクリプトや参照資料を同梱） | 特定作業の手順書と付随リソース。description に「いつ使うか」を明記（これで呼び出しが決まる） | タスクに関連すると判断されたとき自動 |

## copilot-instructions.md に書くこと

> .github/copilot-instructions.md

- リポジトリ共通の前提
- コーディング規約
- 検証方法
- 許可範囲・禁止範囲
- その他、コードから読み取れないこと

## agents/~.agent.md に書くこと

> .github/agents/<name>.agent.md

- 役割・担当する範囲
- 入力・参照する資料
- 利用ツール・変更可能範囲
- model指定
- 返す成果・停止条件

## カスタムスキル：<スキル名>/SKILL.md に書くこと

> .github/skills/<スキル名>/SKILL.md

- 使用する場面・対象作業
- 再利用する具体的な手順
- 参照資料・判定基準
- 出力の形式

要件定義/設計/実装/テストなどの作業について記載する。
記載することは、description/scope/参照資料/ツール・・・など