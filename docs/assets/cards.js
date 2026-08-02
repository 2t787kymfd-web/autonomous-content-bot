/* cards.js
   廃止済み。トップページのカードグリッドは、JavaScriptを実行しない
   クローラーや解析ツールにもツールへのリンクが見えるよう、
   publisher.py側でmanifest.jsonから静的HTMLとして直接index.htmlへ
   埋め込む方式に変更した(docs/index.htmlの<!-- CARDS:START -->〜
   <!-- CARDS:END -->を参照)。
   既存の公開済みページの一部がまだこのファイルをリンクしているため
   (再公開されるまで404を避けるため)、ファイル自体は空のまま残す。 */
