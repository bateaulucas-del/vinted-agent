const $ = (id) => document.getElementById(id);
let mode = "url";

document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => {
  mode = t.dataset.mode;
  document.querySelectorAll(".tab").forEach((x) => {
    x.classList.toggle("active", x === t);
    x.setAttribute("aria-selected", x === t);
  });
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
  $("error").textContent = msg;
  $("error").classList.remove("hidden");
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
  const btn = $("go");
  btn.disabled = true;
  btn.textContent = "Analyse en cours…";
  try {
    const r = await fetch("/api/identify", { method: "POST", body: fd });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || "Une erreur est survenue.");
    render(data);
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
      btns.append(
        Object.assign(document.createElement("a"), { href: b.vinted_url, target: "_blank", rel: "noopener", className: "main", textContent: "Vinted" }),
        Object.assign(document.createElement("a"), { href: b.ebay_url, target: "_blank", rel: "noopener", className: "alt", textContent: "eBay" }),
      );
      row.append(txt, btns);
      bbox.append(row);
    }
  }

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
  $("result").classList.remove("hidden");
  $("result").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderSites(box, sites) {
  box.replaceChildren();
  for (const s of sites || []) {
    const row = document.createElement("div");
    row.className = "link site";
    const txt = document.createElement("div");
    const b = document.createElement("strong"); b.textContent = s.site;
    const c = document.createElement("div");
    if (s.count === null || s.count === undefined) {
      c.className = "q"; c.textContent = "Nombre non disponible";
    } else {
      c.className = "count";
      c.textContent = s.count === 0 ? "Aucune annonce" : `${s.count.toLocaleString("fr-FR")} annonce${s.count > 1 ? "s" : ""}`;
    }
    txt.append(b, c);
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
