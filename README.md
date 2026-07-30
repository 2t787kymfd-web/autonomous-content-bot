# autonomous-content-bot

「AIが自律的にコンテンツを作り、広告収益で自分の運用費を稼ぐ」ループの
プロトタイプです。Polymarketボットと同じ構造(観測→判断→実行→収支管理→
生存チェック)を、コンテンツ生成+広告収益というドメインに置き換えています。

## 現状の動作確認済みの点

- `python3 -m src.main_loop` を実行すると1サイクルが動きます(dry_runモード)
- 現状は `researcher.py` が「独自データなし」を返す実装のため、
  **意図的に何も生成・公開されません**。これはバグではなく安全側のデフォルトです。
  Google/YouTubeの2026年時点のポリシーは「独自の価値がないAI量産コンテンツ」を
  明確に狙い撃ちしているため、「データが無ければ作らない」をガードとして
  組み込んでいます。

## 実際に動かすために埋める部分(TODO)

| ファイル | やること |
|---|---|
| `src/researcher.py` | 為替・暗号資産以外のニッチ向けに一次情報を取得する処理を追加(現状は為替・暗号資産のみ実装済み) |
| `src/generator.py` / `src/judge.py` | `ANTHROPIC_API_KEY` を環境変数に設定すれば実際にAI生成・AI判断が動きます |
| `src/publisher.py` | 実装済み。`live`モードで`docs/`への書き出し後、GitHub Pagesへ`git push`まで自動実行されます |
| `src/revenue_tracker.py` | `manual`(`data/revenue_log.csv`に`date,amount_usd,niche`を追記)は実装済み。`adsense_api`はコード実装済みだがAdSenseアカウント未承認のため未検証。`ADSENSE_*`を`.env`に設定して使用します |
| `config.yaml` | ニッチの種、予算、しきい値、`reinvestment.*`を調整 |

## 実行方法

```bash
pip install -r requirements.txt --break-system-packages
export ANTHROPIC_API_KEY="sk-ant-..."   # 生成を実際に動かす場合
python3 -m src.main_loop
```

cronでの定期実行(`run_cycle.sh`がvenv有効化・.env読み込みまで行う):

```
*/30 * * * * /path/to/autonomous-content-bot/run_cycle.sh >> /path/to/autonomous-content-bot/data/run.log 2>&1
```

macOSの場合、`cron`(`/usr/sbin/cron`)がフルディスクアクセス権限を持っていないと
静かにジョブが実行されないことがある。ジョブ登録後は`data/run.log`が更新されて
いるか確認し、更新されない場合はシステム設定 > プライバシーとセキュリティ >
フルディスクアクセスで`cron`(または`/usr/sbin/crond`)を許可する。

## 生存の仕組み

`data/state.json` に残高・履歴が保存されます。
`config.yaml` の `survival.min_balance_to_operate_usd` を下回ると
`alive: false` になり、以後のサイクルは何もせず終了します
(Polymarket版の「残高ゼロで消滅」に相当)。

## 重要な注意点(必ず読んでください)

1. **「完全放置・最大量産」を目指すと収益化停止リスクが高い設計です。**
   2026年時点でGoogle検索/AdSenseは"scaled content abuse"、YouTubeは
   "inauthentic content"というポリシーで、独自性のない量産AIコンテンツを
   明確に対象にしています。このテンプレートは「独自データが無ければ
   生成しない」「既存記事と似すぎたら却下」というガードを標準搭載して
   いますが、これで規約違反を回避できると保証するものではありません。
2. **法的責任は運用者(あなた)にあります。** AIがどれだけ自律的に見えても、
   税務申告、著作権、各プラットフォームの利用規約遵守の責任は消えません。
3. **収益化には現実的な時間がかかります。** AdSense審査、検索順位が付くまでの
   期間など、"48時間で50ドルが3000ドルに"のような即効性は期待しないでください。
4. まずは `mode: dry_run` のまま、生成される記事の質やロジックを
   人間の目で確認してから `mode: live` に切り替えることを強く推奨します。

## ディレクトリ構成

```
autonomous-content-bot/
├── config.yaml          # 設定
├── requirements.txt
├── src/
│   ├── state.py          # 生存状態・ニッチ別損益の管理
│   ├── niche_scanner.py  # ニッチ探索(pytrends + Serper.dev)
│   ├── researcher.py     # 一次データ収集(為替・暗号資産のみ実装)
│   ├── judge.py          # 生成する価値があるかのAI判断
│   ├── generator.py      # AIによる記事生成
│   ├── quality_gate.py   # 独自性・薄さチェック
│   ├── publisher.py      # サイトへの公開(GitHub Pagesへgit push)
│   ├── revenue_tracker.py# 収益集計(manual / AdSense)
│   ├── reinvestment.py   # 再投資判断
│   └── main_loop.py      # 全体オーケストレーション
├── docs/                 # 生成されたHTMLの出力先(GitHub Pages配信元)
└── data/                 # state.json, revenue_log.csv など
```
