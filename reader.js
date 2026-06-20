// ======================================================
// HAARAYA / TAFIYA WEB READER
// Supabase-connected version
// ======================================================

// ✅ ADD YOUR SUPABASE BASE URL HERE
// Example: "https://abcxyz.supabase.co"
// ❌ Do NOT include /rest/v1/
const SUPABASE_URL = "https://laihhrkxnxzohaiiisou.supabase.co";

// ✅ ADD YOUR SUPABASE PUBLISHABLE KEY HERE
// It should start with: sb_publishable_
// ❌ Do NOT use sb_secret_
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_qW4msFbGQ9QuqIZ6-G8QfA_JY_pvcsY";

const BOOK_CODE = "T4-NF-01";
const ASSET_BASE_URL = `${SUPABASE_URL}/storage/v1/object/public/book-assets/`;

let book = null;
let screenIndex = 0; // 0 cover, 1..n pages, n+1 back

const stage = document.querySelector("#stage");
const prevBtn = document.querySelector("#prevBtn");
const nextBtn = document.querySelector("#nextBtn");
const progress = document.querySelector("#progress");
const toggle = document.querySelector("#toggleMode");

function assetUrl(path) {
  return `${ASSET_BASE_URL}${path}`;
}

function convertSupabasePackage(pkg) {
  return {
    book_code: pkg.book.book_code,
    title: pkg.book.title,
    strand: pkg.book.strand,
    level: pkg.book.level,
    tafiya_name: pkg.book.tafiya_name,
    book_type: pkg.book.book_type,
    theme: pkg.book.theme,

    cover: {
      image: assetUrl(pkg.book.cover_image_path)
    },

    pages: pkg.pages.map(page => ({
      page: page.page_number,
      text: page.page_text,
      image: assetUrl(page.image_path),
      layout: page.layout,
      text_band: page.text_band || "medium",
      word_count: page.word_count
    })),

    back_cover: {
      reading_strategy: pkg.skills.reading_strategy,
      comprehension_skill: pkg.skills.comprehension_skill,
      phonological_awareness: pkg.skills.phonological_awareness,
      grammar_mechanics: pkg.skills.grammar_mechanics,
      word_work: pkg.skills.word_work,
      text_structure: pkg.skills.text_structure,
      about: pkg.skills.about_text,
      fp_level: pkg.skills.fp_level,
      uk_book_band: pkg.skills.uk_book_band,
      website: pkg.skills.website
    },

    assets: {
      logos: {
        haaraya_education: assetUrl(pkg.assets.logos.haaraya_education),
        haaraya_literacy: assetUrl(pkg.assets.logos.haaraya_literacy),
        tafiya: assetUrl(pkg.assets.logos.tafiya)
      }
    }
  };
}

function img(src, className, alt = "") {
  const el = document.createElement("img");
  el.src = src;
  el.alt = alt;
  if (className) el.className = className;
  return el;
}

function createCover() {
  const s = document.createElement("section");
  s.className = "book-screen cover";
  const logos = book.assets.logos;

  const brandTop = document.createElement("div");
  brandTop.className = "brand-top";
  brandTop.appendChild(img(logos.tafiya, "brand-tafiya", "Tafiya"));
  brandTop.appendChild(img(logos.haaraya_literacy, "brand-literacy", "Haaraya Literacy"));
  s.appendChild(brandTop);

  const art = document.createElement("div");
  art.className = "cover-art";
  art.appendChild(img(book.cover.image, "", book.title));
  s.appendChild(art);

  const titleZone = document.createElement("div");
  titleZone.className = "cover-title-zone";

  const title = document.createElement("h1");
  title.className = "cover-title";
  title.textContent = book.title;

  titleZone.appendChild(title);
  s.appendChild(titleZone);

  const level = document.createElement("div");
  level.className = "cover-level";
  level.textContent = `${book.tafiya_name || "Tafiya"}  •  ${book.level}`;
  s.appendChild(level);

  s.appendChild(img(logos.haaraya_education, "brand-haaraya", "Haaraya Education"));

  return s;
}

function createReaderPage(page) {
  const s = document.createElement("section");
  s.className = `book-screen reader-page ${page.text_band}`;

  const art = document.createElement("div");
  art.className = "page-art";
  art.appendChild(img(page.image, "", `Page ${page.page}`));
  s.appendChild(art);

  const text = document.createElement("div");
  text.className = "page-text";
  text.textContent = page.text;
  s.appendChild(text);

  const footer = document.createElement("div");
  footer.className = "page-footer";
  footer.appendChild(img(book.assets.logos.haaraya_education, "", "Haaraya Education"));

  const num = document.createElement("span");
  num.className = "page-number";
  num.textContent = page.page;

  footer.appendChild(num);
  s.appendChild(footer);

  return s;
}

function createBackCover() {
  const s = document.createElement("section");
  s.className = "book-screen back-cover";
  const b = book.back_cover;

  const table = document.createElement("table");
  table.className = "skills-table";

  const cap = document.createElement("caption");
  cap.textContent = `${book.book_code} • SKILLS COVERED IN THIS BOOK`;
  table.appendChild(cap);

  const rows = [
    ["Reading Strategy", b.reading_strategy],
    ["Comprehension Skill", b.comprehension_skill],
    ["Phonological Awareness", b.phonological_awareness],
    ["Grammar and Mechanics", b.grammar_mechanics],
    ["Word Work", b.word_work],
    ["Text Structure", b.text_structure]
  ];

  const tbody = document.createElement("tbody");

  rows.forEach(([k, v]) => {
    const tr = document.createElement("tr");

    const td1 = document.createElement("td");
    td1.textContent = k;

    const td2 = document.createElement("td");
    td2.textContent = v || "";

    tr.append(td1, td2);
    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  s.appendChild(table);

  const about = document.createElement("div");
  about.className = "back-section";
  about.innerHTML = `
    <h2>ABOUT THIS BOOK</h2>
    <div class="back-title">${book.title}</div>
    <div class="back-about">${b.about || ""}</div>
    <div class="rule"></div>
    <h2>READING LEVEL</h2>
  `;
  s.appendChild(about);

  const level = document.createElement("table");
  level.className = "level-table";
  level.innerHTML = `
    <tr><td>Haaraya Level</td><td>${book.level} — ${book.tafiya_name}</td></tr>
    <tr><td>Fountas & Pinnell</td><td>${b.fp_level || ""}</td></tr>
    <tr><td>UK Book Band</td><td>${b.uk_book_band || ""}</td></tr>
  `;
  s.appendChild(level);

  const web = document.createElement("div");
  web.className = "website";
  web.textContent = b.website || "";
  s.appendChild(web);

  const series = document.createElement("div");
  series.className = "series-statement";
  series.textContent = "The Haaraya Reading Series provides every Nigerian child with books that look like their world, sound like their language, and build the foundation to read for life.";
  s.appendChild(series);

  const footer = document.createElement("div");
  footer.className = "back-footer";
  footer.innerHTML = `
    <img class="hf" src="${book.assets.logos.haaraya_education}" alt="Haaraya Education">
    <div class="copy">© Author Finisher Nigeria Ltd<br>All rights reserved.<br>RC: [Your Number]<br>ISBN: [National Library No]</div>
    <div class="tf">
      <img class="brand-tafiya" src="${book.assets.logos.tafiya}" alt="Tafiya">
      <img class="brand-literacy" src="${book.assets.logos.haaraya_literacy}" alt="Haaraya Literacy">
    </div>
  `;
  s.appendChild(footer);

  return s;
}

function render() {
  stage.innerHTML = "";

  if (!book) {
    stage.innerHTML = "<pre>Book not loaded yet.</pre>";
    return;
  }

  const last = book.pages.length + 1;

  if (screenIndex === 0) {
    stage.appendChild(createCover());
    progress.textContent = "Cover";
  } else if (screenIndex === last) {
    stage.appendChild(createBackCover());
    progress.textContent = "Back cover";
  } else {
    stage.appendChild(createReaderPage(book.pages[screenIndex - 1]));
    progress.textContent = `Page ${screenIndex} of ${book.pages.length}`;
  }

  prevBtn.disabled = screenIndex === 0;
  nextBtn.disabled = screenIndex === last;
}

prevBtn.addEventListener("click", () => {
  screenIndex = Math.max(0, screenIndex - 1);
  render();
});

nextBtn.addEventListener("click", () => {
  screenIndex = Math.min(book.pages.length + 1, screenIndex + 1);
  render();
});

toggle.addEventListener("click", () => {
  document.body.classList.toggle("wide");
  toggle.textContent = document.body.classList.contains("wide")
    ? "Phone preview"
    : "Wide preview";
});

document.addEventListener("keydown", (e) => {
  if (e.key === "ArrowRight") nextBtn.click();
  if (e.key === "ArrowLeft") prevBtn.click();
});

fetch(`${SUPABASE_URL}/rest/v1/rpc/get_book_package`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "apikey": SUPABASE_PUBLISHABLE_KEY,
    "Authorization": `Bearer ${SUPABASE_PUBLISHABLE_KEY}`
  },
  body: JSON.stringify({
    input_book_code: BOOK_CODE
  })
})
  .then(r => {
    if (!r.ok) {
      throw new Error(`Supabase error ${r.status}: ${r.statusText}`);
    }
    return r.json();
  })
  .then(data => {
    console.log("SUPABASE DATA:", data);

    if (!data || !data.book || !data.pages || !data.skills) {
      throw new Error("Supabase returned data, but the book package is incomplete.");
    }

    book = convertSupabasePackage(data);
    console.log("CONVERTED BOOK:", book);

    render();
  })
  .catch(err => {
    stage.innerHTML = `<pre>${err.message}</pre>`;
    console.error(err);
  });