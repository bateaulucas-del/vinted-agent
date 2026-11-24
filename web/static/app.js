const $ = (id) => document.getElementById(id);
let mode = "url";

document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => {
  mode = t.dataset.mode;
  document.querySelectorAll(".tab").forEach((x) => {
    x.classList.toggle("active", x === t);
    x.setAttribute("aria-selected", x === t);
  });
  document.querySelector(".tabs").classList.toggle("photo", mode === "photo");
  $("pane-url").classList.toggle("hidden", mode !== "url");
  $("pane-photo").classList.toggle("hidden", mode !== "photo");
}));

$("photo").addEventListener("change", () => {
  const f = $("photo").files[0];
  if (!f) return;
  $("preview").src = URL.createObjectURL(f);
  $("preview").classList.remove("hidden");
  $("drop-text").textContent = "Changer de photo";
});

function showError(msg) {
  const e = $("error");
  e.textContent = msg;
  e.classList.add("hidden"); void e.offsetWidth;  // relance l'animation
  e.classList.remove("hidden");
}

$("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("error").classList.add("hidden");
  const fd = new FormData();
  if (mode === "url") {
    const u = $("url").value.trim();
    if (!u) return showError("Colle le lien d'une page produit.");
    fd.append("url", u);
  } else {
    const f = $("photo").files[0];
    if (!f) return showError("Choisis une photo.");
    fd.append("photo", f);
  }
  for (const k of ["size", "max_price", "country"]) {
    const v = $(k).value.trim();
    if (v) fd.append(k, v);
  }
  for (const el of document.querySelectorAll("#more input:checked")) fd.append(el.name, el.value);
  saveChoices();
  const btn = $("go");
  btn.disabled = true;
  btn.innerHTML = '<span class="spin">🔍</span>On cherche…';
  try {
    const r = await fetch("/api/identify", { method: "POST", body: fd });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || "Une erreur est survenue.");
    render(data);
    addHistory(data);
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Chercher";
  }
});

function render({ item, links, sites, sites_query, similar }) {
  const title = [item.brand, item.model].filter(Boolean).join(" · ") || item.category || "Article";
  $("item-title").textContent = title;
  const facts = $("item-facts");
  facts.replaceChildren();
  const add = (label, v) => { if (v) { const li = document.createElement("li"); li.textContent = `${label} : ${v}`; facts.append(li); } };
  add("Type", item.category);
  add("Couleur", item.color);
  add("Taille", item.size);
  if (item.retail_price) add("Prix neuf", `${item.retail_price.toFixed(2)} €`);

  const img = $("item-img");
  const src = mode === "photo" ? $("preview").src : item.image_url;
  if (src) { img.src = src; img.classList.remove("hidden"); } else img.classList.add("hidden");

  $("sites-query").textContent = `Annonces d'occasion pour « ${sites_query} »`;
  renderSites($("sites"), sites);

  $("similar").classList.toggle("hidden", !similar);
  if (similar) {
    $("similar-query").textContent = `Toutes marques : « ${similar.query} »`;
    renderSites($("similar-sites"), similar.sites);
    const bbox = $("similar-brands");
    bbox.replaceChildren();
    if (similar.brands.length) {
      const p = document.createElement("p"); p.className = "q"; p.textContent = "Marques du même style :";
      bbox.append(p);
    }
    for (const b of similar.brands) {
      const row = document.createElement("div"); row.className = "link";
      const txt = document.createElement("div");
      const t = document.createElement("strong"); t.textContent = b.brand;
      const q = document.createElement("div"); q.className = "q"; q.textContent = `« ${b.query} »`;
      txt.append(t, q);
      const btns = document.createElement("div"); btns.className = "btns";
      if (b.vinted_url) btns.append(Object.assign(document.createElement("a"), { href: b.vinted_url, target: "_blank", rel: "noopener", className: "main", textContent: "Vinted" }));
      if (b.ebay_url) btns.append(Object.assign(document.createElement("a"), { href: b.ebay_url, target: "_blank", rel: "noopener", className: "alt", textContent: "eBay" }));
      if (!btns.children.length) continue;
      row.append(txt, btns);
      bbox.append(row);
    }
  }

  $("links-title").classList.toggle("hidden", !links.length);
  const box = $("links");
  box.replaceChildren();
  for (const l of links) {
    const row = document.createElement("div");
    row.className = "link";
    const txt = document.createElement("div");
    const b = document.createElement("strong"); b.textContent = l.label;
    const q = document.createElement("div"); q.className = "q"; q.textContent = `« ${l.query} »`;
    txt.append(b, q);
    const btns = document.createElement("div"); btns.className = "btns";
    const a1 = Object.assign(document.createElement("a"), { href: l.url, target: "_blank", rel: "noopener", className: "main", textContent: "Voir" });
    const a2 = Object.assign(document.createElement("a"), { href: l.newest_url, target: "_blank", rel: "noopener", className: "alt", textContent: "Plus récents" });
    btns.append(a1, a2);
    row.append(txt, btns);
    box.append(row);
  }
  if (item.size) {
    const tip = document.createElement("p"); tip.className = "q";
    tip.textContent = `Astuce : sur Vinted, choisis la taille ${item.size} dans le filtre « Taille ».`;
    box.append(tip);
  }
  document.querySelectorAll("#result .link").forEach((el, i) => el.style.setProperty("--i", i));
  const res = $("result");
  res.classList.remove("hidden", "reveal"); void res.offsetWidth;
  res.classList.add("reveal");
  $("result").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderSites(box, sites) {
  box.replaceChildren();
  for (const s of sites || []) {
    const row = document.createElement("div");
    row.className = "link site";
    const txt = document.createElement("div");
    const b = document.createElement("strong"); b.textContent = s.site;
    txt.append(b);
    const btns = document.createElement("div"); btns.className = "btns";
    btns.append(Object.assign(document.createElement("a"), { href: s.url, target: "_blank", rel: "noopener", className: "main", textContent: "Voir" }));
    row.append(txt, btns);
    box.append(row);
  }
}

$("share").addEventListener("click", async () => {
  const data = { title: "Trouve-le sur Vinted", url: location.origin };
  if (navigator.share) { try { await navigator.share(data); } catch {} }
  else { await navigator.clipboard.writeText(location.origin); $("share").textContent = "Lien copié !"; }
});


// ---------- Réglages (gardés sur l'appareil) ----------
const store = {
  get: (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set: (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
};
const prefs = store.get("prefs", { dark: false, motion: true, remember: true });

function applyPrefs() {
  document.documentElement.classList.toggle("dark", prefs.dark);
  document.documentElement.classList.toggle("no-motion", !prefs.motion);
  $("opt-dark").checked = prefs.dark;
  $("opt-motion").checked = prefs.motion;
  $("opt-remember").checked = prefs.remember;
}
for (const [id, key] of [["opt-dark", "dark"], ["opt-motion", "motion"], ["opt-remember", "remember"]]) {
  $(id).addEventListener("change", () => {
    prefs[key] = $(id).checked;
    store.set("prefs", prefs);
    if (key === "remember" && !prefs.remember) localStorage.removeItem("choices");
    applyPrefs();
  });
}

function saveChoices() {
  if (!prefs.remember) return;
  const choices = { size: $("size").value, max_price: $("max_price").value, country: $("country").value,
    more: [...document.querySelectorAll("#more input")].map((el) => [el.name, el.value, el.checked]) };
  store.set("choices", choices);
}
function loadChoices() {
  const c = prefs.remember && store.get("choices", null);
  if (!c) return;
  for (const k of ["size", "max_price", "country"]) if (c[k] != null) $(k).value = c[k];
  for (const [name, value, checked] of c.more || []) {
    const el = document.querySelector(`#more input[name="${CSS.escape(name)}"][value="${CSS.escape(value)}"]`);
    if (el) el.checked = checked;
  }
}

function addHistory({ item }) {
  const title = [item.brand, item.model].filter(Boolean).join(" · ") || item.category || "Article";
  const entry = { title, url: mode === "url" ? $("url").value.trim() : null, when: Date.now() };
  const h = store.get("history", []).filter((e) => !(e.url && e.url === entry.url));
  store.set("history", [entry, ...h].slice(0, 100));
  renderHistory();
}
let historyShown = 5;
function renderHistory() {
  const ul = $("history");
  ul.replaceChildren();
  const all = store.get("history", []);
  const h = all.slice(0, historyShown);
  $("history-more").classList.toggle("hidden", all.length <= historyShown);
  $("history-more").textContent = `Voir plus (${all.length - historyShown} de plus)`;
  if (!h.length) { const li = document.createElement("li"); li.className = "q"; li.textContent = "Aucune recherche pour l'instant."; ul.append(li); }
  for (const e of h) {
    const li = document.createElement("li");
    const b = document.createElement("button"); b.type = "button"; b.className = "hist";
    const t = document.createElement("span"); t.textContent = e.title;
    const d = document.createElement("small"); d.textContent = (e.url ? "🔗 " : "📷 ") + new Date(e.when).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
    b.append(t, d);
    b.disabled = !e.url;
    b.addEventListener("click", () => {
      document.querySelector('.tab[data-mode="url"]').click();
      $("url").value = e.url;
      toggleSettings(false);
      $("form").requestSubmit();
    });
    li.append(b); ul.append(li);
  }
}
$("history-more").addEventListener("click", () => { historyShown += 10; renderHistory(); });
$("history-clear").addEventListener("click", () => { store.set("history", []); renderHistory(); });

function toggleSettings(open) {
  $("settings").classList.toggle("hidden", !open);
  $("gear").setAttribute("aria-expanded", open);
  if (open) { historyShown = 5; renderHistory(); }
}
$("gear").addEventListener("click", () => toggleSettings($("settings").classList.contains("hidden")));
$("settings-close").addEventListener("click", () => toggleSettings(false));
document.addEventListener("keydown", (e) => { if (e.key === "Escape") toggleSettings(false); });

// ---------- Filtres : compteur et remise à zéro ----------
const DEFAULTS = { sort: "relevance", gender: "", sites: true, conditions: false };
function isDefault(el) {
  if (el.name === "sites") return el.checked;
  if (el.type === "radio") return el.checked === (el.value === DEFAULTS[el.name]);
  return !el.checked;
}
function updateCount() {
  let n = [...document.querySelectorAll("#more input")].filter((el) => el.checked && !isDefault(el) || el.name === "sites" && !el.checked).length;
  if ($("size").value.trim()) n++;
  if ($("max_price").value.trim()) n++;
  $("more-count").textContent = n;
  $("more-count").classList.toggle("hidden", !n);
  $("reset").disabled = !n;
}
$("reset").addEventListener("click", () => {
  for (const el of document.querySelectorAll("#more input")) {
    el.checked = el.name === "sites" ? true : el.type === "radio" ? el.value === DEFAULTS[el.name] : false;
  }
  $("size").value = ""; $("max_price").value = "";
  saveChoices(); updateCount();
  $("reset").textContent = "Filtres enlevés ✓";
  setTimeout(() => { $("reset").textContent = "Enlever tous les filtres"; }, 1500);
});
document.querySelectorAll("#more input, #size, #max_price").forEach((el) => el.addEventListener("input", updateCount));
document.querySelectorAll("#more input").forEach((el) => el.addEventListener("change", updateCount));

applyPrefs();
loadChoices();
updateCount();
