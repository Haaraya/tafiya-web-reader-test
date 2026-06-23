/* ============================================================
   Tafiya Reader — Supabase-connected prototype
   Plain JavaScript. No frameworks, no build tools, no libraries.

   Reads:
   ?book=T4-NF-01

   Calls:
   POST /rest/v1/rpc/get_book_package

   Body:
   { "input_book_code": "T4-NF-01" }

   Security:
   Frontend uses ONLY the Supabase publishable key.
   Never use sb_secret_ keys in this file.
   ============================================================ */

const SUPABASE_URL = "https://laihhrkxnxzohaiiisou.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_qW4msFbGQ9QuqIZ6-G8QfA_JY_pvcsY";

const STORAGE_BUCKET = "book-assets";

const DEFAULT_LOGOS = {
  tafiya: "logos/tafiya_logo.png",
  haaraya_literacy: "logos/haaraya_literacy_logo.png",
  haaraya_education: "logos/haaraya_education_logo_transparent.png"
};

function getBookCodeFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("book") || "T4-NF-01";
}

function supabaseIsConfigured() {
  return (
    SUPABASE_URL &&
    SUPABASE_URL.includes("supabase.co") &&
    SUPABASE_PUBLISHABLE_KEY &&
    !SUPABASE_PUBLISHABLE_KEY.includes("YOUR-") &&
    !SUPABASE_PUBLISHABLE_KEY.startsWith("sb_secret_")
  );
}

async function fetchBookPackage(bookCode) {
  if (!supabaseIsConfigured()) {
    throw new Error("Supabase is not configured.");
  }

  const endpoint = `${SUPABASE_URL}/rest/v1/rpc/get_book_package`;

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "apikey": SUPABASE_PUBLISHABLE_KEY,
      "Authorization": `Bearer ${SUPABASE_PUBLISHABLE_KEY}`,
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    body: JSON.stringify({
      input_book_code: bookCode
    })
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`Supabase RPC failed: ${response.status} ${response.statusText}. ${detail}`);
  }

  const data = await response.json();
  return normalizeBookPackage(data);
}

function normalizeBookPackage(data) {
  let pkg = data;

  if (Array.isArray(pkg)) {
    pkg = pkg[0];
  }

  if (pkg && pkg.get_book_package) {
    pkg = pkg.get_book_package;
  }

  if (pkg && pkg.data && pkg.data.book) {
    pkg = pkg.data;
  }

  if (!pkg || typeof pkg !== "object") {
    throw new Error("Supabase returned an empty or invalid book package.");
  }

  pkg.book = pkg.book || {};
  pkg.pages = Array.isArray(pkg.pages) ? pkg.pages : [];
  pkg.skills = pkg.skills || {};
  pkg.assets = pkg.assets || {};
  pkg.assets.logos = {
    ...DEFAULT_LOGOS,
    ...(pkg.assets.logos || {})
  };

  if (!pkg.book.book_code) {
    pkg.book.book_code = getBookCodeFromUrl();
  }

  return pkg;
}

function assetUrl(path) {
  if (!path) return "";

  const raw = String(path).trim();
  if (!raw) return "";

  if (
    raw.startsWith("http://") ||
    raw.startsWith("https://") ||
    raw.startsWith("data:") ||
    raw.startsWith("blob:")
  ) {
    return raw;
  }

  if (raw.startsWith("/storage/v1/object/public/")) {
    return `${SUPABASE_URL}${raw}`;
  }

  let clean = raw.replace(/^\/+/, "");

  if (clean.startsWith(`${STORAGE_BUCKET}/`)) {
    clean = clean.slice(STORAGE_BUCKET.length + 1);
  }

  clean = encodeURI(clean).replace(/#/g, "%23");

  return `${SUPABASE_URL}/storage/v1/object/public/${STORAGE_BUCKET}/${clean}`;
}

let bookPackage = null;
let screens = [];
let currentIndex = 0;

const el = {};

function cacheDom() {
  el.runTitle = document.getElementById("runningTitle");
  el.runLevel = document.getElementById("runningLevel");
  el.brand = document.getElementById("brand");
  el.book = document.getElementById("book");
  el.surface = null;
  el.prev = document.getElementById("prevBtn");
  el.next = document.getElementById("nextBtn");
  el.back = document.getElementById("backBtn");
  el.progTxt = document.getElementById("progressText");
  el.dots = document.getElementById("dots");
}

function makeEl(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function textValue(value) {
  if (value == null) return "";
  if (Array.isArray(value)) return value.filter(Boolean).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value).trim();
}

function bookTypeLabel(value) {
  const s = textValue(value);
  if (!s) return "";

  return s
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\bnon fiction\b/i, "Non-Fiction")
    .replace(/\bnon-fiction\b/i, "Non-Fiction")
    .trim();
}

function levelLabel(lvl) {
  const s = textValue(lvl);
  if (!s) return "";

  if (/^level\b/i.test(s)) {
    return s.replace(/\s+/g, " ");
  }

  return `Level ${s}`;
}

function topMetaLabel(book) {
  const parts = [];

  const lvl = levelLabel(book.level);
  const type = bookTypeLabel(book.book_type);

  if (lvl) parts.push(lvl);
  if (type) parts.push(type);

  return parts.join(" · ");
}

function logoPath(key) {
  const logos = (bookPackage.assets && bookPackage.assets.logos) || {};
  return logos[key] || DEFAULT_LOGOS[key] || "";
}

function logoImg(path, cls) {
  const src = assetUrl(path);
  if (!src) return null;

  const img = new Image();
  img.className = cls;
  img.alt = "";
  img.onerror = () => img.remove();
  img.src = src;

  return img;
}

function imageInto(container, path, phLabel) {
  const src = assetUrl(path);

  if (src) {
    const img = new Image();
    img.alt = "";
    img.onerror = () => placeholderInto(container, phLabel);
    container.appendChild(img);
    img.src = src;
  } else {
    placeholderInto(container, phLabel);
  }
}

function placeholderInto(container, label) {
  container.innerHTML = "";
  container.classList.add("ph");

  const note = document.createElement("div");
  note.className = "ph-note";
  note.textContent = label;

  container.appendChild(note);
}

function skeleton(widthPx) {
  const sk = makeEl("span", "skeleton");
  sk.style.width = (widthPx || 60) + "px";
  return sk;
}

function skeletonLines(n) {
  const frag = document.createDocumentFragment();
  const widths = [100, 100, 62];

  for (let i = 0; i < n; i++) {
    const bar = makeEl("span", "skeleton skeleton-line");
    bar.style.width = (widths[i] != null ? widths[i] : 100) + "%";
    frag.appendChild(bar);
  }

  return frag;
}

function setValue(container, value, fallbackWidth) {
  const v = textValue(value);

  if (v) {
    container.textContent = v;
  } else {
    container.appendChild(skeleton(fallbackWidth || 90));
  }
}

function sectionTitle(text) {
  return makeEl("div", "back-section-title", text);
}

function renderStatus(title, detail) {
  if (!el.book) return;

  el.book.className = "book";
  el.book.innerHTML = "";

  const surface = makeEl("div", "surface story");
  el.book.appendChild(surface);
  el.surface = surface;

  const box = makeEl("div", "story-text");
  box.style.top = "40cqh";
  box.style.fontSize = "4.2cqw";
  box.style.lineHeight = "1.35";
  box.style.fontWeight = "700";
  box.textContent = title;

  const small = makeEl("div", "");
  small.style.marginTop = "2cqh";
  small.style.fontSize = "2.7cqw";
  small.style.fontWeight = "400";
  small.style.lineHeight = "1.35";
  small.textContent = detail || "";

  box.appendChild(small);
  surface.appendChild(box);

  if (el.runTitle) el.runTitle.textContent = title;
  if (el.runLevel) el.runLevel.textContent = "";
  if (el.progTxt) el.progTxt.textContent = "";
  if (el.dots) el.dots.innerHTML = "";
  if (el.prev) el.prev.disabled = true;
  if (el.next) el.next.disabled = true;
}

function renderBookMeta() {
  const b = bookPackage.book || {};

  el.runTitle.textContent = textValue(b.title) || "Book title";
  el.runLevel.textContent = topMetaLabel(b);

  document.title = `${textValue(b.title) || "Tafiya Reader"} — Tafiya Reader`;

  el.brand.innerHTML = "";

  if (textValue(b.strand)) {
    el.brand.appendChild(makeEl("span", "strand", textValue(b.strand)));
  } else {
    const ph = makeEl("span", "strand is-empty");
    ph.appendChild(skeleton(72));
    el.brand.appendChild(ph);
  }
}

function buildScreens() {
  screens = [{ type: "cover" }];

  const pages = (bookPackage.pages || [])
    .slice()
    .sort((a, b) => (a.page_number || 0) - (b.page_number || 0));

  pages.forEach((p) => screens.push({ type: "page", page: p }));

  screens.push({ type: "back" });
}

function renderScreen() {
  const s = screens[currentIndex];

  el.book.className = "book";
  el.book.innerHTML = "";

  el.book.style.animation = "none";
  void el.book.offsetWidth;
  el.book.style.animation = "";

  const surface = makeEl(
    "div",
    "surface " + (s.type === "cover" ? "cover" : s.type === "back" ? "back" : "story")
  );

  el.book.appendChild(surface);
  el.surface = surface;

  if (s.type === "cover") {
    renderCover();
  } else if (s.type === "back") {
    renderBack();
  } else {
    renderPage(s.page);
  }

  el.surface.scrollTop = 0;
  updateNav();
  saveProgress();
}

function renderCover() {
  const b = bookPackage.book || {};

  const top = makeEl("div", "cover-top");

  const taf = logoImg(logoPath("tafiya"), "logo-tafiya");
  if (taf) top.appendChild(taf);

  const lit = logoImg(logoPath("haaraya_literacy"), "logo-literacy");
  if (lit) top.appendChild(lit);

  el.surface.appendChild(top);

  const hero = makeEl("div", "cover-hero");
  imageInto(hero, b.cover_image_path, "cover image");
  el.surface.appendChild(hero);

  const titles = makeEl("div", "cover-titles");

  const titleText = textValue(b.title);
  const h = makeEl("h1", "cover-title", titleText || "Book title");
  if (!titleText) h.classList.add("is-empty");

  titles.appendChild(h);

  titles.appendChild(
    makeEl(
      "div",
      "cover-sub",
      `${textValue(b.tafiya_name) || "Tafiya"}  •  ${levelLabel(b.level) || "—"}`
    )
  );

  el.surface.appendChild(titles);

  const bottom = makeEl("div", "cover-bottom");

  const ed = logoImg(logoPath("haaraya_education"), "logo-haaraya");
  if (ed) bottom.appendChild(ed);

  el.surface.appendChild(bottom);
}

function renderPage(page) {
  const imgWrap = makeEl("div", "story-img");
  imageInto(imgWrap, page.image_path, `illustration · page ${page.page_number}`);
  el.surface.appendChild(imgWrap);

  const txt = makeEl("p", "story-text");
  const pageText = textValue(page.page_text);

  txt.textContent = pageText || "Story text will appear here";

  if (!pageText) {
    txt.classList.add("is-empty");
  }

  el.surface.appendChild(txt);
}

function renderBack() {
  const b = bookPackage.book || {};
  const s = bookPackage.skills || {};
  const type = bookTypeLabel(b.book_type);

  const skillsBlock = makeEl("div", "skills-block");

  const headerText =
    `${textValue(b.book_code) || ""} · ELEMENTS USED IN THIS BOOK` +
    (type ? ` — ${type.toUpperCase()}` : "");

  skillsBlock.appendChild(makeEl("div", "skills-header", headerText));

  const table = makeEl("div", "skills-table");

  const rows = [
    ["Reading Strategy", s.reading_strategy],
    ["Comprehension Skill", s.comprehension_skill],
    ["Phonological Awareness", s.phonological_awareness],
    ["Grammar and Mechanics", s.grammar_mechanics],
    ["Word Work", s.word_work],
    ["Text Structure", s.text_structure]
  ];

  rows.forEach(([label, value], i) => {
    const row = makeEl("div", "skills-row");
    row.appendChild(makeEl("span", "skills-key", label));

    const vv = makeEl("span", "skills-val");
    setValue(vv, value, [120, 96, 108, 88][i % 4]);

    row.appendChild(vv);
    table.appendChild(row);
  });

  skillsBlock.appendChild(table);
  el.surface.appendChild(skillsBlock);

  el.surface.appendChild(sectionTitle("About this book"));

  const bt = makeEl("div", "back-booktitle");
  setValue(bt, b.title, 150);
  el.surface.appendChild(bt);

  const about = makeEl("p", "back-about");
  const aboutText = textValue(s.about_text);

  if (aboutText) {
    about.textContent = aboutText;
  } else {
    about.classList.add("is-empty");
    about.appendChild(skeletonLines(3));
  }

  el.surface.appendChild(about);

  el.surface.appendChild(makeEl("div", "back-divider"));

  el.surface.appendChild(sectionTitle("Reading level"));

  const lvl = makeEl("div", "level-block");

  const levelRows = [
    ["Haaraya Level", levelLabel(b.level)],
    ["Fountas & Pinnell", s.fp_level],
    ["UK Book Band", s.uk_book_band]
  ];

  levelRows.forEach(([label, value], i) => {
    const row = makeEl("div", "level-row");
    row.appendChild(makeEl("span", "level-key", label));

    const vv = makeEl("span", "level-val");
    setValue(vv, value, [90, 50, 64][i % 3]);

    row.appendChild(vv);
    lvl.appendChild(row);
  });

  el.surface.appendChild(lvl);

  const bottom = makeEl("div", "back-bottom");
  bottom.style.marginTop = "auto";

  bottom.appendChild(
    makeEl("div", "back-website", textValue(s.website) || "haarayaeducation.org")
  );

  bottom.appendChild(
    makeEl(
      "p",
      "back-series",
      "The Haaraya Reading Series provides every Nigerian child with books that look like their world, sound like their language, and build the foundation to read for life."
    )
  );

  const footer = makeEl("div", "back-footer");

  const left = makeEl("div", "col-left");
  const ed = logoImg(logoPath("haaraya_education"), "logo-haaraya");
  if (ed) left.appendChild(ed);

  const center = makeEl("div", "col-center");
  center.appendChild(makeEl("div", "back-imprint", "© Author Finisher Nigeria Ltd"));
  center.appendChild(makeEl("div", "back-imprint", "All rights reserved."));
  center.appendChild(makeEl("div", "back-imprint", "RC: [Your Number]"));
  center.appendChild(makeEl("div", "back-imprint", "ISBN: [National Library No]"));

  const right = makeEl("div", "col-right");
  const taf = logoImg(logoPath("tafiya"), "logo-tafiya");
  if (taf) right.appendChild(taf);

  const lit = logoImg(logoPath("haaraya_literacy"), "logo-literacy");
  if (lit) right.appendChild(lit);

  footer.appendChild(left);
  footer.appendChild(center);
  footer.appendChild(right);

  bottom.appendChild(footer);
  el.surface.appendChild(bottom);
}

function updateNav() {
  const total = screens.length;

  el.prev.disabled = currentIndex === 0;
  el.next.disabled = currentIndex === total - 1;

  const s = screens[currentIndex];

  if (s.type === "cover") {
    el.progTxt.textContent = "Front cover";
  } else if (s.type === "back") {
    el.progTxt.textContent = "";
  } else {
    const count = screens.filter((x) => x.type === "page").length;
    el.progTxt.textContent = `Page ${s.page.page_number} of ${count}`;
  }

  el.dots.innerHTML = "";

  if (screens.length > 16) return;

  screens.forEach((sc, i) => {
    const d = makeEl("button", "dot" + (i === currentIndex ? " active" : ""));
    d.type = "button";

    const lbl =
      sc.type === "cover"
        ? "cover"
        : sc.type === "back"
          ? "back cover"
          : `page ${sc.page.page_number}`;

    d.setAttribute("aria-label", `Go to ${lbl}`);
    d.addEventListener("click", () => goTo(i));

    el.dots.appendChild(d);
  });
}

function goTo(i) {
  const c = Math.max(0, Math.min(screens.length - 1, i));

  if (c === currentIndex) return;

  currentIndex = c;
  renderScreen();
}

function nextPage() {
  goTo(currentIndex + 1);
}

function previousPage() {
  goTo(currentIndex - 1);
}

function progressKey() {
  return `tafiya-reader:${(bookPackage.book && bookPackage.book.book_code) || ""}:screen`;
}

function saveProgress() {
  try {
    localStorage.setItem(progressKey(), String(currentIndex));
  } catch (e) {}
}

function restoreProgress() {
  try {
    const v = parseInt(localStorage.getItem(progressKey()), 10);

    if (!isNaN(v) && v >= 0 && v < screens.length) {
      currentIndex = v;
    }
  } catch (e) {}
}

function bindEvents() {
  el.next.addEventListener("click", nextPage);
  el.prev.addEventListener("click", previousPage);

  el.back.addEventListener("click", () => {
    window.location.href = "../library.html";
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight") {
      e.preventDefault();
      nextPage();
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      previousPage();
    }
  });

  let sx = 0;
  let sy = 0;
  let tracking = false;

  el.book.addEventListener(
    "touchstart",
    (e) => {
      const t = e.changedTouches[0];
      sx = t.clientX;
      sy = t.clientY;
      tracking = true;
    },
    { passive: true }
  );

  el.book.addEventListener(
    "touchend",
    (e) => {
      if (!tracking) return;

      tracking = false;

      const t = e.changedTouches[0];
      const dx = t.clientX - sx;
      const dy = t.clientY - sy;

      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        if (dx < 0) nextPage();
        else previousPage();
      }
    },
    { passive: true }
  );
}

function renderBook(pkg) {
  bookPackage = normalizeBookPackage(pkg);
  currentIndex = 0;

  buildScreens();
  renderBookMeta();
  restoreProgress();
  renderScreen();
}

async function boot() {
  cacheDom();
  bindEvents();

  const BOOK_CODE = getBookCodeFromUrl();

  renderStatus("Loading book…", BOOK_CODE);

  try {
    const pkg = await fetchBookPackage(BOOK_CODE);
    renderBook(pkg);
  } catch (err) {
    console.error("[Tafiya Reader]", err);
    renderStatus("Could not load book", err.message);
  }
}

document.addEventListener("DOMContentLoaded", boot);