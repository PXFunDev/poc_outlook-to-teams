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