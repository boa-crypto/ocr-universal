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
    var initialToken=token(),sequence=0,busy=false,documentState=null,uncertain=false,revoked=false;
    var id=input('id','Identifiant du dossier');id.maxLength=64;
    var fields={};['designation','matiere','fonction','usage','caracteristiques'].forEach(function(k){fields[k]=input(k,k);fields[k].maxLength=256;});
    var state=input('statut','Transition de revue','select');['en_revue','a_completer','proposition_humaine','rejetee'].forEach(function(k){var o=node('option',k);o.value=k;state.append(o);});
    var motivation=input('justification','Justification déclarée','textarea');motivation.maxLength=4000;
    var code=input('code','Candidat proposé (jamais automatique)','select');
    var rgi=input('rgi','Raisonnement RGI déclaré, à vérifier','textarea');rgi.maxLength=4000;
    var notes=input('notes','Notes et exclusions déclarées, à vérifier','textarea');notes.maxLength=4000;
    var status=node('p','Aucune décision juridique ou publication possible.');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
    var result=node('pre');result.dir='auto';var candidates=node('div'),history=node('pre');history.dir='auto';
    function current(){return !revoked && root.isConnected && active() && initialToken===token();}
    function validId(){return /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(id.value);}
    function product(){var p={};Object.keys(fields).forEach(function(k){p[k]=fields[k].value||null;});p.designation=fields.designation.value;return p;}
    function reset(){sequence++;documentState=null;uncertain=false;id.value='';Object.values(fields).forEach(function(i){i.value='';});motivation.value=rgi.value=notes.value='';code.replaceChildren();result.textContent=history.textContent='';candidates.replaceChildren();status.textContent='Dossier à charger ou à créer. Aucune publication.';update();}
    function update(){root.disabled=busy || !lot.selectedOptions.length || lot.selectedOptions[0].dataset.lotType!=="tarif";save.disabled=busy||!documentState||uncertain;create.disabled=busy||uncertain;}
    function validate(data,expectedId,expectedLot){
      if(!data || data.publication_active!==false || data.validation_juridique!=='non_validee' || data.perimetre!=='revue_administrative_quarantaine')throw Error('Réponse de dossier non conforme.');
      var d=data.resultat;
      if(!d || d.id!==expectedId || d.lot_id!==expectedLot || d.publication_active!==false || d.validation_juridique!=='non_validee' || !Number.isInteger(d.version) || d.version<1 || d.version>100 || !/^[a-f0-9]{64}$/.test(d.manifest_sha256) || !['brouillon','en_revue','a_completer','proposition_humaine','rejetee'].includes(d.statut) || !d.diagnostic || !d.diagnostic.recherche || !Array.isArray(d.diagnostic.recherche.resultats) || d.diagnostic.classement_ia_effectue!==false)throw Error('Réponse de dossier non conforme.');
      return d;
    }
    function render(d){
      documentState=d;Object.keys(fields).forEach(function(k){fields[k].value=d.diagnostic.produit_declare[k]||'';});
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
    async function request(method,payload){
      if(!current()){documentState=null;root.replaceChildren();return;}
      if(busy)return;
      if(!validId()){status.textContent='Identifiant simple de 1 à 64 caractères requis.';return;}
      var selection=lot.value,identity=id.value,number=++sequence,definiteRejection=false;
      busy=true;update();status.textContent='Traitement en cours…';
      try{
        var headers={Accept:'application/json'};if(initialToken)headers.Authorization='Bearer '+initialToken;
        if(payload)headers['Content-Type']='application/json';
        var path='/api/v1/customs-review/lots/'+encodeURIComponent(selection)+'/assessments'+(method==='POST'?'':'/'+encodeURIComponent(identity));
        var response=await fetch(path,{method:method,headers:headers,body:payload?JSON.stringify(payload):undefined,credentials:'same-origin',cache:'no-store'});
        if(!current() || sequence!==number || lot.value!==selection || id.value!==identity)return;
        if(!response.ok){
          definiteRejection=response.status>=400 && response.status<500 && response.status!==409;
          if(!definiteRejection)uncertain=true;
          if(response.status===401 || response.status===403){revoked=true;documentState=null;result.textContent=history.textContent='';candidates.replaceChildren();}
          throw Error(response.status===503?'Audit ou service indisponible : sauvegarde possible. Relire ce dossier après rétablissement, ne pas rejouer.':response.status===409?'Conflit ou identifiant existant : relire avant modification.':'Demande refusée ('+response.status+'). Aucun classement validé.');
        }
        var data=await response.json();if(!current()||sequence!==number||lot.value!==selection||id.value!==identity)return;
        if(data.lecture_seule!==(method==='GET'))throw Error('Mode de réponse incohérent.');
        render(validate(data,identity,selection));uncertain=false;
        status.textContent='Dossier enregistré/lu — proposition non validée, non publiée. Version '+documentState.version;
      }catch(e){
        if(!current()||sequence!==number)return;
        if(!definiteRejection){uncertain=true;documentState=null;result.textContent=history.textContent='';candidates.replaceChildren();code.replaceChildren();}
        status.textContent=e.message && !/fetch|network/i.test(e.message)?e.message:'Connexion interrompue : état incertain, relire avant toute nouvelle écriture.';
      }finally{busy=false;if(!current()){documentState=null;root.replaceChildren();}else update();}
    }
    var create=button('create','Créer le brouillon',function(){if(!uncertain && fields.designation.value.trim())request('POST',{dossier_id:id.value,produit:product()});});
    button('load','Charger / réconcilier le dossier',function(){request('GET');});
    var save=button('save','Enregistrer une révision explicite',function(){
      if(!documentState||uncertain||motivation.value.trim().length<10)return;
      var p={version_attendue:documentState.version,statut:state.value,justification:motivation.value};
      if(!['proposition_humaine','rejetee'].includes(documentState.statut))p.produit=product();
      if(state.value==='proposition_humaine'){
        var c=documentState.diagnostic.recherche.resultats.find(function(v){return v.ligne.code_tarifaire_10===code.value;});
        if(!c || rgi.value.trim().length<10 || notes.value.trim().length<10){status.textContent='Choix explicite, raisonnement RGI et notes/exclusions requis.';return;}
        p.code_propose=code.value;p.raisonnement_rgi=rgi.value;p.notes_exclusions=notes.value;p.references=[c.ligne.reference];
      }
      request('PATCH',p);
    });
    root.append(status,result,candidates,history);lot.addEventListener('change',reset);
    id.addEventListener('input',function(){documentState=null;uncertain=true;result.textContent=history.textContent='';candidates.replaceChildren();save.disabled=true;});
    // Un nouvel identifiant permet la création, jamais la réutilisation d'une révision chargée.
    id.addEventListener('change',function(){uncertain=false;update();});
    update();
    return {reset:reset};
  }
  window.UniOCRCustomsAssessments=Object.freeze({mount:mount});
})();
