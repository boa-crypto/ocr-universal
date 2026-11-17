/* Dossiers métier de quarantaine. Écritures explicites, jamais de publication. */
(function () {
  'use strict';
  function mount(parent, lot, active) {
    var root=document.createElement('fieldset');root.dataset.assessment='';
    var legend=document.createElement('legend');legend.textContent='Dossier de proposition tarifaire — non validé juridiquement';root.append(legend);parent.append(root);
    function node(tag,text){var n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;}
    function input(name,label,tag){var l=node('label',label),i=node(tag||'input');i.dataset.field=name;i.dir='auto';l.append(i);root.append(l);return i;}
    function button(name,label,action){var b=node('button',label);b.type='button';b.dataset.action=name;b.addEventListener('click',action);root.append(b);return b;}
    function token(){try{return sessionStorage.getItem('uniocr_token')||'';}catch(e){return '';}}
    var initialToken=token(),sequence=0,busy=false,documentState=null,uncertain=false,revoked=false,historical=false,readingFile=false,piecesDirty=false,draftPieces=[],selectedClaim=null;
    var id=input('id','Identifiant du dossier');id.maxLength=64;
    var fields={};['designation','matiere','fonction','usage','caracteristiques'].forEach(function(k){fields[k]=input(k,k);fields[k].maxLength=256;});
    var state=input('statut','Transition de revue','select');['en_revue','a_completer','proposition_humaine','rejetee'].forEach(function(k){var o=node('option',k);o.value=k;state.append(o);});
    var motivation=input('justification','Justification déclarée','textarea');motivation.maxLength=4000;
    var code=input('code','Candidat proposé (jamais automatique)','select');
    var rgi=input('rgi','Raisonnement RGI déclaré, à vérifier','textarea');rgi.maxLength=4000;
    var notes=input('notes','Notes et exclusions déclarées, à vérifier','textarea');notes.maxLength=4000;
    var versionInput=input('version_lecture','Version historique (facultative)');versionInput.type='number';versionInput.min='1';versionInput.max='100';
    var pieceArea=node('fieldset');pieceArea.append(node('legend','Pièces techniques textuelles déclarées — non vérifiées'));
    var pieceFields={};
    ['piece_id','nom','nature','critere','localisateur_declare','texte'].forEach(function(k){
      var l=node('label',k),i=node(k==='texte'?'textarea':k==='nature'||k==='critere'?'select':'input');i.dataset.pieceField=k;i.dir='auto';l.append(i);pieceArea.append(l);pieceFields[k]=i;
    });
    pieceFields.piece_id.maxLength=64;pieceFields.nom.maxLength=128;pieceFields.localisateur_declare.maxLength=256;pieceFields.texte.maxLength=16384;
    ['fiche_technique','notice','attestation','declaration','autre'].forEach(function(k){var o=node('option',k);o.value=k;pieceFields.nature.append(o);});
    Object.keys(fields).forEach(function(k){var o=node('option',k);o.value=k;pieceFields.critere.append(o);});
    var fileLabel=node('label','Importer un texte UTF8 .txt (32 Kio maximum, sans enregistrement automatique)'),fileInput=node('input');fileInput.type='file';fileInput.accept='.txt,text/plain';fileLabel.append(fileInput);pieceArea.append(fileLabel);
    var claimLabel=node('label','Valeur attribuée humainement à une sélection du texte (facultative)'),claimValue=node('input');claimValue.maxLength=256;claimValue.dataset.pieceField='valeur_declaree';claimLabel.append(claimValue);pieceArea.append(claimLabel);
    var citeSelection=node('button','Associer la sélection du texte au critère déclaré');citeSelection.type='button';citeSelection.dataset.action='cite-selection';pieceArea.append(citeSelection);
    function clearClaim(){selectedClaim=null;}
    pieceFields.texte.addEventListener('input',clearClaim);pieceFields.critere.addEventListener('change',clearClaim);claimValue.addEventListener('input',clearClaim);
    citeSelection.addEventListener('click',function(){
      if(!current()||busy||readingFile||piecesLocked())return;
      var text=pieceFields.texte.value,a=pieceFields.texte.selectionStart,b=pieceFields.texte.selectionEnd,citation=text.slice(a,b);
      if(!citation || Array.from(citation).length>4096 || !claimValue.value.trim()){status.textContent='Sélectionner un extrait (4096 points Unicode maximum) et déclarer une valeur.';return;}
      selectedClaim={critere:pieceFields.critere.value,valeur_declaree:claimValue.value,debut:Array.from(text.slice(0,a)).length,fin:Array.from(text.slice(0,b)).length,citation:citation};
      status.textContent='Citation sélectionnée localement. Son exactitude textuelle sera vérifiée ; sa portée technique ne sera pas certifiée.';
    });
    var addPiece=node('button','Ajouter cette pièce au brouillon local');addPiece.type='button';addPiece.dataset.action='add-piece';pieceArea.append(addPiece);
    var pieceList=node('div');root.append(pieceArea,pieceList);
    function piecePayload(p){var r={};['piece_id','nom','nature','criteres_declares','localisateur_declare','texte','declarations_attributs'].forEach(function(k){r[k]=p[k];});return r;}
    function piecesLocked(){return historical || (documentState && ['proposition_humaine','rejetee'].includes(documentState.statut));}
    function drawPieces(){
      pieceList.replaceChildren();pieceList.append(node('p','Pièces déclarées, jamais authentifiées ; elles ne remplissent pas automatiquement les caractéristiques produit.'));
      draftPieces.forEach(function(p,index){
        var box=node('div');box.append(node('pre',JSON.stringify(p,null,2)));
        var remove=node('button','Retirer du brouillon local : '+p.piece_id);remove.type='button';remove.dataset.removePiece=p.piece_id;remove.disabled=Boolean(piecesLocked());
        remove.addEventListener('click',function(){if(busy||readingFile||!current()||piecesLocked())return;draftPieces.splice(index,1);piecesDirty=true;drawPieces();});box.append(remove);pieceList.append(box);
      });
    }
    addPiece.addEventListener('click',function(){
      if(busy||readingFile||!current()||piecesLocked())return;
      var p={piece_id:pieceFields.piece_id.value,nom:pieceFields.nom.value,nature:pieceFields.nature.value,criteres_declares:[pieceFields.critere.value],localisateur_declare:pieceFields.localisateur_declare.value,texte:pieceFields.texte.value,declarations_attributs:selectedClaim?[selectedClaim]:[]};
      if(draftPieces.length>=5 || !/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(p.piece_id) || draftPieces.some(function(v){return v.piece_id===p.piece_id;}) || !p.nom.trim() || !p.localisateur_declare.trim() || !p.texte.trim()){
        status.textContent='Identifiant unique, nom, localisateur et texte requis ; cinq pièces maximum.';return;
      }
      draftPieces.push(p);selectedClaim=null;claimValue.value='';piecesDirty=true;drawPieces();status.textContent='Pièce ajoutée localement. Créer ou réviser explicitement pour sauvegarder.';
    });
    fileInput.addEventListener('change',async function(){
      if(busy||readingFile||!current()||piecesLocked())return;
      var f=fileInput.files && fileInput.files[0];if(!f)return;
      var context=sequence,identity=id.value,selection=lot.value;
      if(f.size>32768 || !/\.txt$/i.test(f.name)){status.textContent='Seul un texte UTF8 .txt de 32 Kio maximum est accepté.';fileInput.value='';return;}
      readingFile=true;update();
      try{
        var bytes=await f.arrayBuffer(),text=new TextDecoder('utf-8',{fatal:true}).decode(bytes);
        if(!current()||context!==sequence||identity!==id.value||selection!==lot.value)return;
        if(text.length>16384 || !text.trim() || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]/.test(text))throw Error('Texte vide, trop long ou contrôle interdit.');
        selectedClaim=null;claimValue.value='';pieceFields.nom.value=f.name;pieceFields.texte.value=text;status.textContent='Texte lu localement ; renseigner son identifiant et son localisateur puis l’ajouter explicitement.';
      }catch(e){if(current()&&context===sequence)status.textContent='Import refusé : UTF8 strict, sans contrôle interdit, 16384 caractères maximum.';}
      finally{readingFile=false;fileInput.value='';if(current())update();}
    });
    var status=node('p','Aucune décision juridique ou publication possible.');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
    var comparisonView=node('pre');comparisonView.dir='auto';comparisonView.dataset.comparison='';
    var result=node('pre');result.dir='auto';var candidates=node('div'),history=node('pre');history.dir='auto';
    function current(){return !revoked && root.isConnected && active() && initialToken===token();}
    function validId(){return /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(id.value);}
    function product(){var p={};Object.keys(fields).forEach(function(k){p[k]=fields[k].value||null;});p.designation=fields.designation.value;return p;}
    function reset(){sequence++;documentState=null;uncertain=false;historical=false;draftPieces=[];selectedClaim=null;claimValue.value='';piecesDirty=false;versionInput.value='';Object.values(pieceFields).forEach(function(i){if(i.tagName!=='SELECT')i.value='';});fileInput.value='';drawPieces();id.value='';Object.values(fields).forEach(function(i){i.value='';});motivation.value=rgi.value=notes.value='';code.replaceChildren();result.textContent=history.textContent=comparisonView.textContent='';candidates.replaceChildren();status.textContent='Dossier à charger ou à créer. Aucune publication.';update();}
    function update(){root.disabled=busy || readingFile || !lot.selectedOptions.length || lot.selectedOptions[0].dataset.lotType!=="tarif";save.disabled=busy||readingFile||historical||!documentState||uncertain;create.disabled=busy||readingFile||historical||uncertain;pieceArea.disabled=Boolean(piecesLocked());compare.disabled=busy||readingFile||!documentState||uncertain;}
    function validate(data,expectedId,expectedLot){
      if(!data || data.publication_active!==false || data.validation_juridique!=='non_validee' || data.perimetre!=='revue_administrative_quarantaine')throw Error('Réponse de dossier non conforme.');
      var d=data.resultat;
      if(!d || (d.pieces_techniques!==undefined && (!Array.isArray(d.pieces_techniques)||d.pieces_techniques.length>5)) || d.id!==expectedId || d.lot_id!==expectedLot || d.publication_active!==false || d.validation_juridique!=='non_validee' || !Number.isInteger(d.version) || d.version<1 || d.version>100 || !/^[a-f0-9]{64}$/.test(d.manifest_sha256) || !['brouillon','en_revue','a_completer','proposition_humaine','rejetee'].includes(d.statut) || !d.diagnostic || !d.diagnostic.recherche || !Array.isArray(d.diagnostic.recherche.resultats) || d.diagnostic.classement_ia_effectue!==false)throw Error('Réponse de dossier non conforme.');
      return d;
    }
    function render(d){
      comparisonView.textContent='';documentState=d;draftPieces=(d.pieces_techniques||[]).map(function(p){return JSON.parse(JSON.stringify(p));});piecesDirty=false;selectedClaim=null;claimValue.value='';Object.values(pieceFields).forEach(function(i){if(i.tagName!=='SELECT')i.value='';});drawPieces();Object.keys(fields).forEach(function(k){fields[k].value=d.diagnostic.produit_declare[k]||'';});
      result.textContent='Version '+d.version+' — '+d.statut+' — acteur serveur : '+d.acteur+'\n'+JSON.stringify(d.diagnostic.questions_a_documenter,null,2);
      if(d.diagnostic.abstention_documentaire)result.textContent+='\nAbstention : aucune piste documentaire, pas absence de droit.';
      code.replaceChildren();var empty=node('option','Choisir explicitement');empty.value='';code.append(empty);
      candidates.replaceChildren();candidates.append(node('p','Comparaison documentaire, pas pertinence juridique, attributs certifiés ou probabilités.'));
      d.diagnostic.recherche.resultats.forEach(function(c){
        if(!c.ligne || !/^[0-9]{10}$/.test(c.ligne.code_tarifaire_10))return;
        var o=node('option',c.ligne.code_tarifaire_10);o.value=c.ligne.code_tarifaire_10;code.append(o);
        candidates.append(node('p',c.ligne.code_tarifaire_10+' — '+(c.ligne.designation_officielle_fr||'')+' — '+(c.ligne.designation_officielle_ar||'')+'\nRéférence déclarée : '+JSON.stringify(c.ligne.reference)+'\nCorrespondances littérales : '+JSON.stringify(c.correspondances_par_critere)+'\nExtraits reçus : '+JSON.stringify(c.extraits_correspondants||[])+'\nTermes non retrouvés : '+JSON.stringify(c.termes_non_retrouves_par_critere)));
      });
      history.textContent=JSON.stringify(d.historique||[],null,2);
    }
    async function request(method,payload,readVersion,comparisonOnly){
      if(!current()){documentState=null;root.replaceChildren();return;}
      if(busy||readingFile)return;
      if(!validId()){status.textContent='Identifiant simple de 1 à 64 caractères requis.';return;}
      var selection=lot.value,identity=id.value,number=++sequence,definiteRejection=false;
      busy=true;update();status.textContent='Traitement en cours…';
      try{
        var headers={Accept:'application/json'};if(initialToken)headers.Authorization='Bearer '+initialToken;
        if(payload)headers['Content-Type']='application/json';
        var path='/api/v1/customs-review/lots/'+encodeURIComponent(selection)+'/assessments'+(method==='POST'?'':'/'+encodeURIComponent(identity))+(comparisonOnly?'/comparison':'')+(readVersion?'?version='+readVersion:'');
        var response=await fetch(path,{method:method,headers:headers,body:payload?JSON.stringify(payload):undefined,credentials:'same-origin',cache:'no-store'});
        if(!current() || sequence!==number || lot.value!==selection || id.value!==identity)return;
        if(!response.ok){
          definiteRejection=response.status>=400 && response.status<500 && response.status!==409;
          if(!definiteRejection)uncertain=true;
          if(response.status===401 || response.status===403){revoked=true;documentState=null;result.textContent=history.textContent=comparisonView.textContent='';candidates.replaceChildren();}
          throw Error(response.status===503?'Audit ou service indisponible : sauvegarde possible. Relire ce dossier après rétablissement, ne pas rejouer.':response.status===409?'Conflit ou identifiant existant : relire avant modification.':'Demande refusée ('+response.status+'). Aucun classement validé.');
        }
        var data=await response.json();if(!current()||sequence!==number||lot.value!==selection||id.value!==identity)return;
        if(data.lecture_seule!==(method==='GET'))throw Error('Mode de réponse incohérent.');
        if(comparisonOnly){
          var c=data.resultat;
          if(data.publication_active!==false || data.validation_juridique!=='non_validee' || data.perimetre!=='revue_administrative_quarantaine' || !c || c.type_rapport!=='comparaison_declarations_et_pistes_non_validee' || c.dossier_id!==identity || c.lot_id!==selection || c.version!==readVersion || !documentState || c.manifest_sha256!==documentState.manifest_sha256 || !/^[a-f0-9]{64}$/.test(c.sha256_dossier) || c.attributs_techniques_certifies!==false || c.contradiction_semantique_etablie!==false || c.classement_ia_effectue!==false || c.candidat_retenu_automatiquement!==false || c.taux_calcules!==false || c.politique_comparaison!=='egalite_exacte_sans_normalisation_traduction_ou_synonymes' || !Array.isArray(c.questions_a_arbitrer) || c.questions_a_arbitrer.length>15 || c.publication_active!==false || c.validation_juridique!=='non_validee' || !Array.isArray(c.criteres) || c.criteres.length!==5 || c.criteres.map(function(x){return x.critere;}).join(',')!==Object.keys(fields).join(',') || !Array.isArray(c.candidats) || c.candidats.length>20)throw Error('Comparaison non conforme.');
          comparisonView.textContent='Comparaison de la version enregistrée '+c.version+' ; pas du brouillon local. Aucune inférence technique.\n'+JSON.stringify(c,null,2);
          status.textContent='Comparaison documentaire en lecture seule ; valeurs différentes à examiner, pas contradiction prouvée.';return;
        }
        var checked=validate(data,identity,selection);if(readVersion&&checked.version!==readVersion)throw Error('Version historique incohérente.');
        historical=Boolean(readVersion);render(checked);uncertain=false;
        status.textContent='Dossier enregistré/lu — proposition non validée, non publiée. Version '+documentState.version+(historical?' — version historique, lecture seule.':'');
      }catch(e){
        if(!current()||sequence!==number)return;
        if(!definiteRejection){uncertain=true;documentState=null;result.textContent=history.textContent=comparisonView.textContent='';candidates.replaceChildren();code.replaceChildren();}
        status.textContent=e.message && !/fetch|network/i.test(e.message)?e.message:'Connexion interrompue : état incertain, relire avant toute nouvelle écriture.';
      }finally{busy=false;if(!current()){documentState=null;root.replaceChildren();}else update();}
    }
    var create=button('create','Créer le brouillon',function(){if(!uncertain && fields.designation.value.trim())request('POST',{dossier_id:id.value,produit:product(),pieces_techniques:draftPieces.map(piecePayload)});});
    button('load','Charger / réconcilier le dossier',function(){request('GET');});
    button('load-version','Lire la version historique',function(){var v=Number(versionInput.value);if(!Number.isInteger(v)||v<1||v>100){status.textContent='Version de 1 à 100 requise.';return;}request('GET',undefined,v);});
    var compare=button('compare','Comparer les déclarations de la version enregistrée',function(){if(documentState&&!uncertain)request('GET',undefined,documentState.version,true);});
    var save=button('save','Enregistrer une révision explicite',function(){
      if(historical||!documentState||uncertain||motivation.value.trim().length<10)return;
      var p={version_attendue:documentState.version,statut:state.value,justification:motivation.value};
      if(!['proposition_humaine','rejetee'].includes(documentState.statut)){p.produit=product();if(piecesDirty)p.pieces_techniques=draftPieces.map(piecePayload);}
      if(state.value==='proposition_humaine'){
        var c=documentState.diagnostic.recherche.resultats.find(function(v){return v.ligne.code_tarifaire_10===code.value;});
        if(!c || rgi.value.trim().length<10 || notes.value.trim().length<10){status.textContent='Choix explicite, raisonnement RGI et notes/exclusions requis.';return;}
        p.code_propose=code.value;p.raisonnement_rgi=rgi.value;p.notes_exclusions=notes.value;p.references=[c.ligne.reference];
      }
      request('PATCH',p);
    });
    root.append(status,result,candidates,history,comparisonView);lot.addEventListener('change',reset);
    id.addEventListener('input',function(){documentState=null;historical=false;uncertain=true;result.textContent=history.textContent=comparisonView.textContent='';candidates.replaceChildren();save.disabled=true;});
    // Un nouvel identifiant permet la création, jamais la réutilisation d'une révision chargée.
    id.addEventListener('change',function(){uncertain=false;update();});
    drawPieces();update();
    return {reset:reset};
  }
  window.UniOCRCustomsAssessments=Object.freeze({mount:mount});
})();
