
/* =================== TOASTS =================== */
function toast(msg, type = "info") {
  const box = document.getElementById("toasts");
  const t = document.createElement("div");
  t.className = "toast " + type;
  const icons = { success: "✓", error: "✕", info: "ℹ" };
  t.innerHTML = `<div class="ic">${icons[type] || "ℹ"}</div><div>${esc(msg)}</div>`;
  box.appendChild(t);
  setTimeout(() => { t.classList.add("hide"); setTimeout(() => t.remove(), 380); }, 4200);
}

/* =================== SOURIS / FLOU CARTES =================== */
document.addEventListener("mousemove", e => {
  const card = e.target.closest?.(".card, .drop");
  if (!card) return;
  const r = card.getBoundingClientRect();
  card.style.setProperty("--mx", (e.clientX - r.left) + "px");
  card.style.setProperty("--my", (e.clientY - r.top) + "px");
});

/* =================== HORLOGE =================== */
setInterval(() => {
  const n = new Date();
  document.getElementById("clockChip").textContent =
    n.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" }) + " · " +
    n.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}, 1000);

/* =================== LOG =================== */
function log(msg, cls = "") {
  const el = document.getElementById("processLog");
  const t = new Date().toLocaleTimeString("fr-FR");
  el.innerHTML += `\n<span class="lt">[${t}]</span> <span class="${cls}">${esc(msg)}</span>`;
  el.scrollTop = el.scrollHeight;
}

/* =================== UPLOAD =================== */
const drop = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
drop.addEventListener("click", () => fileInput.click());
drop.addEventListener("keydown", event => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    fileInput.click();
  }
});
drop.addEventListener("dragover", e => { e.preventDefault(); drop.classList.add("drag"); });
drop.addEventListener("dragleave", () => drop.classList.remove("drag"));
drop.addEventListener("drop", e => {
  e.preventDefault(); drop.classList.remove("drag");
  if (e.dataTransfer.files.length) { fileInput.files = e.dataTransfer.files; onFile(); }
});
fileInput.addEventListener("change", onFile);

function setFile(file) {
  currentFile = file || null;
  document.getElementById("dropName").textContent = currentFile ? "📎 " + currentFile.name : "";
  document.getElementById("uploadBtn").disabled = !currentFile || !connected;
  document.getElementById("clearBtn").style.display = currentFile ? "" : "none";
  if (currentFile) toast("Fichier prêt : " + currentFile.name, "info");
}

function onFile() { setFile(fileInput.files[0] || null); }

document.getElementById("clearBtn").addEventListener("click", () => {
  currentFile = null; fileInput.value = "";
  document.getElementById("dropName").textContent = "";
  document.getElementById("uploadBtn").disabled = true;
  document.getElementById("clearBtn").style.display = "none";
});

/* =================== CAPTURE CAMÉRA =================== */
const camOverlay = document.getElementById("camOverlay");
const camVideo = document.getElementById("camVideo");
const camCanvas = document.getElementById("camCanvas");
let camStream = null;
let cameraReturnFocus = null;

function closeCamera() {
  if (camStream) { camStream.getTracks().forEach(t => t.stop()); camStream = null; }
  camVideo.srcObject = null;
  camOverlay.style.display = "none";
  camOverlay.setAttribute("aria-hidden", "true");
  if (cameraReturnFocus && cameraReturnFocus.isConnected) cameraReturnFocus.focus();
  cameraReturnFocus = null;
}

async function openCamera() {
  cameraReturnFocus = document.activeElement;
  document.getElementById("camNote").textContent = "";
  camOverlay.style.display = "flex";
  camOverlay.setAttribute("aria-hidden", "false");
  document.getElementById("camMode").focus();
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("API caméra indisponible dans ce contexte");
    }
    camStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 } }, audio: false });
    camVideo.srcObject = camStream;
  } catch (e) {
    // pas de caméra, permission refusée, ou iframe sans autorisation caméra :
    // repli sur l'entrée fichier native (ouvre l'appareil photo sur mobile)
    closeCamera();
    toast("Caméra indisponible (" + e.message + ") — sélecteur de fichier", "info");
    document.getElementById("cameraInput").click();
  }
}

document.getElementById("cameraBtn").addEventListener("click", openCamera);
document.getElementById("camCancelBtn").addEventListener("click", closeCamera);
camOverlay.addEventListener("click", event => {
  if (event.target === camOverlay) closeCamera();
});
camOverlay.addEventListener("keydown", event => {
  if (event.key === "Escape") {
    event.preventDefault();
    closeCamera();
    return;
  }
  if (event.key !== "Tab") return;
  const focusables = [...camOverlay.querySelectorAll("button:not([disabled]), select:not([disabled]), input:not([disabled]), video[tabindex]")];
  if (!focusables.length) { event.preventDefault(); return; }
  const first = focusables[0], last = focusables[focusables.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault(); last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault(); first.focus();
  }
});

document.getElementById("camCaptureBtn").addEventListener("click", () => {
  const w = camVideo.videoWidth, h = camVideo.videoHeight;
  if (!w || !h) { toast("Caméra non prête — réessayez", "error"); return; }
  camCanvas.width = w; camCanvas.height = h;
  camCanvas.getContext("2d").drawImage(camVideo, 0, 0, w, h);
  camCanvas.toBlob((blob) => {
    if (!blob) { toast("Capture impossible", "error"); return; }
    const file = new File([blob], "photo_" + Date.now() + ".png", { type: "image/png" });
    applyCamMode();
    setFile(file);
    closeCamera();
    toast("Photo capturée 📸", "success");
  }, "image/png");
});

function applyCamMode() {
  const mode = document.getElementById("camMode").value;
  if (mode === "container" || mode === "vehicle_plate" || mode === "carte_grise") {
    document.getElementById("profileSelect").value = mode;
    syncProfileHint();
  }
}

document.getElementById("cameraInput").addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (f) { applyCamMode(); setFile(f); }
  e.target.value = "";
});

document.getElementById("uploadBtn").addEventListener("click", async () => {
  if (!currentFile) return;
  if (!connected) {
    toast("Serveur injoignable — connectez l'API via le bandeau jaune", "error");
    log("ERREUR : serveur API injoignable (aperçu statique ?) — ouvrez l'URL du serveur live ou collez-la dans le bandeau", "err");
    return;
  }
  const fd = new FormData();
  fd.append("file", currentFile);
  fd.append("profile", document.getElementById("profileSelect").value);
  const langsSel = [...document.querySelectorAll("#langChips .langchip.on")]
    .map(c => c.dataset.lang).join(",");
  const fmtsSel = [...document.querySelectorAll("#fmtChips input:checked")]
    .map(i => i.dataset.fmt).join(",");
  const qmBtn = document.querySelector("#qualitySeg .on");
  fd.append("languages", langsSel);
  fd.append("quality_mode", qmBtn ? qmBtn.dataset.qm : "accurate");
  fd.append("preprocess", document.getElementById("preprocessMode").value !== "off");
  fd.append("preprocess_mode", document.getElementById("preprocessMode").value);
  fd.append("variant_comparison", document.getElementById("variantCmp").checked);
  fd.append("export_formats", fmtsSel || "json,txt");
  fd.append("page_range", document.getElementById("pageRange").value.trim());
  fd.append("render_dpi", document.getElementById("renderDpi").value);
  fd.append("engine", document.getElementById("engineSelect").value);
  fd.append("extract_fields", document.getElementById("exFields").checked);
  fd.append("extract_tables", document.getElementById("exTables").checked);
  fd.append("extract_barcodes", document.getElementById("exBarcodes").checked);
  fd.append("min_confidence_review", (document.getElementById("reviewRange").value / 100).toFixed(2));
  document.getElementById("uploadStatus").textContent = "Envoi en cours…";
  document.querySelector(".instrument").classList.add("processing");
  resetPipeline();
  try {
    const r = await fetchAuthenticated("/api/documents", { method: "POST", body: fd });
    if (!r.ok) throw new Error(await readError(r));
    const j = await r.json();
    currentJob = j.job_id;
    document.getElementById("uploadStatus").textContent = "Job " + j.job_id;
    log("Document reçu — « " + j.filename + " »", "ok");
    toast("Analyse lancée 🚀", "success");
    pollJob(j.job_id);
  } catch (e) {
    document.getElementById("uploadStatus").textContent = "Erreur";
    log("ERREUR : " + e.message, "err");
    toast("Échec : " + e.message, "error");
  }
});

function resetPipeline() {
  document.getElementById("progressBar").style.width = "0%";
  document.querySelectorAll("#pipelineSteps .step").forEach(s => s.classList.remove("on", "done", "err"));
  document.querySelector(".instrument").classList.remove("processing");
}

function setStage(stage, error = false) {
  const stages = ["ingest", "ocr", "tables", "fields", "quality", "done"];
  const idx = stages.indexOf(stage);
  document.querySelectorAll("#pipelineSteps .step").forEach((s, i) => {
    s.classList.remove("on", "done", "err");
    if (idx < 0) return;
    if (i < idx) s.classList.add("done");
    else if (i === idx) s.classList.add(error ? "err" : "on");
  });
}

async function pollJob(id) {
  const tick = async () => {
    let j;
    try { j = await fetchJson("/api/jobs/" + id); }
    catch { return setTimeout(tick, 1200); }
    document.getElementById("progressBar").style.width = Math.round((j.progress || 0) * 100) + "%";
    setStage(j.stage || "", j.status === "error");
    if (j.status === "done") {
      setStage("done");
      document.querySelector(".instrument").classList.remove("processing");
      log("Traitement terminé avec succès ✓", "ok");
      toast("Analyse terminée ✨", "success");
      loadResult(id); loadJobs();
      return;
    }
    if (j.status === "error") {
      document.querySelector(".instrument").classList.remove("processing");
      log("Échec : " + (j.error || "inconnu"), "err");
      toast("Traitement en échec", "error");
      return;
    }
    setTimeout(tick, 800);
  };
  tick();
}

/* =================== RESULTAT =================== */
async function loadResult(id) {
  let res;
  try { res = await fetchJson("/api/jobs/" + id + "/result"); }
  catch (e) { toast(e.message, "error"); return; }
  currentResult = res;
  currentPage = 1;
  renderResult();

  const links = document.getElementById("exportLinks");
  const links2 = document.getElementById("exportLinksResult");
  [links, links2].forEach(box => { box.innerHTML = ""; });
  const fmts = [["json", "🧬", "données complètes"], ["txt", "📄", "texte brut"],
                ["csv", "📑", "champs + tableaux"], ["xlsx", "📊", "classeur 5 feuilles"],
                ["xml", "🔮", "intégration tiers"], ["pdf", "📕", "PDF consultable"]];
  fmts.forEach(([f, ic, sub]) => {
    const b = document.createElement("button");
    b.className = "export-item";
    b.style.cursor = "pointer";
    b.innerHTML = `<div class="ic">${ic}</div><div class="fmt">${f.toUpperCase()}</div><div class="sz">${sub}</div>`;
    b.addEventListener("click", () => downloadExport(f));
    links.appendChild(b);
    const b2 = b.cloneNode(true);
    b2.addEventListener("click", () => downloadExport(f));
    links2.appendChild(b2);
  });
}

/* Téléchargement robuste : fetch → Blob → sauvegarde, avec retour visuel */
async function downloadExport(fmt) {
  if (!currentJob) { toast("Aucun document sélectionné", "info"); return; }
  toast("Préparation de l'export " + fmt.toUpperCase() + "…", "info");
  try {
    const r = await fetchAuthenticated("/api/jobs/" + currentJob + "/export/" + fmt);
    if (!r.ok) throw new Error(await readError(r));
    const blob = await r.blob();
    const cd = r.headers.get("content-disposition") || "";
    const m = cd.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
    const fname = m ? decodeURIComponent(m[1]) : ("unocr_export." + (fmt === "csv" && blob.type.includes("zip") ? "zip" : fmt));
    const a = document.createElement("a");
    const url = URL.createObjectURL(blob);
    a.href = url;
    a.download = fname;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    log("Export " + fmt.toUpperCase() + " téléchargé (" + Math.round(blob.size / 1024) + " Ko)", "ok");
    toast("Export " + fmt.toUpperCase() + " téléchargé ✓", "success");
  } catch (e) {
    log("ERREUR export " + fmt + " : " + e.message, "err");
    toast("Export " + fmt.toUpperCase() + " impossible : " + e.message, "error");
  }
}

function renderResult() {
  if (!currentResult) return;
  const res = currentResult;
  renderPage();
  document.getElementById("textView").value =
    (res.pages || []).map(p => "───── Page " + p.page_num + " ─────\n" + p.text).join("\n\n");

  // champs
  const ft = document.querySelector("#fieldsTable tbody");
  ft.innerHTML = "";
  Object.entries(res.fields || {}).forEach(([name, f]) => {
    const tr = document.createElement("tr");
    const conf = Math.round((f.confidence || 0) * 100);
    const cls = conf >= 75 ? "hi" : (conf >= 50 ? "md" : "lo");
    tr.innerHTML =
      `<td><b>${esc(f.label || name)}</b><br><span class="mono" style="font-size:10px;color:var(--muted)">${esc(name)}</span></td>` +
      `<td>${f.raw_value ? esc(f.raw_value) : '<span class="muted">non détecté</span>'}</td>` +
      `<td class="muted">${esc(f.normalized_value ?? "—")}</td>` +
      `<td><span class="meter ${cls}"><i style="width:0"></i></span><b style="font-size:11.5px">${conf}%</b></td>` +
      `<td><span class="badge ${esc(f.status)}">${esc(f.status)}</span></td>` +
      `<td><div class="rowflex"><input class="edit" data-field="${esc(name)}" placeholder="valeur confirmée…">` +
      `<button class="btn sm" data-confirm="${esc(name)}">Valider</button></div></td>`;
    // Pas de gestionnaire en ligne : une valeur contrôlée par l'utilisateur
    // (le nom d'un champ de profil) placée dans `onclick="…"` s'exécute
    // après décodage HTML — l'échappement des caractères ne suffit pas.
    // Le nom passe par `dataset` et l'action par `addEventListener`.
    tr.querySelector("[data-confirm]").addEventListener("click", () => {
      confirmField(name);
    });
    tr.addEventListener("click", e => {
      if (e.target.closest("input,button")) return;
      document.querySelectorAll("#fieldsTable tbody tr").forEach(x => x.classList.remove("sel"));
      tr.classList.add("sel");
      highlightField(f);
    });
    ft.appendChild(tr);
    requestAnimationFrame(() => {
      const m = tr.querySelector(".meter i");
      if (m) m.style.width = conf + "%";
    });
  });

  // tableaux
  const tv = document.getElementById("tablesView");
  if (!(res.tables || []).length) {
    tv.innerHTML = '<div class="empty"><div class="big">📊</div>Aucun tableau détecté.</div>';
  } else {
    tv.innerHTML = res.tables.map((t, i) => {
      const matrix = buildMatrix(t);
      return `<div style="margin-bottom:16px">
        <div class="rowflex" style="margin-bottom:8px">
          <span class="badge info">TABLE ${i + 1}</span>
          <span class="pill">page ${t.page_num}</span>
          <span class="pill">${esc(t.method)}</span>
          <span class="pill">${Math.round((t.confidence || 0) * 100)}% conf.</span>
          ${t.multipage ? '<span class="badge validated">multipages</span>' : ""}
        </div>
        <div class="scroll" style="max-height:250px"><table class="tbl">` +
        matrix.map((row, ri) => "<tr>" + row.map(c =>
          ri < (t.header_rows || 1) ? `<th>${esc(c)}</th>` : `<td>${esc(c)}</td>`
        ).join("") + "</tr>").join("") +
        `</table></div></div>`;
    }).join("");
  }

  // codes-barres
  const bv = document.getElementById("barcodesView");
  bv.innerHTML = (res.barcodes || []).length
    ? res.barcodes.map(b => `<div class="anom"><div class="msg"><span class="badge info">${esc(b.format)}</span> <b class="mono">${esc(b.text)}</b></div><div class="pg pill">p.${b.page}</div></div>`).join("")
    : '<div class="empty"><div class="big">🏷️</div>Aucun code détecté.</div>';

  // moteurs
  const ev = document.getElementById("enginesView");
  const runs = (res.pages || []).flatMap(p => p.engine_runs || []);
  const byEngine = {};
  runs.forEach(r => {
    byEngine[r.engine] = byEngine[r.engine] || { conf: [], words: 0, ms: 0 };
    byEngine[r.engine].conf.push(r.mean_confidence);
    byEngine[r.engine].words += r.word_count; byEngine[r.engine].ms += r.duration_ms;
  });
  const names = Object.keys(byEngine);
  if (names.length > 1) {
    ev.innerHTML = names.map(n => {
      const v = byEngine[n];
      const c = Math.round(v.conf.reduce((a, b) => a + b, 0) / v.conf.length * 100);
      return `<div class="engine-row"><span class="stat up"></span><b>${esc(n)}</b>
        <span class="meter hi"><i style="width:${c}%"></i></span>
        <div class="meta">${v.words} mots · ${Math.round(v.ms)} ms</div></div>`;
    }).join("");
  } else {
    ev.innerHTML = '<div class="empty">Comparaison indisponible : un seul moteur OCR actif dans cet environnement.<br>L\'architecture multi-moteurs s\'active dès qu\'EasyOCR/PaddleOCR est installé.</div>';
  }

  // qualité
  const q = res.quality || {};
  setGauge("gaugeEngine", "qEngine", q.mean_engine_confidence);
  setGauge("gaugeGlobal", "qGlobal", q.mean_global_confidence);
  const anoms = q.anomalies || [];
  document.getElementById("qAnom").textContent = anoms.length;
  const errs = anoms.filter(a => a.severity === "error").length;
  const warns = anoms.filter(a => a.severity === "warning").length;
  document.getElementById("qAnomBreak").textContent =
    `${errs} erreur(s) · ${warns} avertissement(s) · ${anoms.length - errs - warns} info(s)`;

  const av = document.getElementById("anomaliesView");
  if (!anoms.length) {
    av.innerHTML = '<div class="empty"><div class="big">✨</div>Aucune anomalie détectée.</div>';
  } else {
    av.innerHTML = anoms.map(a => {
      const sev = a.severity === "error" ? "crit" : (a.severity === "warning" ? "warn" : "info");
      return `<div class="anom"><span class="badge ${sev}">${esc(a.code)}</span>
        <div class="msg">${esc(a.message)}</div>
        ${a.page_num ? `<div class="pg pill">p.${a.page_num}</div>` : ""}</div>`;
    }).join("");
  }
  const disag = q.disagreements || [];
  document.getElementById("disagreementsView").innerHTML = disag.length
    ? disag.map(d => `<div class="anom"><div class="msg mono">${esc(JSON.stringify(d.text_by_engine))}</div><div class="pg badge ${d.resolution === "best_confidence" ? "validated" : "warn"}">${esc(d.resolution)}</div></div>`).join("")
    : '<div class="empty">Aucun désaccord entre moteurs.</div>';
}

function setGauge(gaugeId, labelId, value) {
  const v = Math.round((value || 0) * 100);
  const circ = document.getElementById(gaugeId);
  if (circ) circ.style.strokeDashoffset = String(289 - (289 * v / 100));
  document.getElementById(labelId).textContent = v + "%";
}

function buildMatrix(t) {
  const g = Array.from({ length: t.n_rows }, () => Array(t.n_cols).fill(""));
  (t.cells || []).forEach(c => {
    if (c.row < t.n_rows && c.col < t.n_cols) g[c.row][c.col] = c.text;
  });
  return g;
}

function renderPage() {
  const res = currentResult;
  if (!res || !(res.pages || []).length) return;
  const page = res.pages.find(p => p.page_num === currentPage) || res.pages[0];
  currentPage = page.page_num;
  document.getElementById("pageLabel").textContent =
    `page ${page.page_num} / ${res.pages.length}`;
  const vb = document.getElementById("variantBadge");
  vb.style.display = ""; vb.textContent = "variante : " + (page.variant_selected || "—");
  const lb = document.getElementById("langBadge");
  const langs = (page.detected_languages || []).join(", ");
  if (langs) { lb.style.display = ""; lb.textContent = "🌐 " + langs; } else lb.style.display = "none";

  const viewer = document.getElementById("viewer");
  viewer.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "wrap";
  const img = document.createElement("img");
  img.src = API + "/api/jobs/" + currentJob + "/page/" + page.page_num + "/image";
  img.alt = "page " + page.page_num;
  img.onerror = () => {
    viewer.innerHTML = '<div class="empty" style="margin:14px"><div class="big">📃</div>Page purement numérique — pas d\'image source.<br>Le texte complet est affiché dans le panneau de droite.</div>';
  };
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${page.width} ${page.height}`);
  svg.id = "overlaySvg";
  wrap.appendChild(img); wrap.appendChild(svg);
  viewer.appendChild(wrap);
  (page.words || []).forEach(w => {
    const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    r.setAttribute("x", w.bbox.x0); r.setAttribute("y", w.bbox.y0);
    r.setAttribute("width", w.bbox.x1 - w.bbox.x0);
    r.setAttribute("height", w.bbox.y1 - w.bbox.y0);
    r.setAttribute("class", "zone");
    svg.appendChild(r);
  });
}

function highlightField(f) {
  if (!f || !f.bbox) { toast("Champ sans géométrie localisée", "info"); return; }
  if (f.page_num && f.page_num !== currentPage) {
    currentPage = f.page_num;
    renderPage();
    setTimeout(() => highlightField(f), 350);
    return;
  }
  const svg = document.getElementById("overlaySvg");
  if (!svg) return;
  svg.querySelectorAll("rect").forEach(r => r.classList.remove("hl"));
  const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  r.setAttribute("x", f.bbox.x0); r.setAttribute("y", f.bbox.y0);
  r.setAttribute("width", f.bbox.x1 - f.bbox.x0);
  r.setAttribute("height", f.bbox.y1 - f.bbox.y0);
  r.setAttribute("class", "zone hl");
  svg.appendChild(r);
  r.scrollIntoView({ block: "center", behavior: "smooth" });
  toast("Zone localisée sur le document", "info");
}

async function confirmField(name) {
  // On retrouve le champ par parcours du DOM plutôt que par un sélecteur
  // interpolé : un nom de champ contient librement des apostrophes ou des
  // crochets, qui casseraient le sélecteur (et permettraient d'en injecter
  // un autre).
  const input = Array.from(
    document.querySelectorAll("#fieldsTable input.edit[data-field]")
  ).find(el => el.dataset.field === name);
  if (!input || !input.value) { toast("Saisissez une valeur à confirmer", "info"); return; }
  const r = await fetchAuthenticated("/api/jobs/" + currentJob + "/fields/" + encodeURIComponent(name), {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirmed_value: input.value })
  });
  if (r.ok) {
    log("Champ « " + name + " » confirmé par l'utilisateur (tracé dans l'audit)", "ok");
    toast("Champ confirmé ✓ — valeur d'origine conservée", "success");
    loadResult(currentJob);
  } else toast("Échec de la validation : " + await readError(r), "error");
}

document.getElementById("prevPage").addEventListener("click", () => {
  if (currentPage > 1) { currentPage--; renderPage(); }
});
document.getElementById("nextPage").addEventListener("click", () => {
  if (currentResult && currentPage < currentResult.pages.length) { currentPage++; renderPage(); }
});
document.getElementById("textSearch").addEventListener("input", e => {
  const q = e.target.value;
  const t = document.getElementById("textView");
  if (!q) return;
  const idx = t.value.toLowerCase().indexOf(q.toLowerCase());
  if (idx >= 0) { t.focus(); t.setSelectionRange(idx, idx + q.length); }
});

/* =================== JOBS =================== */
async function loadJobs() {
  let jobs;
  try { jobs = await fetchJson("/api/jobs?limit=100"); }
  catch (e) {
    document.querySelector("#jobsTable tbody").innerHTML = "";
    document.getElementById("jobsEmpty").style.display = "";
    return;
  }
  const q = (document.getElementById("docSearch").value || "").toLowerCase();
  const st = document.getElementById("filterStatus").value;
  const tbody = document.querySelector("#jobsTable tbody");
  tbody.innerHTML = "";
  const filtered = jobs.filter(j =>
    (!q || j.filename.toLowerCase().includes(q)) && (!st || j.status === st));
  document.getElementById("jobsEmpty").style.display = filtered.length ? "none" : "";
  filtered.forEach((j, i) => {
    const tr = document.createElement("tr");
    tr.style.animation = `riseIn .4s ${Math.min(i * 0.04, 0.5)}s both`;
    const d = new Date(j.created_at * 1000).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
    tr.innerHTML =
      `<td><b>${esc(j.filename)}</b></td>` +
      `<td><span class="badge ${j.status}">${j.status}</span></td>` +
      `<td><span class="meter ${j.status === "done" ? "hi" : "md"}"><i style="width:${Math.round(j.progress * 100)}%"></i></span></td>` +
      `<td><span class="pill">${esc(j.options?.profile || "")}</span></td>` +
      `<td class="muted" style="font-size:11px">${d}</td>` +
      `<td style="text-align:right;white-space:nowrap">
        <button class="btn ghost sm" data-open-job="${esc(j.id)}">Ouvrir</button>
        <button class="btn ghost sm" data-retry-job="${esc(j.id)}">↻</button>
        <button class="btn ghost sm" data-del-job="${esc(j.id)}">✕</button>
      </td>`;
    // GestionnairesAttachés, jamais `onclick="…"` : l'identifiant du job
    // est inséré dans l'attribut `data-*`, jamais dans du JavaScript.
    tr.querySelector("[data-open-job]").addEventListener("click", () => openJob(j.id));
    tr.querySelector("[data-retry-job]").addEventListener("click", () => retryJob(j.id));
    tr.querySelector("[data-del-job]").addEventListener("click", () => delJob(j.id));
    tbody.appendChild(tr);
  });
}
document.getElementById("docSearch").addEventListener("input", loadJobs);
document.getElementById("filterStatus").addEventListener("change", loadJobs);

function openJob(id) {
  currentJob = id;
  loadResult(id);
  document.querySelector('.nav-item[data-tab="tab-result"]').click();
}
async function retryJob(id) {
  await fetchAuthenticated("/api/jobs/" + id + "/retry", { method: "POST" });
  toast("Job relancé", "info");
  loadJobs();
}
async function delJob(id) {
  if (!confirm("Supprimer ce job et ses artefacts ? (opération journalisée)")) return;
  await fetchAuthenticated("/api/jobs/" + id, { method: "DELETE" });
  toast("Job supprimé (audit enregistré)", "info");
  loadJobs();
}

/* =================== STATS =================== */
/* ─────────────── sauvegarde du magasin (P0) ─────────────── */
function backupOut(html) {
  const box = document.getElementById("backupOut");
  if (box) box.innerHTML = html;
}

async function lancerSauvegarde() {
  backupOut('<div class="card-sub">Sauvegarde en cours…</div>');
  try {
    const r = await api("/api/backups", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keep: 5 }),
    });
    backupOut(
      '<div class="card-sub" style="color:var(--ok)">Sauvegarde créée : ' +
      esc(r.chemin.split("/").pop()) + "</div>" +
      '<div class="card-sub">' + r.fichiers + " fichier(s), " +
      Math.round(r.octets / 1024) + " Ko — empreinte " +
      esc(r.empreinte.slice(0, 16)) + "…</div>");
    toast("Sauvegarde créée ✓", "success");
  } catch (e) {
    backupOut('<div class="card-sub" style="color:var(--err)">Échec : ' +
              esc(e.message) + "</div>");
    toast("Sauvegarde impossible : " + e.message, "error");
  }
}

async function listerSauvegardes() {
  backupOut('<div class="card-sub">Lecture des sauvegardes…</div>');
  try {
    const r = await api("/api/backups");
    if (!r.sauvegardes.length) {
      backupOut('<div class="card-sub">Aucune sauvegarde pour l’instant.</div>');
      return;
    }
    let html = '<table class="tbl"><thead><tr><th>Sauvegarde</th>' +
      "<th>Taille</th><th></th></tr></thead><tbody>";
    r.sauvegardes.forEach(s => {
      html += "<tr><td class='mono'>" + esc(s.nom) + "</td><td>" +
        Math.round(s.taille / 1024) + " Ko</td>" +
        '<td><button class="btn sm" data-restore="' + esc(s.chemin) +
        '">Restaurer</button></td></tr>';
    });
    html += "</tbody></table>";
    backupOut(html);
    document.querySelectorAll("[data-restore]").forEach(b => {
      b.addEventListener("click", () => demanderRestauration(b.dataset.restore));
    });
  } catch (e) {
    backupOut('<div class="card-sub" style="color:var(--err)">Échec : ' +
              esc(e.message) + "</div>");
  }
}

function demanderRestauration(chemin) {
  /* Restaurer écrase le magasin : la confirmation doit être explicite et
     rappeler ce qui est perdu, pas un « OK » neutre. */
  const ok = confirm(
    "Restaurer " + chemin.split("/").pop() + " ?\n\n" +
    "Cette opération réécrit le magasin local. Les documents et corrections " +
    "postérieurs à la sauvegarde seront perdus.");
  if (!ok) return;
  const motif = prompt("Motif de la restauration (obligatoire) :");
  if (!motif || !motif.trim()) { toast("Restauration annulée : motif requis.", "info"); return; }
  effectuerRestauration(chemin, motif.trim());
}

async function effectuerRestauration(chemin, motif) {
  backupOut('<div class="card-sub">Restauration en cours…</div>');
  try {
    const r = await api("/api/backups/restore", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chemin: chemin, force: true }),
    });
    backupOut('<div class="card-sub" style="color:var(--ok)">Magasin restauré : ' +
              r.fichiers + " fichier(s) réécrits.</div>" +
              '<div class="card-sub">Motif consigné : ' + esc(motif) + "</div>");
    toast("Magasin restauré ✓", "success");
    if (typeof loadStats === "function") loadStats();
  } catch (e) {
    backupOut('<div class="card-sub" style="color:var(--err)">Restauration refusée : ' +
              esc(e.message) + "</div>");
    toast("Restauration impossible : " + e.message, "error");
  }
}

/* câblage des boutons de sauvegarde — posé ici pour rester à côté du code
   qu'il déclenche, et parce que les éléments existent dès le chargement. */
(function brancherSauvegarde() {
  const maintenant = document.getElementById("btnBackupNow");
  const liste = document.getElementById("btnBackupList");
  if (maintenant) maintenant.addEventListener("click", lancerSauvegarde);
  if (liste) liste.addEventListener("click", listerSauvegardes);
})();

async function loadStats() {
  let s;
  try { s = await fetchJson("/api/stats"); }
  catch (e) { return; }
  countUp("stTotal", s.jobs_total || 0);
  countUp("stDone", s.jobs_done || 0);
  countUp("stError", s.jobs_error || 0);
  document.getElementById("stMem").textContent = (s.memory_percent ?? "—") + "%";

  const counts = [s.jobs_processing || 0, s.jobs_processing || 0, s.jobs_done || 0, s.jobs_error || 0];
  const max = Math.max(4, ...counts);
  document.querySelectorAll("#statusChart .b").forEach((b, i) => {
    const vals = [s.jobs_total - s.jobs_done - s.jobs_error - s.jobs_processing, s.jobs_processing, s.jobs_done, s.jobs_error].map(v => Math.max(0, v));
    const v = vals[i];
    b.style.height = Math.max(8, (v / max) * 100) + "%";
    b.querySelector("em").textContent = v;
  });
}

function countUp(id, target) {
  const el = document.getElementById(id);
  const start = parseInt(el.textContent) || 0;
  const t0 = performance.now();
  const dur = 700;
  const step = now => {
    const p = Math.min(1, (now - t0) / dur);
    el.textContent = Math.round(start + (target - start) * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

/* =================== CONFIG =================== */
/* Repli statique : les 7 profils livrés avec le produit (si serveur injoignable) */
const STATIC_PROFILES = [
  { name: "generic", label: "Profil générique", description: "Dates, contacts, montants, identifiants courants." },
  { name: "invoice", label: "Facture", description: "Numéro, dates, TVA, totaux HT/TTC, devise." },
  { name: "port_bl", label: "Portuaire — Bill of Lading", description: "BL, conteneurs (ISO 6346 vérifiée), navire, ports, marchandises, ETA/ETD, douane." },
  { name: "packing_list", label: "Portuaire — Liste de colisage", description: "Conteneurs, sceaux, colis, poids, volumes, marquage." },
  { name: "container", label: "Photo conteneur (ISO 6346)", description: "Photo d'un conteneur : n° ISO 6346 avec chiffre de contrôle vérifié, type, sceau, plaque du camion." },
  { name: "vehicle_plate", label: "Photo plaque / véhicule", description: "Plaque d'immatriculation (FR, DZ, ES, DE, IT, PT/NL, BE, UK, TR, MA, TN), n° de châssis VIN, marque/modèle." },
  { name: "carte_grise", label: "Carte grise / certificat d'immatriculation", description: "Plaque, VIN, marque, modèle, énergie, date de 1re immatriculation, puissances, PTAC, couleur, titulaire." },
];
let ALL_PROFILES = STATIC_PROFILES.slice();

function fillProfileSelect(profs) {
  ALL_PROFILES = profs && profs.length ? profs : STATIC_PROFILES.slice();
  const photo = ["container", "vehicle_plate", "carte_grise"];
  const groups = [["Générique", p => p.name === "generic"],
                  ["Photo / terrain 📷", p => photo.includes(p.name)],
                  ["Métier", p => p.name !== "generic" && !photo.includes(p.name)
                    && !p.name.startsWith("port") && p.name !== "packing_list"],
                  ["Portuaire 🚢", p => p.name.startsWith("port") || p.name === "packing_list"]];
  const sel = document.getElementById("profileSelect");
  sel.innerHTML = "";
  groups.forEach(([label, pred]) => {
    const list = ALL_PROFILES.filter(pred);
    if (!list.length) return;
    const og = document.createElement("optgroup");
    og.label = label;
    list.forEach(p => {
      const o = document.createElement("option");
      o.value = p.name;
      o.textContent = p.label || p.name;
      og.appendChild(o);
    });
    sel.appendChild(og);
  });
  syncProfileHint();
}

function syncProfileHint() {
  const name = document.getElementById("profileSelect").value;
  const p = ALL_PROFILES.find(x => x.name === name);
  document.getElementById("profileHint").textContent = p ? (p.description || "") : "";
}
document.getElementById("profileSelect").addEventListener("change", syncProfileHint);

function setConnected(ok) {
  connected = ok;
  const chip = document.getElementById("enginesChip");
  const dot = chip.querySelector(".dot");
  const uploadBtn = document.getElementById("uploadBtn");
  if (ok) {
    chip.classList.add("glow");
    dot.style.background = "var(--ok)";
    document.getElementById("offlineBanner").style.display = "none";
    uploadBtn.disabled = !currentFile;
  } else {
    chip.classList.remove("glow");
    dot.style.background = "var(--err)";
    document.getElementById("enginesTxt").textContent = "hors connexion";
    document.getElementById("offlineBanner").style.display = "";
    uploadBtn.disabled = true;
    const inp = document.getElementById("apiBaseInput");
    if (inp && API) inp.value = API;
  }
}

/* Auto-détection : si l'UI tourne dans un aperçu (autre origine), devine l'URL
   de l'API live à partir du nom d'hôte (https://{port}-{sandbox}.e2b.app). */
async function autoProbe() {
  const m = location.hostname.match(/^(?:\d+-)?(.+\.e2b\.app)$/);
  if (!m) return false;
  const cand = "https://8000-" + m[1];
  if (cand === location.origin) return false;
  try {
    const r = await fetch(cand + "/api/health", { signal: AbortSignal.timeout(5000) });
    if (r.ok) {
      API = cand;
      localStorage.setItem("unocr_api", cand);
      toast("API UniOCR détectée : " + cand, "success");
      log("API détectée automatiquement : " + cand, "ok");
      return true;
    }
  } catch (e) { /* inaccessible — on garde le mode aperçu */ }
  return false;
}

/* Connexion manuelle à une URL de serveur (aperçu cross-origin, proxy…) */
document.getElementById("apiBaseBtn").addEventListener("click", async () => {
  const val = (document.getElementById("apiBaseInput").value || "").trim().replace(/\/+$/, "");
  if (!val) { toast("Saisissez l'URL du serveur UniOCR", "info"); return; }
  try {
    const r = await fetch(val + "/api/health", { signal: AbortSignal.timeout(6000) });
    if (!r.ok) throw new Error("HTTP " + r.status);
    localStorage.setItem("unocr_api", val);
    toast("Connecté au serveur " + val + " ✓", "success");
    setTimeout(() => location.reload(), 600);
  } catch (e) {
    toast("Impossible de joindre " + val + " (" + e.message + ")", "error");
  }
});

async function loadConfig() {
  try {
    const [eng, langs, profs] = await Promise.all([
      fetchJson("/api/engines"),
      fetchJson("/api/languages"),
      fetchJson("/api/profiles"),
    ]);
    setConnected(true);
    const actives = eng.filter(e => e.available).map(e => e.name);
    document.getElementById("enginesTxt").textContent = "moteurs actifs : " + actives.join(", ");

    document.getElementById("enginesList").innerHTML = eng.map(e =>
      `<div class="engine-row">
        <span class="stat ${e.available ? "up" : "down"}"></span>
        <b>${esc(e.name)}</b>
        <span class="pill">${esc(e.kind)}</span>
        ${e.available ? '<span class="badge done">actif</span>' : '<span class="badge not_detected">non installé</span>'}
        <div class="meta">${e.available ? esc((e.languages || []).slice(0, 6).join(" ") || "—") : "s'active automatiquement si installé"}</div>
      </div>`).join("");

    document.getElementById("langsView").innerHTML =
      (langs.installed_models || []).map(l => `<span class="pill lang">🌐 ${esc(l)}</span>`).join("") +
      `<div class="muted" style="font-size:11px;margin-top:9px">Seules les langues dont le modèle est installé sont déclarées supportées.</div>`;

    document.getElementById("profilesView").innerHTML = (profs || []).map(p =>
      `<div class="anom"><div class="msg"><b>${esc(p.name)}</b> — ${esc(p.label)}
        <div class="muted" style="margin-top:3px">${esc(p.description)}</div>
        <div style="margin-top:6px">${(p.fields || []).slice(0, 6).map(f => `<span class="pill" style="font-size:10px">${esc(f)}</span>`).join("")}${(p.fields || []).length > 6 ? `<span class="pill" style="font-size:10px">+${p.fields.length - 6}</span>` : ""}</div>
      </div></div>`).join("");

    fillProfileSelect(profs);
  } catch (e) {
    setConnected(false);
    fillProfileSelect(STATIC_PROFILES);
    document.getElementById("enginesList").innerHTML = '<div class="empty">Serveur injoignable — lancez <b class="mono">./scripts/run_server.sh</b>.</div>';
  }
}

/* =================== UTILS =================== */
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* =================== OPTIONS (panneau avancé) =================== */
function initOptions() {
  // Ce panneau appartient à l'ancienne page d'import : s'il n'est pas dans le
  // document, on n'empêche pas le reste des extras (thème, raccourcis) de
  // s'initialiser.
  const advToggle = document.getElementById("advToggle");
  if (!advToggle) return;
  advToggle.addEventListener("click", () => {
    document.getElementById("advPanel")?.classList.toggle("open");
  });
  document.querySelectorAll("#qualitySeg button").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll("#qualitySeg button").forEach(x => x.classList.remove("on"));
    b.classList.add("on");
    const hint = document.getElementById("qmHint");
    if (hint) hint.textContent = b.dataset.qm === "accurate"
      ? "Accurate compare les variantes et garde la meilleure."
      : "Fast traite chaque page avec un seul passage.";
  }));
  document.querySelectorAll("#fmtChips .langchip").forEach(chip => chip.addEventListener("click", (e) => {
    e.preventDefault();
    const cb = chip.querySelector("input");
    if (!cb) return;
    cb.checked = !cb.checked;
    chip.classList.toggle("on", cb.checked);
  }));
  const range = document.getElementById("reviewRange");
  if (range) range.addEventListener("input", (e) => {
    const val = document.getElementById("reviewVal");
    if (val) val.textContent = e.target.value + " %";
  });
}

async function initLangChips() {
  const box = document.getElementById("langChips");
  if (!box) return;
  try {
    const data = await api("/api/languages");
    const installed = data.installed_models || [];
    const names = data.catalog || {};
    if (!installed.length) {
      box.innerHTML = '<span class="muted" style="font-size:11px">Aucun modèle de langue détecté — l\'auto-détection sera utilisée.</span>';
      return;
    }
    box.innerHTML = installed.map(code =>
      `<span class="langchip" data-lang="${esc(code)}">${esc(code)}${names[code] ? " · " + esc(names[code]) : ""}<span class="ok">✓</span></span>`
    ).join("");
    box.querySelectorAll(".langchip").forEach(chip => chip.addEventListener("click", () => {
      chip.classList.toggle("on");
    }));
  } catch (e) {
    box.innerHTML = '<span class="muted" style="font-size:11px">API non joignable — connectez l\'API puis rechargez pour choisir les langues.</span>';
  }
}

/* =================== INIT =================== */
(async () => {
  try { initOptions(); } catch (e) { /* panneau absent : sans effet */ }
  await loadConfig();
  if (!connected && await autoProbe()) {
    await loadConfig();          // recharge avec l'API détectée
  }
  if (!connected) {
    log("Aucune API jointe — si vous êtes dans l'aperçu du lecteur de fichiers, ouvrez l'URL du serveur live (port 8000) ou collez-la dans le bandeau jaune.", "err");
  }
  await initLangChips();
  try { await loadJobs(); } catch (e) {}
})();


/* ═══════════ EXTRAS ÉDITORIAUX ═══════════
   Ajouts uniquement : aucun code métier ci-dessus n'est modifié.
   - bascule de thème (clair / sombre, préférence système respectée)
   - réduction de la barre latérale
   - recherche globale → filtre réel des documents
   - page d'accueil : données RÉELLES (moteurs, stats, derniers jobs)
   ═══════════════════════════════════════════ */
(function editorialExtras() {
  const root = document.documentElement;
  const saved = localStorage.getItem("unocr_theme");
  const prefersLight = window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: light)").matches;
  if (saved === "light" || saved === "dark") root.setAttribute("data-theme", saved);
  else if (prefersLight) root.setAttribute("data-theme", "light");

  const tt = document.getElementById("themeToggle");
  if (tt) tt.addEventListener("click", () => {
    const next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
    root.setAttribute("data-theme", next);
    localStorage.setItem("unocr_theme", next);
  });

  const app = document.getElementById("app");
  const sc = document.getElementById("sidebarCollapse");
  if (sc && app) sc.addEventListener("click", () => {
    app.classList.toggle("collapsed");
    localStorage.setItem("unocr_sidebar",
      app.classList.contains("collapsed") ? "1" : "0");
  });
  if (app && localStorage.getItem("unocr_sidebar") === "1")
    app.classList.add("collapsed");

  // recherche globale : filtre réel de la liste des documents
  const gs = document.getElementById("globalSearch");
  if (gs) gs.addEventListener("input", () => {
    const ds = document.getElementById("docSearch");
    if (ds) {
      ds.value = gs.value;
      ds.dispatchEvent(new Event("input"));
    }
  });

  // ── page d'accueil : uniquement des données réelles ──
  async function loadHome() {
    const engEl = document.getElementById("homeEngines");
    const stEl = document.getElementById("homeStats");
    const recEl = document.getElementById("homeRecent");
    if (!engEl && !stEl && !recEl) return;
    try {
      const [eng, st, jobs] = await Promise.all([
        api("/api/engines"), api("/api/stats"), api("/api/jobs?limit=5"),
      ]);
      const avail = (eng || []).filter(e => e.available).map(e => e.name);
      if (engEl) engEl.textContent = avail.length
        ? avail.join(" · ")
        : "aucun moteur disponible";
      if (stEl) stEl.textContent =
        (st.jobs_total || 0) + " documents · " + (st.jobs_done || 0) +
        " terminés · mémoire " + (st.memory_percent != null ? st.memory_percent : "—") + " %";
      if (recEl) {
        const list = Array.isArray(jobs) ? jobs.slice(0, 5) : [];
        if (!list.length) {
          recEl.innerHTML = '<div class="empty">Aucun document traité pour l\'instant — l\'historique apparaîtra ici.</div>';
        } else {
          recEl.innerHTML = list.map(j => {
            const d = j.created_at
              ? new Date(j.created_at * 1000).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })
              : "";
            return '<div class="recent-item" data-open-job="' + esc(j.id) + '" role="button" tabindex="0">' +
              '<span class="badge ' + esc(j.status) + '">' + esc(j.status) + '</span>' +
              '<span class="fn">' + esc(j.filename) + '</span>' +
              '<span class="mono muted" style="font-size:10px">' + d + '</span></div>';
          }).join("");
          // Délégation d'événement : l'identifiant du job reste dans un
          // attribut `data-*`, il n'est jamais interprété comme du code.
          recEl.querySelectorAll("[data-open-job]").forEach(el => {
            el.addEventListener("click", () => openJob(el.dataset.openJob));
            el.addEventListener("keydown", (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openJob(el.dataset.openJob);
              }
            });
          });
        }
      }
    } catch (e) {
      if (engEl) engEl.textContent = "API non jointe — données indisponibles";
      if (stEl) stEl.textContent = "—";
      if (recEl && !recEl.querySelector(".recent-item"))
        recEl.innerHTML = '<div class="empty">Historique indisponible — API non jointe.</div>';
    }
  }
  loadHome();
  setInterval(loadHome, 20000);
})();
/* ═══════════ RÉVISION, RECHERCHE, RACCOURCIS ═══════════
   Ajouts purs : le code métier ci-dessus n'est pas modifié.
   ═══════════════════════════════════════════════════════ */
(function reviewSearchKeys() {
  const PAGE = "tab-review";

  /* ---- 1. entrée de navigation pour la page Révision ---- */
  const META = window.PAGE_META || (window.PAGE_META = {});
  META[PAGE] = ["À réviser", "File de validation humaine — champs à trancher"];

  /* ---- 2. file de révision ---- */
  let reviewData = [];
  let focusIdx = 0;

  const $ = id => document.getElementById(id);

  async function loadReview() {
    const list = $("reviewList"), count = $("reviewCount"), stats = $("reviewStats");
    if (!list) return;
    const threshold = $("reviewThreshold")?.value || "0.75";
    const undet = $("reviewUndetected")?.checked ? "true" : "false";
    list.innerHTML = '<div class="muted">Chargement de la file…</div>';
    try {
      const d = await api(`/api/review?threshold=${encodeURIComponent(threshold)}` +
        `&include_undetected=${undet}`);
      reviewData = d.items || [];
      focusIdx = 0;
      if (!reviewData.length) {
        list.innerHTML = '<div class="empty">Rien à réviser — tous les champs sont ' +
          'au-dessus du seuil, détectés et valides.</div>';
        count.textContent = "0 champ";
        stats.innerHTML = stat("Documents", 0) + stat("Champs", 0);
        return;
      }
      const nFields = reviewData.reduce((n, i) => n + i.fields.length, 0);
      count.textContent = `${nFields} champ${nFields > 1 ? "s" : ""} · ` +
        `${reviewData.length} document${reviewData.length > 1 ? "s" : ""}`;
      stats.innerHTML = stat("Documents", reviewData.length) + stat("Champs", nFields) +
        stat("Seuil", Math.round(d.threshold * 100) + " %");
      list.innerHTML = reviewData.map((doc, di) => `
        <div class="review-doc">
          <div class="review-doc-head">
            <span class="fn">${esc(doc.filename)}</span>
            ${doc.profile ? `<span class="pill">${esc(doc.profile)}</span>` : ""}
            <span class="meta">${doc.created_at
              ? new Date(doc.created_at * 1000).toLocaleString("fr-FR",
                  { dateStyle: "short", timeStyle: "short" }) : ""}</span>
          </div>
          ${doc.fields.map((f, fi) => reviewRow(doc, f, di, fi)).join("")}
        </div>`).join("");
      markFocus();
    } catch (e) {
      list.innerHTML = '<div class="empty">File indisponible — API non jointe.</div>';
      count.textContent = "—";
    }
  }

  function stat(lbl, val) {
    return `<div class="stat"><span class="big">${val}</span><span class="lbl">${lbl}</span></div>`;
  }

  function reviewRow(doc, f, di, fi) {
    const conf = Math.round((f.confidence || 0) * 100);
    const cls = conf >= 75 ? "hi" : (conf >= 50 ? "md" : "lo");
    return `<div class="review-row" data-di="${di}" data-fi="${fi}" data-job="${esc(doc.job_id)}"
                 data-field="${esc(f.field)}">
      <div>
        <span class="rr-label">${esc(f.label || f.field)}</span>
        <span class="rr-name">${esc(f.field)}</span>
        <div class="rr-reasons">⚠ ${f.reasons.map(esc).join(" · ")}</div>
      </div>
      <div>
        <div class="rr-value">${f.value ? esc(f.value) : '<span class="muted">non détecté</span>'}</div>
        <div class="rr-conf" style="margin-top:5px">
          <span class="meter ${cls}" style="width:64px"><i style="width:${conf}%"></i></span>
          <span>${conf}%</span>
          <span class="badge ${esc(f.status)}">${esc(f.status)}</span>
        </div>
      </div>
      <div class="rr-actions">
        <input class="edit" data-confirm value="${esc(f.value || "")}"
               placeholder="valeur confirmée…" aria-label="Valeur confirmée pour ${esc(f.label || f.field)}">
        <div class="rr-btn-row">
          <button class="btn sm" data-validate>Valider</button>
          <button class="btn ghost sm" data-undo title="Restaurer l'état d'avant correction (U)">Annuler</button>
          <button class="btn ghost sm" data-open>Ouvrir</button>
        </div>
      </div>
    </div>`;
  }

  function markFocus() {
    document.querySelectorAll("#reviewList .review-row").forEach(r => r.classList.remove("focused"));
    const rows = document.querySelectorAll("#reviewList .review-row");
    if (!rows.length) return;
    focusIdx = Math.max(0, Math.min(focusIdx, rows.length - 1));
    rows[focusIdx].classList.add("focused");
    rows[focusIdx].scrollIntoView({ block: "nearest" });
  }

  function rowCourante() {
    return document.querySelectorAll("#reviewList .review-row")[focusIdx] || null;
  }

  /* Annulation d'une correction : l'état d'avant est restitué, la trace reste.
     Le motif est demandé car une annulation est une décision, pas un clic. */
  async function undoRow(row) {
    const job = row.dataset.job, field = row.dataset.field;
    const motif = prompt(`Pourquoi annuler la correction de « ${field} » ?`);
    if (motif === null) return;
    if (!motif.trim()) { toast("Un motif est nécessaire pour tracer l'annulation.", "error"); return; }
    try {
      const r = await api(`/api/jobs/${job}/fields/${field}/undo`, {
        method: "POST", body: JSON.stringify({ motif: motif.trim() }),
      });
      toast(`« ${field} » restauré à « ${r.restaure?.valeur ?? "?"} »`, "success");
      loadReview();
    } catch (e) {
      toast(`Annulation impossible : ${e.message}`, "error");
    }
  }

  async function validateRow(row) {
    const job = row.dataset.job, field = row.dataset.field;
    const input = row.querySelector("[data-confirm]");
    const value = (input?.value || "").trim();
    if (!value) { toast("Saisissez une valeur à confirmer.", "error"); input?.focus(); return; }
    try {
      await api(`/api/jobs/${job}/fields/${field}`, {
        method: "PATCH", body: JSON.stringify({ confirmed_value: value }),
      });
      row.classList.add("done");
      toast(`« ${value} » confirmé pour ${field}`, "success");
      loadReview();
    } catch (e) {
      toast(`Validation impossible : ${e.message}`, "error");
    }
  }

  /* Annulation d'une correction : l'état d'avant est restitué, la trace reste.
     Le motif est demandé car une annulation est une décision, pas un clic. */
  async function undoRow(row) {
    const job = row.dataset.job, field = row.dataset.field;
    const motif = prompt(`Pourquoi annuler la correction de « ${field} » ?`);
    if (motif === null) return;
    if (!motif.trim()) { toast("Un motif est nécessaire pour tracer l'annulation.", "error"); return; }
    try {
      const r = await api(`/api/jobs/${job}/fields/${field}/undo`, {
        method: "POST", body: JSON.stringify({ motif: motif.trim() }),
      });
      toast(`« ${field} » restauré à « ${r.restaure?.valeur ?? "?"} »`, "success");
      loadReview();
    } catch (e) {
      toast(`Annulation impossible : ${e.message}`, "error");
    }
  }

  document.addEventListener("click", e => {
    const row = e.target.closest?.("#reviewList .review-row");
    if (row) {
      focusIdx = Array.from(document.querySelectorAll("#reviewList .review-row")).indexOf(row);
      markFocus();
    }
    const v = e.target.closest?.("[data-validate]");
    if (v) { const r = v.closest(".review-row"); validateRow(r); return; }
    const u = e.target.closest?.("[data-undo]");
    if (u) { const r = u.closest(".review-row"); undoRow(r); return; }
    const o = e.target.closest?.("[data-open]");
    if (o) { openJob(o.closest(".review-row").dataset.job); return; }
  });

  $("reviewRefresh")?.addEventListener("click", loadReview);
  $("reviewThreshold")?.addEventListener("change", loadReview);
  $("reviewUndetected")?.addEventListener("change", loadReview);

  /* ─── identité et droits ───
     Au démarrage, on demande à l'API qui nous sommes. Si data/rbac.json est
     actif et qu'aucun jeton valide n'est fourni, la modale s'ouvre — plutôt
     que de découvrir un 401 au premier clic. */
  function demanderJeton() {
    $("jetonVoile")?.classList.remove("hidden");
    $("jetonInput")?.focus();
  }
  function majEnteteJeton() {
    const chip = $("identChip"), txt = $("identTxt");
    if (!chip) return;
    if (!MOI || !MOI.actif) { chip.classList.add("hidden"); return; }
    chip.classList.remove("hidden");
    txt.textContent = MOI.nom + " · " + (MOI.roles || []).join(", ");
    chip.title = "Rôles : " + (MOI.roles || []).join(", ") +
      " — périmètre : " + (MOI.dossiers || []).join(", ");
  }
  async function chargeIdentite() {
    try {
      MOI = await api("/api/rbac/moi");
    } catch (e) { MOI = { actif: false }; }
    majEnteteJeton();
    if (MOI.actif && !MOI.nom) demanderJeton();
  }
  $("jetonBtn")?.addEventListener("click", () => {
    definirJeton($("jetonInput")?.value);
    chargeIdentite().then(() => { $("jetonVoile")?.classList.add("hidden"); });
  });
  $("jetonInput")?.addEventListener("keydown", e => {
    if (e.key === "Enter") $("jetonBtn")?.click();
  });
  chargeIdentite();

  /* ---- 3. recherche plein texte inter-documents ---- */
  const gs = $("globalSearch"), sr = $("searchResults");
  let searchTimer = null;

  function closeSearch() {
    sr?.classList.add("hidden");
    gs?.setAttribute("aria-expanded", "false");
  }

  function highlight(text, q) {
    const i = text.toLowerCase().indexOf(q.toLowerCase());
    if (i < 0) return esc(text);
    return esc(text.slice(0, i)) + "<mark>" + esc(text.slice(i, i + q.length)) +
      "</mark>" + esc(text.slice(i + q.length));
  }

  async function runSearch() {
    const q = (gs.value || "").trim();
    if (q.length < 2) { closeSearch(); return; }
    sr.classList.remove("hidden");
    gs.setAttribute("aria-expanded", "true");
    sr.innerHTML = '<div class="sr-head">Recherche…</div>';
    try {
      const d = await api(`/api/search?q=${encodeURIComponent(q)}&limit=20`);
      if (!d.hits.length) {
        sr.innerHTML = '<div class="sr-head">Aucun résultat</div>' +
          '<div class="sr-item muted">Aucun document ne contient « ' + esc(q) + ' ».</div>';
        return;
      }
      const seen = new Set();
      const head = `<div class="sr-head">${d.returned} résultat${d.returned > 1 ? "s" : ""}` +
        `${d.truncated ? " (tronqué)" : ""}</div>`;
      sr.innerHTML = head + d.hits.map(h => {
        const key = h.job_id + "|" + h.kind + "|" + (h.field || h.page || "") + "|" +
          (h.value || h.snippet || "");
        if (seen.has(key)) return "";
        seen.add(key);
        const label = h.kind === "field"
          ? `Champ « ${esc(h.label || h.field)} »`
          : `Page ${h.page ?? "?"} · texte`;
        const detail = h.kind === "field" ? esc(h.value || "—") : highlight(h.snippet || "", q);
        return `<button class="sr-item" data-job="${esc(h.job_id)}" role="option">
          <span class="sr-file">${esc(h.filename)}</span>
          <span class="sr-meta">${label}${h.status ? ` · <span class="badge ${esc(h.status)}">${esc(h.status)}</span>` : ""}</span>
          <span class="sr-snip">${detail}</span>
        </button>`;
      }).join("");
    } catch (e) {
      sr.innerHTML = '<div class="sr-head">Recherche indisponible</div>' +
        '<div class="sr-item muted">API non jointe.</div>';
    }
  }

  gs?.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(runSearch, 220);
  });
  sr?.addEventListener("click", e => {
    const b = e.target.closest("[data-job]");
    if (!b) return;
    closeSearch();
    openJob(b.dataset.job);
  });
  document.addEventListener("click", e => {
    if (!e.target.closest?.(".top-search")) closeSearch();
  });

  /* ---- 4. raccourcis clavier ---- */
  const TABS = ["tab-import", "tab-docs", "tab-result", "tab-review",
                "tab-quality", "tab-config", "tab-dashboard",
                "tab-profiles", "tab-connectors", "tab-dossier", "tab-transit"];
  let gPending = false, gTimer = null;

  function typing(el) {
    return el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" ||
      el.tagName === "SELECT" || el.isContentEditable);
  }
  function gotoTab(tab) {
    document.querySelector(`.nav-item[data-tab="${tab}"]`)?.click();
  }
  function currentTab() {
    const active = document.querySelector(".nav-item.active");
    return active ? active.dataset.tab : "tab-import";
  }

  document.addEventListener("keydown", e => {
    if (typing(e.target)) {
      if (e.key === "Escape") { e.target.blur(); closeSearch(); }
      return;
    }
    if (e.metaKey || e.ctrlKey || e.altKey) return;

    const onReview = currentTab() === PAGE;
    const k = e.key;

    if (k === "Escape") {
      closeSearch();
      $("helpOverlay")?.classList.add("hidden");
      return;
    }
    if (k === "/") {
      e.preventDefault(); gs?.focus(); gs?.select(); return;
    }
    if (k === "?") {
      e.preventDefault();
      const h = $("helpOverlay");
      h?.classList.remove("hidden");
      $("helpClose")?.focus();
      return;
    }
    if (k === "t") {
      $("themeToggle")?.click(); return;
    }
    if (onReview) {
      const rows = document.querySelectorAll("#reviewList .review-row");
      if (k === "j" || k === "ArrowDown") {
        e.preventDefault(); focusIdx = Math.min(focusIdx + 1, rows.length - 1); markFocus(); return;
      }
      if (k === "k" || k === "ArrowUp") {
        e.preventDefault(); focusIdx = Math.max(focusIdx - 1, 0); markFocus(); return;
      }
      if (k === "Enter") {
        const row = rows[focusIdx];
        if (row) { e.preventDefault(); validateRow(row); }
        return;
      }
      if (k === "o") {
        const row = rows[focusIdx];
        if (row) openJob(row.dataset.job);
        return;
      }
      /* « u » annule la correction de la ligne focalisée. Le motif est
         demandé par undoRow : une annulation non motivée serait une trace
         d'audit inexpliquée. */
      if (k === "u" || k === "U") {
        const row = rows[focusIdx];
        if (row) { e.preventDefault(); undoRow(row); }
        return;
      }
    }
    if (k === "g") { gPending = true; clearTimeout(gTimer);
      gTimer = setTimeout(() => { gPending = false; }, 900); return; }
    if (gPending && /^[1-9]$/.test(k) && Number(k) - 1 < TABS.length) {
      gPending = false;
      gotoTab(TABS[Number(k) - 1]);
      return;
    }
    gPending = false;
  });

  $("helpClose")?.addEventListener("click", () => $("helpOverlay")?.classList.add("hidden"));
  $("helpOverlay")?.addEventListener("click", e => {
    if (e.target.id === "helpOverlay") e.target.classList.add("hidden");
  });

  // First-time user walkthrough
  const hasSeenWalkthrough = localStorage.getItem("unocr_walkthrough");
  if (!hasSeenWalkthrough) {
    // Show walkthrough after a short delay
    setTimeout(() => {
      $("walkthroughOverlay")?.classList.remove("hidden");
    }, 500);

    // When user dismisses, mark as seen
    $("walkthroughSkip")?.addEventListener("click", () => {
      localStorage.setItem("unocr_walkthrough", "1");
      $("walkthroughOverlay")?.classList.add("hidden");
    });
  }
})();
/* ═══════════ LOTS · AUDIT · SÉLECTION ═══════════
   Ajouts purs : aucun code métier ci-dessus n'est modifié.
   ══════════════════════════════════════════════ */
(function batchAuditSelection() {
  const $ = id => document.getElementById(id);
  const fmtSize = n => n < 1024 ? n + " o" : (n < 1048576
    ? (n / 1024).toFixed(0) + " Ko" : (n / 1048576).toFixed(1) + " Mo");

  /* ═════════ 1. traitement par lots ═════════ */
  const input = $("batchInput");
  let chosen = [];   // {file, name, size}

  function renderFiles() {
    const box = $("batchFiles");
    $("batchCount").textContent = chosen.length
      ? chosen.length + (chosen.length > 1 ? " fichiers" : " fichier")
      : "aucun fichier";
    $("batchRun").disabled = !chosen.length;
    $("batchClear").disabled = !chosen.length;
    box.innerHTML = chosen.map((f, i) =>
      `<div class="batch-file"><span class="bf-name">${esc(f.name)}</span>` +
      `<span class="bf-size">${fmtSize(f.size)}</span>` +
      `<button class="bf-rm" data-i="${i}" title="Retirer" aria-label="Retirer">✕</button></div>`
    ).join("");
  }

  $("batchPick")?.addEventListener("click", () => input?.click());
  input?.addEventListener("change", () => {
    for (const f of (input.files || [])) chosen.push({ file: f, name: f.name, size: f.size });
    input.value = "";
    renderFiles();
  });
  $("batchClear")?.addEventListener("click", () => { chosen = []; renderFiles(); });
  $("batchFiles")?.addEventListener("click", e => {
    const b = e.target.closest("[data-i]");
    if (!b) return;
    chosen.splice(Number(b.dataset.i), 1);
    renderFiles();
  });

  $("batchRun")?.addEventListener("click", async () => {
    if (!chosen.length) return;
    const btn = $("batchRun");
    btn.disabled = true;
    $("batchStatus").textContent = "envoi de " + chosen.length + " fichier(s)…";
    $("batchResult").innerHTML = "";
    try {
      const fd = new FormData();
      for (const c of chosen) fd.append("files", c.file, c.name);
      // les réglages courants de l'onglet Import sont réutilisés tels quels
      const prof = $("profileSelect")?.value || "generic";
      fd.append("profile", prof);
      fd.append("quality_mode",
        document.querySelector("#qualitySeg .on")?.dataset.mode || "accurate");
      const fmts = Array.from(
        document.querySelectorAll('#fmtChips input[data-fmt]'))
        .filter(i => i.checked).map(i => i.dataset.fmt).join(",");
      fd.append("export_formats", fmts || "json,txt");

      const d = await fetchJson("/api/batches", { method: "POST", body: fd });
      $("batchStatus").textContent = d.accepted + " accepté(s), " +
        d.rejected.length + " refusé(s)";

      // suivi de la progression réelle
      const ids = d.jobs.map(j => j.job_id);
      let done = 0;
      const poll = setInterval(async () => {
        done = 0;
        for (const j of d.jobs) {
          try {
            const st = (await fetchJson("/api/jobs/" + j.job_id)).status;
            if (st === "done" || st === "error") done++;
          } catch { /* job encore en vol */ }
        }
        $("batchStatus").textContent = `${done}/${ids.length} terminé(s)`;
        if (done >= ids.length) {
          clearInterval(poll);
          renderBatch(d);
        }
      }, 1200);

      if (!ids.length) renderBatch(d);
    } catch (e) {
      $("batchStatus").textContent = "";
      toast("Lot impossible : " + e.message, "error");
      btn.disabled = false;
    }
  });

  function renderBatch(d) {
    $("batchRun").disabled = !chosen.length;
    const rows = d.jobs.map(j =>
      `<div class="batch-row"><span class="br-file">${esc(j.filename)}</span>` +
      `<span class="badge ${esc(j.status)}">${esc(j.status)}</span>` +
      `${j.cached ? '<span class="pill">réutilisé</span>' : ""}` +
      `<button class="btn ghost sm" data-open="${esc(j.job_id)}">Ouvrir</button></div>`
    ).join("");
    const rej = d.rejected.length
      ? `<div class="batch-summary" style="border-color:var(--warn)">⚠ ${d.rejected.length} fichier(s) refusé(s) : ` +
        d.rejected.map(r => esc(r.filename)).join(", ") + "</div>"
      : "";
    const ok = d.jobs.filter(j => j.status === "done").map(j => j.job_id);
    const exp = ok.length ? `
      <div class="batch-export">
        <span class="muted mono" style="font-size:10.5px;align-self:center">Export groupé :</span>
        ${["csv", "xlsx", "json", "txt"].map(f =>
          `<button class="btn ghost sm" data-bexp="${f}">${f.toUpperCase()}</button>`).join("")}
      </div>` : "";
    $("batchResult").innerHTML =
      `<div class="batch-summary"><span><span class="bs-n">${d.jobs.length}</span>document(s)</span>` +
      `<span><span class="bs-n">${ok.length}</span>terminé(s)</span>` +
      `<span><span class="bs-n">${d.rejected.length}</span>refusé(s)</span></div>` +
      rej + `<div class="panel panel-flush" style="padding:0">${rows}</div>` + exp;
  }

  $("batchResult")?.addEventListener("click", async e => {
    const o = e.target.closest("[data-open]");
    if (o) { openJob(o.dataset.open); return; }
    const x = e.target.closest("[data-bexp]");
    if (!x) return;
    const ids = Array.from(
      $("batchResult").querySelectorAll("[data-open]")).map(b => b.dataset.open);
    if (!ids.length) return;
    const fmt = x.dataset.bexp;
    toast("Préparation de l'export groupé " + fmt.toUpperCase() + "…", "info");
    try {
      const r = await fetchAuthenticated("/api/batches/export/" + fmt + "?ids=" +
        encodeURIComponent(ids.join(",")));
      if (!r.ok) throw new Error(await readError(r));
      const blob = await r.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "unocr_lot." + fmt;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 5000);
      toast("Export groupé téléchargé ✓", "success");
    } catch (err) {
      toast("Export groupé impossible : " + err.message, "error");
    }
  });

  /* ═════════ 2. journal d'audit filtrable ═════════ */
  async function loadAudit() {
    const box = $("auditLog");
    if (!box) return;
    const ev = $("auditEvent")?.value || "";
    const q = $("auditQuery")?.value.trim() || "";
    const params = new URLSearchParams({ limit: "300" });
    if (ev) params.set("event", ev);
    if (q) params.set("q", q);
    box.innerHTML = '<div class="muted">Chargement du journal…</div>';
    try {
      const d = await fetchJson("/api/audit?" + params.toString());
      const sel = $("auditEvent");
      if (sel && sel.options.length <= 1) {
        for (const name of d.events) {
          const o = document.createElement("option");
          o.value = name; o.textContent = name;
          sel.appendChild(o);
        }
      }
      if (!d.entries.length) {
        box.innerHTML = '<div class="muted">Aucun événement pour ce filtre.</div>';
        return;
      }
      box.innerHTML = d.entries.map(e => {
        const ts = new Date(e.ts * 1000)
          .toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "medium" });
        const { ts: _t, event, ...rest } = e;
        const det = Object.entries(rest)
          .map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : v}`)
          .join(" ");
        return `<div class="audit-entry"><span class="ae-ts">${ts}</span>` +
          `<span class="ae-ev">${esc(event)}</span>` +
          `<span class="ae-det">${esc(det)}</span></div>`;
      }).join("");
    } catch (err) {
      box.innerHTML = '<div class="muted">Journal indisponible — API non jointe.</div>';
    }
  }
  $("auditRefresh")?.addEventListener("click", loadAudit);
  $("auditEvent")?.addEventListener("change", loadAudit);
  let auditTimer = null;
  $("auditQuery")?.addEventListener("input", () => {
    clearTimeout(auditTimer);
    auditTimer = setTimeout(loadAudit, 250);
  });
  // chargé quand on affiche le tableau de bord
  document.querySelector('.nav-item[data-tab="tab-dashboard"]')
    ?.addEventListener("click", () => setTimeout(loadAudit, 60));

  /* ═════════ 3. sélection de champs → export ciblé ═════════ */
  const tbody = document.querySelector("#fieldsTable tbody");
  if (tbody && window.MutationObserver) {
    new MutationObserver(() => {
      for (const tr of tbody.querySelectorAll("tr")) {
        if (tr.querySelector(":scope > td.sel-cell")) continue;
        const td = document.createElement("td");
        td.className = "sel-cell";
        td.innerHTML = '<input type="checkbox" class="sel-cb" aria-label="Sélectionner ce champ">';
        tr.insertBefore(td, tr.firstChild);
      }
      syncSel();
    }).observe(tbody, { childList: true });
  }

  function selected() {
    return Array.from(document.querySelectorAll("#fieldsTable .sel-cb"))
      .filter(cb => cb.checked)
      .map(cb => cb.closest("tr").querySelector(".mono")?.textContent?.trim())
      .filter(Boolean);
  }
  function syncSel() {
    const n = selected().length;
    if ($("selCount")) $("selCount").textContent = n + (n > 1 ? " champs" : " champ");
    if ($("exportSelCsv")) $("exportSelCsv").disabled = !n;
    if ($("exportSelJson")) $("exportSelJson").disabled = !n;
  }
  document.addEventListener("change", e => {
    if (e.target.classList?.contains("sel-cb")) syncSel();
    if (e.target.id === "selAll") {
      const on = e.target.checked;
      document.querySelectorAll("#fieldsTable .sel-cb").forEach(cb => { cb.checked = on; });
      syncSel();
    }
  });
  async function exportSelection(fmt) {
    const names = selected();
    if (!names.length || !currentJob) return;
    toast("Export de " + names.length + " champ(s)…", "info");
    try {
      const r = await fetchAuthenticated(`/api/jobs/${currentJob}/export/${fmt}/selected?fields=` +
        encodeURIComponent(names.join(",")));
      if (!r.ok) throw new Error(await readError(r));
      const blob = await r.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "unocr_selection." + fmt;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 5000);
      toast("Sélection exportée ✓", "success");
    } catch (err) {
      toast("Export impossible : " + err.message, "error");
    }
  }
  $("exportSelCsv")?.addEventListener("click", () => exportSelection("csv"));
  $("exportSelJson")?.addEventListener("click", () => exportSelection("json"));
})();

/* ═══════════ ÉDITEUR DE PROFILS ═══════════
   Ajout pur. Les profils utilisateur sont écrits dans data/profiles/ :
   les profils livrés ne sont jamais modifiés.
   ═══════════════════════════════════════ */
(function profileEditor() {
  const $ = id => document.getElementById(id);
  const META = window.PAGE_META || (window.PAGE_META = {});
  META["tab-profiles"] = ["Profils métier", "Champs, motifs et validateurs — avec essai à blanc"];

  let all = [];            // [{name, label, description, fields, source}]
  let current = null;      // profil en cours d'édition
  let catalog = { normalizations: [], validators: [], aux_validators: [] };

  /* ── chargement ── */
  async function loadList() {
    try {
      const [list, cat] = await Promise.all([
        fetchJson("/api/profiles"), fetchJson("/api/profiles/catalog")]);
      catalog = cat;
      all = list;
      const sel = $("profName")?.value;
      $("profList").innerHTML = list.map(p =>
        `<button class="prof-item${current && current.name === p.name ? " on" : ""}" ` +
        `data-name="${esc(p.name)}"><span class="pi-name">${esc(p.label || p.name)}</span>` +
        `<span class="pi-src">${p.name}</span></button>`).join("");
      if (sel) $("profName").value = sel;
    } catch (e) {
      $("profList").innerHTML = '<div class="muted">Profils indisponibles.</div>';
    }
  }

  async function openProfile(name) {
    try {
      const p = await fetchJson("/api/profiles/" + encodeURIComponent(name));
      current = p;
      $("profEmpty").style.display = "none";
      $("profForm").style.display = "";
      $("profSource").textContent = p.source === "user" ? "Utilisateur" : "Livré";
      $("profName").value = p.name;
      $("profLabel").value = p.label || "";
      $("profDesc").value = p.description || "";
      $("profDelete").disabled = p.source !== "user";
      $("profDelete").title = p.source === "user"
        ? "Supprimer ce profil utilisateur"
        : "Profil livré avec le projet — non supprimable";
      renderFields(p.fields || []);
      $("profTestOut").innerHTML = "";
      loadList();
    } catch (e) {
      toast("Profil inaccessible : " + e.message, "error");
    }
  }

  function renderFields(fields) {
    $("profFields").innerHTML = fields.map((f, i) => `
      <div class="prof-field" data-i="${i}">
        <div class="prof-field-head">
          <span class="pf-key">${esc(f.key || "(sans clé)")}</span>
          ${f.required ? '<span class="pill">requis</span>' : ""}
          <button class="pf-rm" data-rm="${i}" title="Retirer ce champ">✕ retirer</button>
        </div>
        <div class="prof-field-grid">
          <div><label class="lb">Clé</label>
            <input class="inp" data-f="key" value="${esc(f.key || "")}" placeholder="invoice_number"></div>
          <div><label class="lb">Libellé</label>
            <input class="inp" data-f="label" value="${esc(f.label || "")}" placeholder="Numéro de facture"></div>
          <div><label class="lb">Normalisation</label>
            <select class="inp" data-f="normalize">
              <option value="">aucune</option>
              ${catalog.normalizations.map(n =>
                `<option value="${esc(n)}"${f.normalize === n ? " selected" : ""}>${esc(n)}</option>`).join("")}
            </select></div>
          <div><label class="lb">Validateurs</label>
            <select class="inp" data-f="validator">
              <option value="">aucun</option>
              ${catalog.validators.map(v =>
                `<option value="${esc(v)}"${(f.validators || [])[0] === v ? " selected" : ""}>${esc(v)}</option>`).join("")}
            </select></div>
        </div>
        <div style="margin-top:10px">
          <label class="lb">Motifs (regex, un par ligne — le groupe 1 est la valeur)</label>
          <textarea class="inp" rows="2" data-f="patterns"
            style="font-family:var(--font-mono);font-size:11px">${esc((f.patterns || []).join("\n"))}</textarea>
        </div>
        <label class="ph-check" style="margin-top:8px">
          <input type="checkbox" data-f="required"${f.required ? " checked" : ""}>
          <span>Champ requis</span>
        </label>
      </div>`).join("");
  }

  function collectFields() {
    return Array.from($("profFields").querySelectorAll(".prof-field")).map(box => {
      const get = k => box.querySelector(`[data-f="${k}"]`);
      const validators = [];
      const v = get("validator")?.value;
      if (v) validators.push(v);
      return {
        key: (get("key")?.value || "").trim(),
        label: get("label")?.value || "",
        patterns: (get("patterns")?.value || "").split("\n")
          .map(x => x.trim()).filter(Boolean),
        normalize: get("normalize")?.value || null,
        validators,
        required: !!get("required")?.checked,
        category: "general",
      };
    }).filter(f => f.key);
  }

  /* ── interactions ── */
  $("profList")?.addEventListener("click", e => {
    const b = e.target.closest("[data-name]");
    if (b) openProfile(b.dataset.name);
  });
  $("profNew")?.addEventListener("click", () => {
    current = { name: "", label: "", description: "", fields: [], source: "user" };
    $("profEmpty").style.display = "none";
    $("profForm").style.display = "";
    $("profSource").textContent = "Nouveau";
    $("profName").value = "";
    $("profLabel").value = "";
    $("profDesc").value = "";
    $("profDelete").disabled = true;
    renderFields([]);
    $("profTestOut").innerHTML = "";
    $("profName").focus();
  });
  $("profAddField")?.addEventListener("click", () => {
    const fields = collectFields();
    fields.push({ key: "", label: "", patterns: [], normalize: null,
                  validators: [], required: false, category: "general" });
    renderFields(fields);
  });
  $("profFields")?.addEventListener("click", e => {
    const rm = e.target.closest("[data-rm]");
    if (!rm) return;
    const fields = collectFields();
    fields.splice(Number(rm.dataset.rm), 1);
    renderFields(fields);
  });

  $("profSave")?.addEventListener("click", async () => {
    const name = ($("profName").value || "").trim();
    if (!name) { toast("Donnez un identifiant au profil.", "error"); return; }
    const body = {
      label: $("profLabel").value || name,
      description: $("profDesc").value || "",
      fields: collectFields(),
    };
    if (!body.fields.length) {
      toast("Un profil sans champ n'extraira rien.", "error");
      return;
    }
    $("profMsg").textContent = "enregistrement…";
    try {
      const r = await fetchJson("/api/profiles/" + encodeURIComponent(name),
        { method: "PUT", body: JSON.stringify(body),
          headers: { "Content-Type": "application/json" } });
      $("profMsg").textContent = `enregistré (${r.fields} champs)` +
        (r.overrides_builtin ? " — remplace un profil livré" : "");
      toast(`Profil « ${name} » enregistré`, "success");
      openProfile(name);
    } catch (e) {
      $("profMsg").textContent = "";
      toast("Enregistrement refusé : " + e.message, "error");
    }
  });

  $("profDelete")?.addEventListener("click", async () => {
    const name = $("profName").value;
    if (!name || !confirm(`Supprimer le profil « ${name} » de data/profiles/ ?`)) return;
    try {
      await fetchJson("/api/profiles/" + encodeURIComponent(name), { method: "DELETE" });
      toast("Profil supprimé", "info");
      current = null;
      $("profForm").style.display = "none";
      $("profEmpty").style.display = "";
      loadList();
    } catch (e) {
      toast("Suppression impossible : " + e.message, "error");
    }
  });

  $("profRunTest")?.addEventListener("click", async () => {
    const body = {
      profile: {
        name: $("profName").value || "essai",
        label: $("profLabel").value || "Essai",
        fields: collectFields(),
      },
      text: $("profTestText").value || "",
      job_id: $("profTestJob").value.trim() || undefined,
    };
    if (!body.profile.fields.length) {
      toast("Ajoutez au moins un champ à essayer.", "error"); return;
    }
    $("profTestOut").innerHTML = '<div class="muted">Essai en cours…</div>';
    try {
      const r = await fetchJson("/api/profiles/test",
        { method: "POST", body: JSON.stringify(body),
          headers: { "Content-Type": "application/json" } });
      const rows = Object.entries(r.fields).map(([k, f]) => {
        const conf = Math.round((f.confidence || 0) * 100);
        return `<div class="prof-test-row">
          <span class="ptr-key">${esc(k)}</span>
          <span class="ptr-val">${f.raw_value ? esc(f.raw_value) : '<span class="muted">non détecté</span>'}</span>
          <span class="badge ${esc(f.status)}">${esc(f.status)}</span>
          <span class="muted mono" style="font-size:10px">${conf}%</span>
        </div>`;
      }).join("");
      $("profTestOut").innerHTML =
        `<div class="prof-test-summary">${r.detected}/${r.total} champ(s) détecté(s)</div>` + rows;
    } catch (e) {
      $("profTestOut").innerHTML =
        '<div class="empty">Essai impossible : ' + esc(e.message) + "</div>";
    }
  });

  document.querySelector('.nav-item[data-tab="tab-profiles"]')
    ?.addEventListener("click", () => { if (!all.length) loadList(); });
})();



