/* Recherche explicite dans des pages natives indexées, pas dans des articles validés. */
(function(){
  'use strict';
  function mount(parent,lot,active){
    function node(tag,text){var n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;}
    function token(){try{return sessionStorage.getItem('uniocr_token')||'';}catch(e){return '';}}
    var initialToken=token(),seq=0,busy=false,revoked=false;
    var root=node('fieldset'),legend=node('legend','Rechercher dans les pages PDF reçues — non validées'),label=node('label','Termes littéraux (même page)'),q=node('input'),docLabel=node('label','ID du document exact (facultatif)'),doc=node('input'),button=node('button','Rechercher les pages'),next=node('button','Pages de résultats suivantes'),status=node('p'),output=node('pre');
    q.maxLength=doc.maxLength=256;q.dir=doc.dir=output.dir='auto';button.type=next.type='button';status.setAttribute('role','status');label.append(q);docLabel.append(doc);root.append(legend,label,docLabel,button,next,status,output);parent.append(root);
    var offset=null,lastQuery=null;
    function current(){return !revoked&&root.isConnected&&active()&&token()===initialToken;}
    function update(){root.disabled=busy||!lot.selectedOptions.length||lot.selectedOptions[0].dataset.lotType!=='code';next.disabled=busy||offset===null;}
    function clear(){seq++;offset=null;lastQuery=null;output.textContent='';status.textContent='Recherche documentaire uniquement, sans correction du texte ni droit à date.';update();}
    lot.addEventListener('change',function(){q.value=doc.value='';clear();});
    [q,doc].forEach(function(i){i.addEventListener('input',clear);});
    async function search(start){
      if(!current()){root.replaceChildren();return;}
      if(busy||!q.value.trim())return;
      var number=++seq,selection=lot.value,query=q.value,documentId=doc.value;
      busy=true;update();output.textContent='';status.textContent='Recherche…';
      try{
        var params=new URLSearchParams({q:query,limit:'20',offset:String(start)});if(documentId)params.set('document_id',documentId);
        var headers={Accept:'application/json'};if(initialToken)headers.Authorization='Bearer '+initialToken;
        var response=await fetch('/api/v1/customs-review/lots/'+encodeURIComponent(selection)+'/pdf-search?'+params,{headers:headers,method:'GET',credentials:'same-origin',cache:'no-store'});
        if(!current()||number!==seq||lot.value!==selection)return;
        if(!response.ok){if(response.status===401||response.status===403){revoked=true;root.replaceChildren();return;}throw Error(response.status===409?'Index absent, non épinglé ou incohérent ; aucune recherche dégradée automatique.':'Recherche refusée ('+response.status+').');}
        var data=await response.json();if(!current()||number!==seq)return;
        var r=data.resultat;
        if(data.lecture_seule!==true||data.publication_active!==false||data.validation_juridique!=='non_validee'||data.perimetre!=='revue_administrative_quarantaine'||!r||r.type_recherche!=='pages_pdf_natives'||r.lot_id!==selection||r.requete!==query||r.decalage!==start||r.limite!==20||r.publication_active!==false||r.validation_juridique!=='non_validee'||r.ocr_effectue!==false||r.articles_localises_automatiquement!==false||!r.archive||!/^[a-f0-9]{64}$/.test(r.archive.manifest_sha256)||!/^[a-f0-9]{64}$/.test(r.index_sha256)||!Array.isArray(r.resultats)||r.resultats.length>20||!Number.isInteger(r.total_correspondances)||r.total_correspondances<r.resultats.length||!(r.decalage_suivant===null||(Number.isInteger(r.decalage_suivant)&&r.decalage_suivant===start+r.resultats.length&&r.decalage_suivant>start)))throw Error('Réponse documentaire non conforme.');
        offset=r.decalage_suivant;lastQuery={q:query,doc:documentId};output.textContent=JSON.stringify(r,null,2);status.textContent=r.total_correspondances+' page(s) correspondante(s), pas articles validés ni occurrences. Aucun résultat ne prouve une absence de droit.';
      }catch(e){if(current()&&number===seq){offset=null;lastQuery=null;output.textContent='';status.textContent=e.message||'Connexion interrompue.';}}
      finally{busy=false;if(!current())root.replaceChildren();else update();}
    }
    button.addEventListener('click',function(){search(0);});next.addEventListener('click',function(){if(offset!==null&&lastQuery&&lastQuery.q===q.value&&lastQuery.doc===doc.value)search(offset);});clear();
  }
  window.UniOCRCustomsLegalPages=Object.freeze({mount:mount});
})();
