/* cards.js
   トップページ(index.html)のツールカード一覧を動的に組み立てる。
   {SITE_BASE_PATH}/assets/manifest.json (publisher.pyが公開のたびupsertする)
   を読み込み、カテゴリ別にグループ化したカードグリッドを表示する。
   カードのリンク先はカテゴリ別サブディレクトリを含むslug(例: finance/fx)の
   ため、nav.jsと同じくSITE_BASE_PATHからのルート相対パスを使う
   (このファイルは静的アセットでPython側からテンプレート化されないため、
   src/theme.pyのSITE_BASE_PATHと同じ値をここに直接複製している)。
   新しいkindが増えるたびにindex.htmlを手動編集する必要がないようにするため
   (nav.jsと同じ設計方針)。 */

(function () {
  var SITE_BASE_PATH = "/autonomous-content-bot";

  var CATEGORY_ICON = {
    "金融": "💹",
    "天気・防災": "⛅",
    "天文・暦": "🌌",
    "生活計算": "🧮",
    "暦・和文化": "📅",
    "国・地域・雑学": "🌐",
    "地理・開発者向け": "🗺️",
    "エンタメ": "🎵",
    "スポーツ": "⚽",
  };
  var DEFAULT_ICON = "🔧";

  // カテゴリ→theme.cssのゲージカラー変数名。カードの縁取りに使う
  // (「観測盤」コンセプト。theme.cssで定義されたCSS変数をそのまま参照する)。
  var CATEGORY_GAUGE_VAR = {
    "金融": "--gauge-finance",
    "天気・防災": "--gauge-weather",
    "天文・暦": "--gauge-astro",
    "生活計算": "--gauge-life",
    "暦・和文化": "--gauge-culture",
    "国・地域・雑学": "--gauge-trivia",
    "地理・開発者向け": "--gauge-geo",
    "エンタメ": "--gauge-entertainment",
    "スポーツ": "--gauge-sports",
  };
  var DEFAULT_GAUGE_VAR = "--gauge-default";

  // ハンバーガーメニュー(nav.js)と表示順を揃える
  var CATEGORY_ORDER = [
    "金融", "天気・防災", "天文・暦", "生活計算", "暦・和文化",
    "国・地域・雑学", "地理・開発者向け", "エンタメ", "スポーツ", "その他",
  ];

  function groupByCategory(manifest) {
    var categories = {};
    manifest.forEach(function (item) {
      var cat = item.category || "その他";
      if (!categories[cat]) categories[cat] = [];
      categories[cat].push(item);
    });
    return categories;
  }

  function buildCard(item) {
    var icon = CATEGORY_ICON[item.category] || DEFAULT_ICON;
    var gaugeVar = CATEGORY_GAUGE_VAR[item.category] || DEFAULT_GAUGE_VAR;

    var article = document.createElement("article");
    article.className = "gauge-card";
    article.style.setProperty("--card-gauge-color", "var(" + gaugeVar + ")");

    var header = document.createElement("header");
    var iconSpan = document.createElement("span");
    iconSpan.className = "tool-emoji";
    iconSpan.textContent = icon;
    var title = document.createElement("strong");
    title.textContent = item.niche || item.slug;
    header.appendChild(iconSpan);
    header.appendChild(document.createTextNode(" "));
    header.appendChild(title);
    article.appendChild(header);

    var desc = document.createElement("p");
    desc.textContent = item.category || "";
    article.appendChild(desc);

    var link = document.createElement("a");
    link.setAttribute("role", "button");
    link.href = SITE_BASE_PATH + "/" + item.slug + ".html";
    link.textContent = "開く";
    article.appendChild(link);

    return article;
  }

  function render(manifest, mount) {
    var categories = groupByCategory(Array.isArray(manifest) ? manifest : []);
    var orderedNames = CATEGORY_ORDER.filter(function (name) {
      return categories[name] && categories[name].length > 0;
    });
    // CATEGORY_ORDERに無いカテゴリ名が来ても取りこぼさないようにする
    Object.keys(categories).forEach(function (name) {
      if (orderedNames.indexOf(name) === -1) orderedNames.push(name);
    });

    if (orderedNames.length === 0) {
      var empty = document.createElement("p");
      empty.textContent = "まだ公開されているツールがありません。";
      mount.appendChild(empty);
      return;
    }

    // モバイル幅ではこのグリッドをCSSで非表示にし(theme.css参照)、
    // 代わりにこのヒントだけを表示してハンバーガーメニューへ誘導する
    // (デスクトップではグリッドをメイン導線、モバイルではハンバーガーメニューを
    // メイン導線にする方針のため)。
    var mobileHint = document.createElement("p");
    mobileHint.className = "mobile-nav-hint";
    mobileHint.textContent = "☰ 右上のメニューからカテゴリ別にツールを探せます。";
    mount.appendChild(mobileHint);

    orderedNames.forEach(function (name) {
      var section = document.createElement("section");
      section.className = "category-section";

      var heading = document.createElement("h2");
      heading.textContent = (CATEGORY_ICON[name] || DEFAULT_ICON) + " " + name;
      section.appendChild(heading);

      var grid = document.createElement("div");
      grid.className = "grid";
      categories[name]
        .slice()
        .sort(function (a, b) {
          return (a.niche || "").localeCompare(b.niche || "", "ja");
        })
        .forEach(function (item) {
          grid.appendChild(buildCard(item));
        });
      section.appendChild(grid);

      mount.appendChild(section);
    });
  }

  function init() {
    var mount = document.getElementById("tool-cards-mount");
    if (!mount) return;

    fetch(SITE_BASE_PATH + "/assets/manifest.json")
      .then(function (res) {
        if (!res.ok) throw new Error("manifest.json not found (status " + res.status + ")");
        return res.json();
      })
      .then(function (manifest) {
        render(manifest, mount);
      })
      .catch(function (err) {
        console.warn("[cards] カード一覧の読み込みに失敗しました:", err);
        var fallback = document.createElement("p");
        fallback.textContent = "ツール一覧の読み込みに失敗しました。しばらくしてから再度お試しください。";
        mount.appendChild(fallback);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
