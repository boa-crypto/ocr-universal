content = '''<!-- ─────────── 01 · IMPORT ─────────── -->
      <section id="tab-import" class="page" role="region" aria-labelledby="import-page-title">
        <header class="page-header">
          <div class="page-header__meta">
            <span class="label label-badge label-badge-brand">01 — Atelier · Capture</span>
          </div>
          <h1 id="import-page-title" class="display-2" data-i18n="h.import">Importez. Vérifiez. Exportez.</h1>
          <p class="lead" data-i18n="h.import.desc">Traitez vos documents localement, examinez les valeurs extraites et gardez leur provenance à portée de main.</p>
          <div class="page-header__stats flex flex-wrap gap-4 mt-4">
            <div class="stat">
              <span class="stat-label">Moteurs actifs</span>
              <span class="stat-value stat-value-sm" id="homeEngines">—</span>
            </div>
            <div class="stat">
              <span class="stat-label">Activité mesurée</span>
              <span class="stat-value stat-value-sm" id="homeStats">—</span>
            </div>
          </div>
        </header>

        <div class="grid grid-cols-1 grid-cols-lg-12 gap-6 gap-lg-8 mt-6">
          <!-- Main Content Area -->
          <div class="col-span-1 col-span-lg-7">
            <!-- Drop Zone Instrument -->
            <div class="card card-elevated p-6" id="dropZoneContainer">
              <div class="file-dropzone" id="dropZone" role="button" tabindex="0" aria-label="Zone d'importation de documents" aria-describedby="dropZoneHint">
                <input type="file" id="fileInput" class="file-input" hidden
                       accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,.docx,.odt,.txt,.rtf,.csv,.xlsx,.xls"
                       aria-label="Sélectionner un fichier">
                <div class="file-dropzone__icon">
                  <svg class="icon icon-2xl icon-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                    <path d="M7 18a4 4 0 01-.9-7.9 5.5 5.5 0 0110.6-1.4A4.5 4.5 0 0117.5 18H7z" stroke-linejoin="round"/>
                    <path d="M12 13v5m0-5l-2 2m2-2l2 2" stroke-linecap="round"/>
                  </svg>
                </div>
                <h3 class="h4 mb-2">Glissez votre document dans l'instrument</h3>
                <p id="dropZoneHint" class="caption text-secondary">ou cliquez pour parcourir · 50 Mo max · traitement 100 % local</p>
                <div class="file-dropzone__filename mt-3" id="dropName" aria-live="polite"></div>
              </div>

              <!-- Camera Button Row -->
              <div class="flex flex-wrap items-center gap-3 mt-4 pt-4 border-t border-border">
                <button type="button" class="btn btn-ghost btn-sm icon-btn icon-btn-md" id="cameraBtn" aria-label="Prendre une photo avec la caméra">
                  <svg class="icon icon-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                    <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/>
                    <circle cx="12" cy="13" r="4"/>
                  </svg>
                  <span class="hidden sm:inline">Prendre une photo</span>
                </button>
                <span class="caption text-tertiary">conteneur · plaque · carte grise — via la caméra</span>
                <input type="file" id="cameraInput" accept="image/*" capture="environment" hidden aria-label="Capture caméra">
              </div>

              <!-- Selected File Info (shown when file selected) -->
              <div class="file-dropzone__selected hidden flex items-center justify-between gap-3 p-3 bg-bg-hover rounded-lg mt-4" id="selectedFileInfo" aria-live="polite">
                <div class="flex items-center gap-3 min-w-0 flex-1">
                  <span class="document-avatar document-avatar-lg" id="selectedFileIcon" aria-hidden="true">PDF</span>
                  <div class="min-w-0">
                    <p class="body-sm font-medium truncate" id="selectedFileName"></p>
                    <p class="caption text-tertiary" id="selectedFileSize"></p>
                  </div>
                </div>
                <button type="button" class="btn btn-ghost btn-sm btn-icon" id="clearBtn" aria-label="Retirer le fichier sélectionné">
                  <svg class="icon icon-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <path d="M18 6L6 18M6 6l12 12"/>
                  </svg>
                </button>
              </div>
            </div>

            <!-- Primary Actions -->
            <div class="flex flex-wrap items-center gap-3 mt-4" role="group" aria-label="Actions principales">
              <button type="button" class="btn btn-primary btn-lg" id="uploadBtn" disabled>
                <span>Lancer l'analyse</span>
                <svg class="icon icon-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true">
                  <path d="M5 12h14M12 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </button>
              <span class="caption text-tertiary flex-1 min-w-[200px]" id="uploadStatus" role="status" aria-live="polite" aria-atomic="true"></span>
            </div>

            <!-- Recent Documents Panel -->
            <div class="card card-elevated mt-6">
              <div class="card-header border-b border-border p-4">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <span class="label label-badge label-badge-neutral">01.b</span>
                    <h2 class="h4">Derniers documents</h2>
                  </div>
                </div>
              </div>
              <div class="card-body p-4" id="homeRecent">
                <div class="empty-state flex flex-col items-center justify-center py-12 text-center">
                  <svg class="icon icon-2xl icon-muted mb-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                    <polyline points="10 9 9 9 8 9"/>
                  </svg>
                  <p class="body text-secondary">Aucun document traité pour l'instant</p>
                  <p class="caption text-tertiary mt-1">L'historique apparaîtra ici après vos premiers traitements</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Sidebar: Settings -->
          <aside class="col-span-1 col-span-lg-5 space-y-6" aria-labelledby="settings-heading">
            <!-- Profile & Quality Settings -->
            <div class="card card-elevated p-5">
              <header class="card-header mb-4">
                <div class="flex items-center gap-3">
                  <span class="label label-badge label-badge-brand">Profil</span>
                  <h2 id="settings-heading" class="h4">Réglages d'analyse</h2>
                </div>
              </header>

              <div class="space-y-5">
                <!-- Profile Selector -->
                <div class="field">
                  <label class="label" for="profileSelect">Profil métier</label>
                  <select class="select select-md" id="profileSelect" aria-describedby="profileHint">
                    <option value="generic">Profil générique</option>
                  </select>
                  <p class="field-hint" id="profileHint"></p>
                </div>

                <!-- Quality Mode (Segmented Control) -->
                <div class="field">
                  <label class="label">Mode qualité</label>
                  <div class="segmented" id="qualitySeg" role="radiogroup" aria-label="Mode qualité">
                    <button type="button" role="radio" class="btn btn-sm" data-qm="fast" aria-pressed="false">
                      <svg class="icon icon-sm mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
                      Fast
                    </button>
                    <button type="button" role="radio" class="btn btn-sm on" data-qm="accurate" aria-pressed="true">
                      <svg class="icon icon-sm mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                      Accurate
                    </button>
                  </div>
                  <p class="field-hint" id="qmHint">Accurate compare les variantes et garde la meilleure.</p>
                </div>

                <!-- Language Chips -->
                <div class="field">
                  <label class="label">Langues (aucune sélection = auto-détection)</label>
                  <div class="flex flex-wrap gap-2" id="langChips" role="group" aria-label="Sélection des langues">
                    <span class="caption text-tertiary">chargement des modèles installés…</span>
                  </div>
                </div>

                <!-- Advanced Options Accordion -->
                <details class="accordion" id="advPanel">
                  <summary class="accordion-trigger flex items-center justify-between cursor-pointer p-2 rounded-lg hover:bg-bg-hover transition-colors">
                    <div class="flex items-center gap-2">
                      <svg class="icon icon-md icon-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                        <circle cx="12" cy="12" r="3"/>
                        <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9L7 7M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/>
                      </svg>
                      <span class="body-medium">Options avancées</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <span class="badge badge-sm badge-brand" id="advCount">11 réglages</span>
                      <svg class="icon icon-sm icon-muted accordion-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                        <polyline points="6 9 12 15 18 9"/>
                      </svg>
                    </div>
                  </summary>
                  <div class="accordion-content pt-4 space-y-5" role="region">
                    <!-- Row 1: Preprocess + DPI -->
                    <div class="grid grid-cols-1 gap-4">
                      <div class="field">
                        <label class="label" for="preprocessMode">Prétraitement</label>
                        <select class="select select-md" id="preprocessMode">
                          <option value="standard">standard — qualité détectée</option>
                          <option value="aggressive">agressif — scans dégradés</option>
                          <option value="off">désactivé — image brute</option>
                        </select>
                      </div>
                      <div class="field">
                        <label class="label" for="renderDpi">Résolution (PDF)</label>
                        <select class="select select-md" id="renderDpi">
                          <option value="150">150 DPI — rapide</option>
                          <option value="200" selected>200 DPI — recommandé</option>
                          <option value="300">300 DPI — fin</option>
                          <option value="400">400 DPI — maximum</option>
                        </select>
                      </div>
                    </div>

                    <!-- Row 2: Engine + Page Range -->
                    <div class="grid grid-cols-1 gap-4">
                      <div class="field">
                        <label class="label" for="engineSelect">Moteur OCR</label>
                        <select class="select select-md" id="engineSelect">
                          <option value="auto">auto — sélection + consensus</option>
                          <option value="indra">indra OCR (ONNX, multilingue)</option>
                          <option value="tesseract">tesseract uniquement</option>
                          <option value="native">couche texte native (PDF)</option>
                        </select>
                      </div>
                      <div class="field">
                        <label class="label" for="pageRange">Pages à traiter</label>
                        <input type="text" class="input input-md" id="pageRange" placeholder="toutes — ex. 1-3, 5" aria-describedby="pageRangeHint">
                        <p class="field-hint" id="pageRangeHint">Laisser vide pour traiter toutes les pages</p>
                      </div>
                    </div>

                    <!-- Review Threshold Slider -->
                    <div class="field">
                      <div class="flex items-center justify-between mb-1">
                        <label class="label mb-0" for="reviewRange">Seuil de revue humaine</label>
                        <span class="badge badge-sm badge-neutral font-mono" id="reviewVal">70 %</span>
                      </div>
                      <div class="slider-wrapper">
                        <input type="range" class="slider" id="reviewRange" min="50" max="95" step="5" value="70" aria-describedby="reviewRangeHint">
                        <span class="slider-value" aria-hidden="true">70%</span>
                      </div>
                      <p class="field-hint" id="reviewRangeHint">En dessous de ce score, les champs sont signalés dans l'onglet Qualité.</p>
                    </div>

                    <!-- Extraction Modules (Switches) -->
                    <div class="field">
                      <label class="label">Modules d'extraction</label>
                      <div class="flex flex-col gap-3" role="group" aria-label="Modules d'extraction">
                        <label class="switch-wrapper">
                          <input type="checkbox" class="switch" id="exFields" checked aria-label="Champs & profils">
                          <span class="switch-label body-sm">Champs & profils</span>
                        </label>
                        <label class="switch-wrapper">
                          <input type="checkbox" class="switch" id="exTables" checked aria-label="Tableaux">
                          <span class="switch-label body-sm">Tableaux</span>
                        </label>
                        <label class="switch-wrapper">
                          <input type="checkbox" class="switch" id="exBarcodes" checked aria-label="Codes-barres">
                          <span class="switch-label body-sm">Codes-barres</span>
                        </label>
                        <label class="switch-wrapper">
                          <input type="checkbox" class="switch" id="variantCmp" checked aria-label="Variantes">
                          <span class="switch-label body-sm">Variantes</span>
                        </label>
                      </div>
                    </div>

                    <!-- Export Formats (Pills with checkboxes) -->
                    <div class="field">
                      <label class="label">Exports générés en fin de traitement</label>
                      <div class="flex flex-wrap gap-2" id="fmtChips" role="group" aria-label="Formats d'export">
                        <label class="pill pill-brand cursor-pointer">
                          <input type="checkbox" data-fmt="json" checked hidden aria-label="JSON"> 🧬 JSON
                        </label>
                        <label class="pill pill-brand cursor-pointer">
                          <input type="checkbox" data-fmt="txt" checked hidden aria-label="TXT"> 📄 TXT
                        </label>
                        <label class="pill pill-brand cursor-pointer">
                          <input type="checkbox" data-fmt="csv" checked hidden aria-label="CSV"> 📑 CSV
                        </label>
                        <label class="pill pill-brand cursor-pointer">
                          <input type="checkbox" data-fmt="xlsx" checked hidden aria-label="XLSX"> 📊 XLSX
                        </label>
                        <label class="pill pill-brand cursor-pointer">
                          <input type="checkbox" data-fmt="xml" checked hidden aria-label="XML"> 🔮 XML
                        </label>
                        <label class="pill pill-brand cursor-pointer">
                          <input type="checkbox" data-fmt="pdf" checked hidden aria-label="PDF"> 📕 PDF
                        </label>
                      </div>
                      <p class="field-hint">Les formats non cochés restent téléchargeables à la demande depuis l'onglet Résultat.</p>
                    </div>
                  </div>
                </details>
              </div>
            </div>

            <!-- Live Pipeline -->
            <div class="card card-elevated p-5">
              <header class="card-header mb-4">
                <div class="flex items-center gap-3">
                  <span class="status-dot status-dot-processing" aria-hidden="true"></span>
                  <h2 class="h4">Pipeline en direct</h2>
                </div>
              </header>

              <div class="space-y-4">
                <!-- Progress Bar -->
                <div class="field">
                  <div class="flex items-center justify-between mb-2">
                    <span class="label">Progression</span>
                    <span class="badge badge-sm badge-brand" id="progressPercent">0 %</span>
                  </div>
                  <div class="progress" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" aria-label="Progression du traitement">
                    <div class="progress-bar" id="progressBar" style="width: 0%"></div>
                  </div>
                </div>

                <!-- Pipeline Steps -->
                <nav class="pipeline-steps" id="pipelineSteps" aria-label="Étapes du pipeline">
                  <ol class="list list-divided" role="list">
                    <li class="step step-pending" data-stage="ingest">
                      <div class="step-marker">
                        <span class="step-index">01</span>
                        <span class="step-dot" aria-hidden="true"></span>
                      </div>
                      <div class="step-content">
                        <span class="step-title body-sm font-medium">Ingestion & sécurité</span>
                        <span class="caption text-tertiary">Validation, hash, détection type</span>
                      </div>
                    </li>
                    <li class="step step-pending" data-stage="ocr">
                      <div class="step-marker">
                        <span class="step-index">02</span>
                        <span class="step-dot" aria-hidden="true"></span>
                      </div>
                      <div class="step-content">
                        <span class="step-title body-sm font-medium">OCR & langues</span>
                        <span class="caption text-tertiary">Reconnaissance, détection langues</span>
                      </div>
                    </li>
                    <li class="step step-pending" data-stage="tables">
                      <div class="step-marker">
                        <span class="step-index">03</span>
                        <span class="step-dot" aria-hidden="true"></span>
                      </div>
                      <div class="step-content">
                        <span class="step-title body-sm font-medium">Tableaux & structure</span>
                        <span class="caption text-tertiary">Détection, reconstruction</span>
                      </div>
                    </li>
                    <li class="step step-pending" data-stage="fields">
                      <div class="step-marker">
                        <span class="step-index">04</span>
                        <span class="step-dot" aria-hidden="true"></span>
                      </div>
                      <div class="step-content">
                        <span class="step-title body-sm font-medium">Champs métier</span>
                        <span class="caption text-tertiary">Extraction, profils, validation</span>
                      </div>
                    </li>
                    <li class="step step-pending" data-stage="quality">
                      <div class="step-marker">
                        <span class="step-index">05</span>
                        <span class="step-dot" aria-hidden="true"></span>
                      </div>
                      <div class="step-content">
                        <span class="step-title body-sm font-medium">Contrôle qualité</span>
                        <span class="caption text-tertiary">Scores, anomalies, seuils</span>
                      </div>
                    </li>
                    <li class="step step-pending" data-stage="done">
                      <div class="step-marker">
                        <span class="step-index">06</span>
                        <span class="step-dot" aria-hidden="true"></span>
                      </div>
                      <div class="step-content">
                        <span class="step-title body-sm font-medium">Terminé</span>
                        <span class="caption text-tertiary">Exports, indexation, notification</span>
                      </div>
                    </li>
                  </ol>
                </nav>

                <!-- Process Log -->
                <div class="field">
                  <label class="label" id="logLabel">Journal du traitement</label>
                  <div class="log-box p-3 font-mono text-sm" id="processLog" role="log" aria-live="polite" aria-labelledby="logLabel" style="min-height: 120px; max-height: 200px; overflow-y: auto;">
                    <div class="text-tertiary">En attente d'un document…</div>
                  </div>
                </div>

                <!-- Export Links (shown after completion) -->
                <div class="flex flex-wrap gap-2" id="exportLinks" role="group" aria-label="Exports disponibles"></div>
              </div>
            </div>
          </aside>
        </div>

        <!-- Batch Processing Section -->
        <div class="card card-elevated mt-8">
          <header class="card-header p-5 border-b border-border">
            <div class="flex items-center gap-3 mb-2">
              <span class="label label-badge label-badge-info">Lots</span>
              <h2 class="h4">Traitement par lots</h2>
            </div>
            <p class="caption text-tertiary max-w-3xl">
              Déposez plusieurs documents d'un coup. Un fichier déjà traité n'est pas recalculé — son résultat existant est réutilisé. Les fichiers refusés (format ou taille) sont écartés et signalés, sans faire échouer le lot.
            </p>
          </header>

          <div class="card-body p-5 space-y-5">
            <!-- Batch File Selection -->
            <div class="file-input-wrapper">
              <input type="file" class="file-input" id="batchInput" multiple
                     accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,.docx,.odt,.txt,.rtf,.csv,.xlsx,.xls"
                     aria-label="Choisir des documents pour le lot">
              <div class="file-input-button flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div class="flex items-center gap-3">
                  <svg class="icon icon-lg icon-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                  </svg>
                  <div>
                    <p class="body-medium font-medium">Choisir des documents</p>
                    <p class="caption text-tertiary">PDF, images, Office, textes · 50 Mo max par fichier</p>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <span class="caption text-tertiary mono" id="batchCount">aucun fichier</span>
                  <button type="button" class="btn btn-ghost btn-sm" id="batchClear" disabled aria-label="Vider la sélection">Vider</button>
                </div>
              </div>
              <div class="file-input-preview" id="batchFiles" role="list" aria-label="Fichiers sélectionnés"></div>
            </div>

            <!-- Batch Actions -->
            <div class="flex flex-wrap items-center gap-3 pt-4 border-t border-border">
              <button type="button" class="btn btn-primary" id="batchRun" disabled>
                <svg class="icon icon-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true">
                  <path d="M5 12h14M12 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                Lancer le traitement
              </button>
              <span class="caption text-tertiary mono" id="batchStatus"></span>
            </div>

            <!-- Batch Results -->
            <div id="batchResult" role="region" aria-label="Résultats du lot"></div>
          </div>
        </div>
      </section>'''

with open('import_refactored.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("File written successfully")