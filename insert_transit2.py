import sys

with open('web/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The tab-connectors section starts at line 780 (index 779)
insert_idx = 779

transit_section = """      <!-- ─────────── 10 · PARCOURS DOCUMENTAIRE ─────────── -->
      <section id="tab-transit" class="page hidden">
        <header class="page-head">
          <div class="page-index">11 — Transit · Gestion maritime</div>
          <h1 class="display" data-i18n="h.transit">Transit <em>maritime</em></h1>
          <p class="lede">Gestion des dossiers d'importation maritime, OCR et contrôle documentaire.</p>
        </header>

        <div class="hero-grid" style="grid-template-columns:1fr 1fr">
          <div class="col-main">
            <div class="panel">
              <div class="panel-head"><span class="idx">Tableau de bord</span>
                <h3 class="sec-title">Vue d'ensemble</h3>
              </div>
              <div class="stat-row">
                <div class="stat">
                  <span class="lbl">Dossiers actifs</span>
                  <div class="v grad-text" id="transitTotal">0</div>
                </div>
                <div class="stat">
                  <span class="lbl">En cours</span>
                  <div class="v" id="transitEnCours">0</div>
                </div>
                <div class="stat">
                  <span class="lbl">Terminés</span>
                  <div class="v" id="transitTermines">0</div>
                </div>
                <div class="stat">
                  <span class="lbl">Erreurs</span>
                  <div class="v" id="transitErreurs">0</div>
                </div>
              </div>
            </div>

            <div class="panel" style="margin-top:26px">
              <div class="panel-head"><span class="idx">Dossiers récents</span>
                <h3 class="sec-title">Derniers dossiers</h3>
              </div>
              <div id="transitDossiersRecent" class="logbox">
                <div class="muted">Aucun dossier chargé.</div>
              </div>
            </div>
          </div>

          <div class="col-side">
            <div class="panel">
              <div class="panel-head"><span class="idx">Créer un dossier</span>
                <h3 class="sec-title">Nouveau dossier de transit</h3>
              </div>
              <div class="panel">
                <div class="panel-head">
                  <span class="idx">Référence</span>
                  <h3 class="sec-title" style="font-size:19px">Nouveau dossier</h3>
                </div>
                <div class="prof-meta">
                  <label class="lb" for="transitRef">Référence</label>
                  <input class="inp" id="transitRef" placeholder="TR-2026-000001" aria-label="Référence du dossier">
                  <label class="lb" for="transitClient">Client importateur</label>
                  <input class="inp" id="transitClient" placeholder="Client" aria-label="Client importateur">
                </div>
                <div class="prof-actions">
                  <button class="btn" id="transitCreer">Créer</button>
                  <span class="muted mono" id="transitMsg" style="font-size:10.5px"></span>
                </div>
              </div>

              <div class="panel" style="margin-top:26px">
                <div class="panel-head"><span class="idx">OCR rapide</span>
                  <h3 class="sec-title">Analyse documentaire</h3>
                </p>
                  <p class="muted" style="font-size:12px;margin:0 0 12px;max-width:70ch">Glissez un document ou sélectionnez-le pour analyse OCR.</p>
                <div class="adv" id="advPanelOcr" style="margin-top:18px">
                  <div class="adv-head" id="advToggleOcr">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9L7 7M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/></svg>
                    Options avancées
                    <span class="pill" id="advCountOcr" style="margin-left:8px">5 réglages</span>
                    <span class="chev">▾</span>
                  </div>
                  <div class="adv-body">
                    <div class="field-row">
                      <div>
                        <label class="lb" for="preprocessModeOcr">Prétraitement</label>
                        <select class="inp" id="preprocessModeOcr">
                          <option value="standard">standard — qualité détectée</option>
                          <option value="aggressive">agressif — scans dégradés</option>
                          <option value="off">désactivé — image brute</option>
                        </select>
                      </div>
                      <div>
                        <label class="lb" for="engineSelectOcr">Moteur OCR</label>
                        <select class="inp" id="engineSelectOcr">
                          <option value="auto">auto — sélection + consensus</option>
                          <option value="indra">indra OCR (ONNX, multilingue)</option>
                          <option value="tesseract">tesseract uniquement</option>
                          <option value="native">couche texte native (PDF)</option>
                        </select>
                      </div>
                    </div>
                    <div class="field-row">
                      <div>
                        <label class="lb" for="pageRangeOcr">Pages à traiter</label>
                        <input class="inp" type="text" id="pageRangeOcr" placeholder="toutes — ex. 1-3, 5">
                      </div>
                      <div>
                        <label class="lb" for="reviewRangeOcr">Seuil de revue humaine</label>
                        <div class="range-row">
                          <input type="range" id="reviewRangeOcr" min="50" max="95" step="5" value="70">
                          <div class="range-val" id="reviewValOcr">70 %</div>
                        </div>
                        <div class="muted" style="font-size:10.5px;margin-top:5px">En dessous de ce score, les champs sont signalés dans l'onglet Qualité.</div>
                      </div>
                    </div>

                    <label class="lb">Modules d'extraction</label>
                    <div class="toggles">
                      <label class="mini-switch"><input type="checkbox" id="exFieldsOcr" checked><span class="track"></span><span class="lbl">Champs & profils</span></label>
                      <label class="mini-switch"><input type="checkbox" id="exTablesOcr" checked><span class="track"></span><span class="lbl">Tableaux</span></label>
                      <label class="mini-switch"><input type="checkbox" id="exBarcodesOcr" checked><span class="track"></span><span class="lbl">Codes-barres</span></label>
                      <label class="mini-switch"><input type="checkbox" id="variantCmpOcr" checked><span class="track"></span><span class="lbl">Variantes</span></label>
                    </div>

                    <label class="lb">Exports générés en fin de traitement</label>
                    <div class="fmt-chips" id="fmtChipsOcr">
                      <label class="langchip on"><input type="checkbox" data-fmt="json" checked hidden>🧬 JSON</label>
                      <label class="langchip on"><input type="checkbox" data-fmt="txt" checked hidden>📄 TXT</label>
                      <label class="langchip on"><input type="checkbox" data-fmt="csv" checked hidden>📑 CSV</label>
                      <label class="langchip on"><input type="checkbox" data-fmt="xlsx" checked hidden>📊 XLSX</label>
                      <label class="langchip on"><input type="checkbox" data-fmt="xml" checked hidden>🔮 XML</label>
                      <label class="langchip on"><input type="checkbox" data-fmt="pdf" checked hidden>📕 PDF</label>
                    </div>
                    <div class="muted" style="font-size:10.5px;margin-top:5px">Les formats non cochés restent téléchargeables à la demande depuis l'onglet Résultat.</div>
                  </div>

                <button class="btn" id="transitAnalyser">Lancer l'analyse OCR</button>
                <span class="muted mono" id="transitStatutOcr" style="font-size:11px"></span>
              </div>
            </div>

          <div class="col-side">
            <div class="panel">
              <div class="panel-head"><span class="idx">Aperçu documentaire</span>
                <h3 class="sec-title">Document source</h3>
              </div>
              <div id="transitApercu" class="empty">Sélectionnez un document pour affichage</div>
            </div>

            <div class="panel" style="margin-top:26px">
              <div class="panel-head"><span class="idx">Anomalies</span>
                <h3 class="sec-title">Détections OCR</h3>
              </div>
              <div id="transitAnomalies" class="empty">Aucune analyse effectuée</div>
            </div>

            <div class="panel" style="margin-top:26px">
              <div class="panel-head"><span class="idx">Consigne</span>
                <h3 class="sec-title">Prochaines actions</h3>
              </div>
              <div id="transitActions" class="empty">
                <p>Aucune action requise pour l'instant.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ─────────── 10 · PARCOURS DOCUMENTAIRE ─────────── -->
      <section id="tab-connectors" class="page hidden">"""

# Insert at the exact position
new_lines = lines[:779] + [transit_section] + lines[779:]

with open('web/index.html', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Done')