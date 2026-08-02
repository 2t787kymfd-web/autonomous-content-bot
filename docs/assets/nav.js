/* nav.js
   ヘッダーへのテレメトリ表示(「● 稼働中 ・ 最終更新: ...」)を自動で
   差し込む。{SITE_BASE_PATH}/assets/manifest.json (publisher.pyが公開の
   たびにupsertする)を読み込み、現在ページ自身のエントリを照合して表示する。
   相対パスではなくSITE_BASE_PATHからのルート相対パスを使う
   (src/theme.pyのSITE_BASE_PATHと同じ値。このファイルは静的アセットで
   Python側からテンプレート化されないため、値をここに直接複製している)。
   (旧: カテゴリ別ハンバーガーメニューもここで組み立てていたが、
   カテゴリ一覧はトップページのカードグリッドに一本化したため削除した)。 */

(function () {
  var SITE_BASE_PATH = "/autonomous-content-bot";

  /* 「観測盤」テレメトリ表示: ヘッダーに「● 稼働中 ・ 最終更新: ...」を
     自動で差し込む。manifest.json内の現在ページ自身のエントリ(slugで照合)
     からupdated_at(公開のたびに更新される、published_atとは別のフィールド)
     を読んで表示する。manifestに無いページ(index/about/privacy等)では
     何も表示しない。全ページ共通のヘルパーとして、テンプレート側の
     マークアップ変更なしに機能する(nav.js自身のトグルボタン等と同じ設計)。
     slugはカテゴリ別ディレクトリを含む(例: "finance/fx")ため、
     ファイル名だけでなくSITE_BASE_PATHを除いたパス全体で照合する。 */
  function injectTelemetry(manifest) {
    var header = document.querySelector(".site-header");
    if (!header) return;

    var path = decodeURIComponent(location.pathname);
    if (path.indexOf(SITE_BASE_PATH) === 0) {
      path = path.slice(SITE_BASE_PATH.length);
    }
    var currentSlug = path.replace(/^\//, "").replace(/\.html$/, "");
    var entry = (Array.isArray(manifest) ? manifest : []).find(function (e) {
      return e.slug === currentSlug;
    });
    if (!entry || !entry.updated_at) return;

    var d = new Date(entry.updated_at);
    var formatted = isNaN(d.getTime())
      ? entry.updated_at
      : d.toLocaleString("ja-JP", {
          year: "numeric", month: "2-digit", day: "2-digit",
          hour: "2-digit", minute: "2-digit",
        });

    var badge = document.createElement("div");
    badge.className = "telemetry-badge";
    var dot = document.createElement("span");
    dot.className = "telemetry-dot";
    var text = document.createElement("span");
    text.textContent = "稼働中 ・ 最終更新: " + formatted;
    badge.appendChild(dot);
    badge.appendChild(text);

    header.appendChild(badge);
  }

  function init() {
    fetch(SITE_BASE_PATH + "/assets/manifest.json")
      .then(function (res) {
        if (!res.ok) throw new Error("manifest.json not found (status " + res.status + ")");
        return res.json();
      })
      .then(injectTelemetry)
      .catch(function (err) {
        // manifest.jsonがまだ存在しない(初回公開前)等の場合はテレメトリ無しで静かに諦める
        console.warn("[nav] テレメトリ表示の読み込みに失敗しました:", err);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
