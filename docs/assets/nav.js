/* nav.js
   ハンバーガーメニュー(カテゴリ別ナビゲーション)を自前で組み立てる。
   ./assets/manifest.json (publisher.pyが公開のたびにupsertする) を読み込み、
   カテゴリ別にグループ化したリンク一覧をスライドインパネルとして表示する。
   全ページが同一ディレクトリ(docs/)直下にフラットに置かれている前提で、
   相対パス "./assets/manifest.json" "./<slug>.html" を使う。
   ページ側のマークアップに依存せず、このスクリプト自身が必要なDOM
   (トグルボタン・オーバーレイ・パネル)を生成してbodyに追加する
   (テンプレートごとに専用のマウント要素を用意する必要が無いようにするため)。 */

(function () {
  function groupByCategory(manifest) {
    var categories = {};
    manifest.forEach(function (item) {
      var cat = item.category || "その他";
      if (!categories[cat]) categories[cat] = [];
      categories[cat].push(item);
    });
    return categories;
  }

  function buildPanel(categories) {
    var panel = document.createElement("nav");
    panel.className = "site-nav-panel";
    panel.setAttribute("aria-label", "カテゴリ別ツール一覧");

    var closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "site-nav-close";
    closeBtn.setAttribute("aria-label", "メニューを閉じる");
    closeBtn.textContent = "×";
    panel.appendChild(closeBtn);

    var heading = document.createElement("strong");
    heading.className = "site-nav-heading";
    heading.textContent = "カテゴリから探す";
    panel.appendChild(heading);

    var categoryNames = Object.keys(categories);
    if (categoryNames.length === 0) {
      var empty = document.createElement("p");
      empty.className = "site-nav-empty";
      empty.textContent = "まだ公開されているツールがありません。";
      panel.appendChild(empty);
    }

    categoryNames.sort().forEach(function (cat) {
      // カテゴリはクリックで展開するアコーディオン形式にする(縦一列に並べ、
      // 選択したカテゴリだけ中身を表示する)。tool_builder.pyのFAQセクションと
      // 同じ<details>/<summary>パターンを踏襲する。
      var section = document.createElement("details");
      section.className = "site-nav-category";

      var summary = document.createElement("summary");
      summary.textContent = cat;
      section.appendChild(summary);

      var ul = document.createElement("ul");
      categories[cat]
        .slice()
        .sort(function (a, b) {
          return (a.niche || "").localeCompare(b.niche || "", "ja");
        })
        .forEach(function (item) {
          var li = document.createElement("li");
          var a = document.createElement("a");
          a.href = "./" + item.slug + ".html";
          a.textContent = item.niche || item.slug;
          li.appendChild(a);
          ul.appendChild(li);
        });
      section.appendChild(ul);
      panel.appendChild(section);
    });

    var homeLink = document.createElement("a");
    homeLink.href = "./index.html";
    homeLink.className = "site-nav-home-link";
    homeLink.textContent = "← トップページへ戻る";
    panel.appendChild(homeLink);

    return { panel: panel, closeBtn: closeBtn };
  }

  function mount(manifest) {
    var categories = groupByCategory(Array.isArray(manifest) ? manifest : []);
    var built = buildPanel(categories);
    var panel = built.panel;
    var closeBtn = built.closeBtn;

    var overlay = document.createElement("div");
    overlay.className = "site-nav-overlay";

    var toggleBtn = document.createElement("button");
    toggleBtn.type = "button";
    toggleBtn.className = "site-nav-toggle";
    toggleBtn.setAttribute("aria-label", "メニューを開く");
    toggleBtn.innerHTML = "<span></span><span></span><span></span>";

    function openMenu() {
      panel.classList.add("is-open");
      overlay.classList.add("is-open");
      document.body.classList.add("site-nav-locked");
    }
    function closeMenu() {
      panel.classList.remove("is-open");
      overlay.classList.remove("is-open");
      document.body.classList.remove("site-nav-locked");
    }

    toggleBtn.addEventListener("click", openMenu);
    closeBtn.addEventListener("click", closeMenu);
    overlay.addEventListener("click", closeMenu);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeMenu();
    });

    document.body.appendChild(toggleBtn);
    document.body.appendChild(overlay);
    document.body.appendChild(panel);
  }

  function init() {
    fetch("./assets/manifest.json")
      .then(function (res) {
        if (!res.ok) throw new Error("manifest.json not found (status " + res.status + ")");
        return res.json();
      })
      .then(mount)
      .catch(function (err) {
        // manifest.jsonがまだ存在しない(初回公開前)等の場合はナビ無しで静かに諦める
        console.warn("[nav] メニューの読み込みに失敗しました:", err);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
