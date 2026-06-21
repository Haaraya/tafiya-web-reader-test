/* ============================================================
   Tafiya Reader — Supabase-ready prototype logic
   Plain JavaScript. No frameworks, no build tools, no libraries.

   The reader renders from ONE object: bookPackage.
   Its shape matches the Supabase RPC get_book_package(input_book_code)
   response exactly.

   Data flow:
   1. Read ?book=T4-NF-01 from the URL.
   2. Ask Supabase RPC get_book_package for that book.
   3. Render the returned bookPackage.
   4. If Supabase fails, fall back to local mock data.
   ============================================================ */

/* ------------------------------------------------------------------ */
/*  Supabase config                                                   */
/* ------------------------------------------------------------------ */

const SUPABASE_URL = "https://laihhrkxnxzohaiiisou.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_qW4msFbGQ9QuqIZ6-G8QfA_JY_pvcsY";
const SUPABASE_BUCKET = "book-assets";

/* ------------------------------------------------------------------ */
/*  URL → book_code                                                   */
/* ------------------------------------------------------------------ */

function getBookCodeFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("book") || "T4-NF-01";
}

/* ------------------------------------------------------------------ */
/*  Asset URL helper                                                  */
/* ------------------------------------------------------------------ */

function assetUrl(path) {
  if (!path) return "";

  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  if (
    !SUPABASE_URL ||
    SUPABASE_URL === "PASTE_YOUR_SUPABASE_PROJECT_URL_HERE"
  ) {
    return path;
  }

  return `${SUPABASE_URL}/storage/v1/object/public/${SUPABASE_BUCKET}/${path}`;
}

/* ------------------------------------------------------------------ */
/*  Supabase fetch                                                    */
/* ------------------------------------------------------------------ */

async function fetchBookPackage(bookCode) {
  if (
    !SUPABASE_URL ||
    !SUPABASE_PUBLISHABLE_KEY ||
    SUPABASE_URL === "PASTE_YOUR_SUPABASE_PROJECT_URL_HERE" ||
    SUPABASE_PUBLISHABLE_KEY === "PASTE_YOUR_SUPABASE_PUBLISHABLE_KEY_HERE"
  ) {
    throw new Error("Supabase URL/key placeholders have not been replaced.");
  }

  const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/get_book_package`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_PUBLISHABLE_KEY,
      Authorization: `Bearer ${SUPABASE_PUBLISHABLE_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      input_book_code: bookCode
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Supabase request failed: ${response.status} ${response.statusText}. ${errorText}`
    );
  }

  const data = await response.json();

  if (!data || !data.book || !Array.isArray(data.pages) || !data.skills) {
    console.log("[Tafiya Reader] Supabase returned:", data);
    throw new Error("Supabase returned an incomplete book package.");
  }

  return data;
}

/* ------------------------------------------------------------------ */
/*  Mock data fallback — exact get_book_package shape                  */
/* ------------------------------------------------------------------ */

function getMockBookPackage(bookCode) {
  const isKeke = bookCode === "T4-NF-02";

  const bookPackage = {
    book: {
      id: isKeke ? "mock-id-keke" : "mock-id-jollof",
      book_code: isKeke ? "T4-NF-02" : "T4-NF-01",
      title: isKeke ? "The Keke Napep" : "How We Cook Jollof Rice",
      strand: "Non-Fiction",
      level: 4,
      tafiya_name: "Tafiya",
      book_type: "Non-Fiction",
      theme: "Everyday Life",
      topic: isKeke ? "Transport" : "Food",
      cover_image_path: isKeke
        ? "sample-images/T4-NF-02_FC.png"
        : "sample-images/T4-NF-01_FC.png",
      status: "approved",
      created_at: "",
      updated_at: ""
    },

    pages: isKeke
      ? [
          {
            id: "mock-keke-page-1",
            book_id: "mock-id-keke",
            page_number: 1,
            page_text: "A keke can go on the road.",
            image_path: "sample-images/T4-NF-02_P1.png",
            layout: "image_top_text_bottom",
            text_band: "bottom",
            word_count: 7,
            created_at: "",
            updated_at: ""
          },
          {
            id: "mock-keke-page-2",
            book_id: "mock-id-keke",
            page_number: 2,
            page_text: "People ride in a keke.",
            image_path: "sample-images/T4-NF-02_P2.png",
            layout: "image_top_text_bottom",
            text_band: "bottom",
            word_count: 6,
            created_at: "",
            updated_at: ""
          }
        ]
      : [
          {
            id: "mock-jollof-page-1",
            book_id: "mock-id-jollof",
            page_number: 1,
            page_text: "We wash the rice.",
            image_path: "sample-images/T4-NF-01_P1.png",
            layout: "image_top_text_bottom",
            text_band: "bottom",
            word_count: 4,
            created_at: "",
            updated_at: ""
          },
          {
            id: "mock-jollof-page-2",
            book_id: "mock-id-jollof",
            page_number: 2,
            page_text: "We cook the stew.",
            image_path: "sample-images/T4-NF-01_P2.png",
            layout: "image_top_text_bottom",
            text_band: "bottom",
            word_count: 4,
            created_at: "",
            updated_at: ""
          }
        ],

    skills: {
      id: isKeke ? "mock-keke-skills-id" : "mock-jollof-skills-id",
      book_id: isKeke ? "mock-id-keke" : "mock-id-jollof",
      reading_strategy: "Ask and Answer Questions",
      comprehension_skill: "Sequence Events",
      phonological_awareness: "Syllables",
      grammar_mechanics: "Simple Sentences",
      word_work: "Content Vocabulary",
      text_structure: "Sequence",
      topic: isKeke ? "Transport" : "Food",
      key_vocabulary: isKeke
        ? "keke, road, driver, ride"
        : "rice, stew, pot, pepper",
      total_word_count: isKeke ? 96 : 120,
      about_text: isKeke
        ? "This book introduces children to the keke napep as everyday transport."
        : "This book shows how people cook jollof rice step by step.",
      fp_level: "D",
      uk_book_band: "Red",
      website: "haarayaeducation.org",
      created_at: "",
      updated_at: ""
    },

    assets: {
      logos: {
        haaraya_education: "sample-logos/haaraya_education_logo_transparent.png",
        haaraya_literacy: "sample-logos/haaraya_literacy_logo.png",
        tafiya: "sample-logos/tafiya_logo.png"
      }
    }
  };

  return bookPackage;
}

/* ------------------------------------------------------------------ */
/*  Reader state + DOM                                                */
/* ------------------------------------------------------------------ */

let bookPackage = null;
let screens = []; // ordered: cover → pages → back
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

/* ------------------------------------------------------------------ */
/*  Small DOM helpers                                                 */
/* ------------------------------------------------------------------ */

function logoPath(key) {
  const L = (bookPackage.assets && bookPackage.assets.logos) || {};
  return L[key] || "";
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

function makeEl(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

/* ------------------------------------------------------------------ */
/*  Render: book metadata                                             */
/* ------------------------------------------------------------------ */

function renderBookMeta() {
  const b = bookPackage.book || {};

  el.runTitle.textContent =
    b.title && b.title.trim() ? b.title : "Book title";

  el.runLevel.textContent =
    (b.level != null ? `Level ${b.level}` : "") +
    (b.book_type ? `  ·  ${b.book_type}` : "");

  document.title = (b.title || "Tafiya Reader") + " — Tafiya Reader";

  el.brand.innerHTML = "";

  if (b.strand && b.strand.trim()) {
    el.brand.appendChild(makeEl("span", "strand", b.strand));
  } else {
    const ph = makeEl("span", "strand is-empty");
    ph.appendChild(skeleton(72));
    el.brand.appendChild(ph);
  }
}

/* ------------------------------------------------------------------ */
/*  Screen list: cover → pages sorted by page_number → back           */
/* ------------------------------------------------------------------ */

function buildScreens() {
  screens = [{ type: "cover" }];

  const pages = (bookPackage.pages || [])
    .slice()
    .sort((a, b) => (a.page_number || 0) - (b.page_number || 0));

  pages.forEach((p) => screens.push({ type: "page", page: p }));

  screens.push({ type: "back" });
}

/* ------------------------------------------------------------------ */
/*  Render current screen                                             */
/* ------------------------------------------------------------------ */

function renderScreen() {
  const s = screens[currentIndex];

  el.book.className = "book";
  el.book.innerHTML = "";

  el.book.style.animation = "none";
  void el.book.offsetWidth;
  el.book.style.animation = "";

  const surface = makeEl(
    "div",
    "surface " +
      (s.type === "cover" ? "cover" : s.type === "back" ? "back" : "story")
  );

  el.book.appendChild(surface);
  el.surface = surface;

  if (s.type === "cover") renderCover();
  else if (s.type === "back") renderBack();
  else renderPage(s.page);

  el.surface.scrollTop = 0;
  updateNav();
  saveProgress();
}

/* ------------------------------------------------------------------ */
/*  Cover                                                             */
/* ------------------------------------------------------------------ */

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

  const h = makeEl(
    "h1",
    "cover-title",
    b.title && b.title.trim() ? b.title : "Book title"
  );

  if (!(b.title && b.title.trim())) h.classList.add("is-empty");

  titles.appendChild(h);

  titles.appendChild(
    makeEl(
      "div",
      "cover-sub",
      `${b.tafiya_name || "Tafiya"}  •  Level ${
        b.level != null ? b.level : "—"
      }`
    )
  );

  el.surface.appendChild(titles);

  const bottom = makeEl("div", "cover-bottom");

  const ed = logoImg(logoPath("haaraya_education"), "logo-haaraya");
  if (ed) bottom.appendChild(ed);

  el.surface.appendChild(bottom);
}

/* ------------------------------------------------------------------ */
/*  Story page                                                        */
/* ------------------------------------------------------------------ */

function renderPage(page) {
  const imgWrap = makeEl("div", "story-img");
  imageInto(
    imgWrap,
    page.image_path,
    `illustration · page ${page.page_number}`
  );

  el.surface.appendChild(imgWrap);

  const txt = makeEl("p", "story-text");

  const has = page.page_text && page.page_text.trim();
  txt.textContent = has ? page.page_text : "Story text will appear here";

  if (!has) txt.classList.add("is-empty");

  el.surface.appendChild(txt);
}

/* ------------------------------------------------------------------ */
/*  Back cover                                                        */
/* ------------------------------------------------------------------ */

function renderBack() {
  const b = bookPackage.book || {};
  const sk = bookPackage.skills || {};

  const skillsBlock = makeEl("div", "skills-block");

  skillsBlock.appendChild(
    makeEl(
      "div",
      "skills-header",
      `${b.book_code || ""} · SKILLS COVERED IN THIS BOOK`
    )
  );

  const table = makeEl("div", "skills-table");

  const skillRows = [
    ["Reading Strategy", sk.reading_strategy],
    ["Comprehension Skill", sk.comprehension_skill],
    ["Phonological Awareness", sk.phonological_awareness],
    ["Grammar and Mechanics", sk.grammar_mechanics],
    ["Word Work", sk.word_work],
    ["Text Structure", sk.text_structure]
  ];

  skillRows.forEach(([label, value], i) => {
    const row = makeEl("div", "skills-row");
    row.appendChild(makeEl("span", "skills-key", label));

    const vv = makeEl("span", "skills-val");

    if (value && String(value).trim()) {
      vv.textContent = value;
    } else {
      vv.appendChild(skeleton([120, 96, 108, 88][i % 4]));
    }

    row.appendChild(vv);
    table.appendChild(row);
  });

  skillsBlock.appendChild(table);
  el.surface.appendChild(skillsBlock);

  el.surface.appendChild(sectionTitle("About this book"));

  const bt = makeEl(
    "div",
    "back-booktitle",
    b.title && b.title.trim() ? b.title : ""
  );

  if (!(b.title && b.title.trim())) {
    bt.classList.add("is-empty");
    bt.appendChild(skeleton(150));
  }

  el.surface.appendChild(bt);

  const about = makeEl("p", "back-about");

  if (sk.about_text && String(sk.about_text).trim()) {
    about.textContent = sk.about_text;
  } else {
    about.classList.add("is-empty");
    about.appendChild(skeletonLines(3));
  }

  el.surface.appendChild(about);

  el.surface.appendChild(makeEl("div", "back-divider"));

  el.surface.appendChild(sectionTitle("Reading level"));

  const lvl = makeEl("div", "level-block");

  const levelRows = [
    ["Haaraya Level", b.level != null ? `${b.tafiya_name || "Tafiya"} ${b.level}` : ""],
    ["Fountas & Pinnell", sk.fp_level],
    ["UK Book Band", sk.uk_book_band]
  ];

  levelRows.forEach(([label, value], i) => {
    const row = makeEl("div", "level-row");
    row.appendChild(makeEl("span", "level-key", label));

    const vv = makeEl("span", "level-val");

    if (value && String(value).trim()) {
      vv.textContent = value;
    } else {
      vv.appendChild(skeleton([90, 50, 64][i % 3]));
    }

    row.appendChild(vv);
    lvl.appendChild(row);
  });

  el.surface.appendChild(lvl);

  el.surface.appendChild(
    makeEl("div", "back-website", sk.website || "haarayaeducation.org")
  );

  el.surface.appendChild(
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

  el.surface.appendChild(footer);
}

/* ------------------------------------------------------------------ */
/*  Back cover helpers                                                */
/* ------------------------------------------------------------------ */

function sectionTitle(text) {
  return makeEl("div", "back-section-title", text);
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

/* ------------------------------------------------------------------ */
/*  Navigation                                                        */
/* ------------------------------------------------------------------ */

function updateNav() {
  const total = screens.length;

  el.prev.disabled = currentIndex === 0;
  el.next.disabled = currentIndex === total - 1;

  const s = screens[currentIndex];

  if (s.type === "cover") {
    el.progTxt.textContent = "Front cover";
  } else if (s.type === "back") {
    el.progTxt.textContent = "About this book";
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

/* ------------------------------------------------------------------ */
/*  Progress persistence                                              */
/* ------------------------------------------------------------------ */

function progressKey() {
  return `tafiya-reader:${
    (bookPackage.book && bookPackage.book.book_code) || ""
  }:screen`;
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

/* ------------------------------------------------------------------ */
/*  Input                                                             */
/* ------------------------------------------------------------------ */

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

/* ------------------------------------------------------------------ */
/*  Render book                                                       */
/* ------------------------------------------------------------------ */

function renderBook(pkg) {
  bookPackage = pkg;
  currentIndex = 0;

  buildScreens();
  renderBookMeta();
  restoreProgress();
  renderScreen();
}

/* ------------------------------------------------------------------ */
/*  Boot                                                              */
/* ------------------------------------------------------------------ */

document.addEventListener("DOMContentLoaded", async () => {
  cacheDom();
  bindEvents();

  const BOOK_CODE = getBookCodeFromUrl();

  try {
    const realPackage = await fetchBookPackage(BOOK_CODE);
    renderBook(realPackage);
    console.log(`[Tafiya Reader] Loaded ${BOOK_CODE} from Supabase.`);
  } catch (error) {
    console.error("[Tafiya Reader] Supabase load failed:", error);
    console.warn("[Tafiya Reader] Falling back to mock data.");
    renderBook(getMockBookPackage(BOOK_CODE));
  }
});