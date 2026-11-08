/* Recherche explicite dans des pages natives indexées, pas dans des articles validés. */
(function(){
  'use strict';
  function mount(parent,lot,active){
    function node(tag,text){var n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;}
    function token(){try{return sessionStorage.getItem('uniocr_token')||'';}catch(e){return '';}}
    var initialToken=token(),seq=0,busy=false,revoked=false;
    var root=node('fieldset'),legend=node('legend','Rechercher dans les pages PDF reçues — non validées'),label=node('label','Termes littéraux (même page)'),q=node('input'),docLabel=node('label','ID du document exact (facultatif)'),doc=node('input'),button=node('button','Rechercher les pages'),next=node('button','Pages de résultats suivantes'),status=node('p'),output=node('pre');
    q.maxLength=doc.maxLength=256;q.dir=doc.dir=output.dir='auto';button.type=next.type='button';status.setAttribute('role','status');label.append(q);docLabel.append(doc);root.append(legend,label,docLabel,button,next,status,output);parent.append(root);
    var modeLabel=node('label','Mode de consultation'),mode=node('select');mode.dataset.pdfMode='';['texte','reperes'].forEach(function(k){var o=node('option',k==='texte'?'Recherche de texte':'Repères d’articles candidats');o.value=k;mode.append(o);});modeLabel.append(mode);root.insertBefore(modeLabel,button);
    var navigation=node('div'),pageView=node('pre');pageView.dir='auto';pageView.dataset.indexPage='';root.append(navigation,pageView);
    var offset=null,lastQuery=null;
    mode.addEventListener('change',function(){q.value='';q.maxLength=mode.value==='texte'?256:32;label.firstChild.textContent=mode.value==='texte'?'Termes littéraux (même page)':'Numéro littéral exact (facultatif, pas article validé)';clear();});
    function current(){return !revoked&&root.isConnected&&active()&&token()===initialToken;}
    function update(){root.disabled=busy||!lot.selectedOptions.length||lot.selectedOptions[0].dataset.lotType!=='code';next.disabled=busy||offset===null;}
    function clear(){seq++;offset=null;lastQuery=null;output.textContent='';navigation.replaceChildren();pageView.textContent='';status.textContent='Recherche documentaire uniquement, sans correction du texte ni droit à date.';update();}
    lot.addEventListener('change',function(){q.value=doc.value='';clear();});
    [q,doc].forEach(function(i){i.addEventListener('input',clear);});
    async function search(start){
      if(!current()){root.replaceChildren();return;}
      if(busy||(mode.value==='texte'&&!q.value.trim()))return;
      var number=++seq,selection=lot.value,query=q.value,documentId=doc.value,kind=mode.value;
      busy=true;update();output.textContent='';navigation.replaceChildren();pageView.textContent='';status.textContent='Recherche…';
      try{
        var params=new URLSearchParams({limit:'20',offset:String(start)});if(kind==='texte')params.set('q',query);else if(query)params.set('numero',query);if(documentId)params.set('document_id',documentId);
        var headers={Accept:'application/json'};if(initialToken)headers.Authorization='Bearer '+initialToken;
        var response=await fetch('/api/v1/customs-review/lots/'+encodeURIComponent(selection)+(kind==='texte'?'/pdf-search?':'/pdf-article-markers?')+params,{headers:headers,method:'GET',credentials:'same-origin',cache:'no-store'});
        if(!current()||number!==seq||lot.value!==selection)return;
        if(!response.ok){if(response.status===401||response.status===403){revoked=true;root.replaceChildren();return;}throw Error(response.status===409?'Index absent, non épinglé ou incohérent ; aucune recherche dégradée automatique.':'Recherche refusée ('+response.status+').');}
        var data=await response.json();if(!current()||number!==seq)return;
        var r=data.resultat;
        if(data.lecture_seule!==true||data.publication_active!==false||data.validation_juridique!=='non_validee'||data.perimetre!=='revue_administrative_quarantaine'||!r||r.type_recherche!==(kind==='texte'?'pages_pdf_natives':'reperes_articles_pdf')||r.lot_id!==selection||r.requete!==query||r.decalage!==start||r.limite!==20||r.publication_active!==false||r.validation_juridique!=='non_validee'||r.classement_douanier_valide!==false||r.restitution_juridique_a_date!==false||r.ocr_effectue!==false||r.articles_localises_automatiquement!==false||(kind==='reperes'&&r.reperes_detectes_automatiquement!==true)||!r.archive||!/^[a-f0-9]{64}$/.test(r.archive.manifest_sha256)||!/^[a-f0-9]{64}$/.test(r.index_sha256)||!Array.isArray(r.resultats)||r.resultats.length>20||!Number.isInteger(r.total_correspondances)||r.total_correspondances<r.resultats.length||!(r.decalage_suivant===null||(Number.isInteger(r.decalage_suivant)&&r.decalage_suivant===start+r.resultats.length&&r.decalage_suivant>start)))throw Error('Réponse documentaire non conforme.');
        if(start>0&&(!lastQuery||lastQuery.index!==r.index_sha256||lastQuery.manifest!==r.archive.manifest_sha256))throw Error('Index changé pendant la pagination ; relancer la recherche.');
        offset=r.decalage_suivant;lastQuery={q:query,doc:documentId,kind:kind,index:r.index_sha256,manifest:r.archive.manifest_sha256};output.textContent=JSON.stringify(r,null,2);status.textContent=r.total_correspondances+(kind==='texte'?' page(s) correspondante(s)':' repère(s) candidat(s)')+', pas articles validés ni occurrences juridiquement qualifiées. Aucun résultat ne prouve une absence de droit.';
        r.resultats.forEach(function(item){
          if(typeof item.document_id!=='string'||!Number.isInteger(item.page_pdf)||item.page_pdf<1||!/^[a-f0-9]{64}$/.test(item.pdf_sha256)||!/^[a-f0-9]{64}$/.test(item.sha256_texte_utf8))return;
          var b=node('button','Lire la page '+item.page_pdf+' — '+(item.numero_litteral||item.document_id));b.type='button';b.dataset.readIndexPage='';b.addEventListener('click',function(){readPage(item,r,selection);});navigation.append(b);
        });
      }catch(e){if(current()&&number===seq){offset=null;lastQuery=null;output.textContent='';status.textContent=e.message||'Connexion interrompue.';}}
      finally{busy=false;if(!current())root.replaceChildren();else update();}
    }
    async function readPage(item,origin,selection){
      if(!current()){root.replaceChildren();return;}if(busy||lot.value!==selection)return;
      var number=++seq,start=Number.isInteger(item.debut)?Math.max(0,item.debut-200):0;
      busy=true;update();pageView.textContent='';
      try{
        var params=new URLSearchParams({document_id:item.document_id,page:String(item.page_pdf),offset:String(start),limit:'4000'}),headers={Accept:'application/json'};if(initialToken)headers.Authorization='Bearer '+initialToken;
        var response=await fetch('/api/v1/customs-review/lots/'+encodeURIComponent(selection)+'/pdf-index-page?'+params,{headers:headers,method:'GET',credentials:'same-origin',cache:'no-store'});
        if(!current()||number!==seq||lot.value!==selection)return;
        if(!response.ok){if(response.status===401||response.status===403){revoked=true;root.replaceChildren();return;}throw Error('Lecture de page refusée ('+response.status+').');}
        var data=await response.json();if(!current()||number!==seq)return;var p=data.resultat;
        if(data.lecture_seule!==true||data.publication_active!==false||data.validation_juridique!=='non_validee'||data.perimetre!=='revue_administrative_quarantaine'||!p||p.type_rapport!=='lecture_page_pdf_indexee'||p.lot_id!==selection||p.document_id!==item.document_id||p.page_pdf!==item.page_pdf||p.pdf_sha256!==item.pdf_sha256||p.sha256_texte_utf8!==item.sha256_texte_utf8||p.index_sha256!==origin.index_sha256||!p.archive||p.archive.manifest_sha256!==origin.archive.manifest_sha256||p.publication_active!==false||p.validation_juridique!=='non_validee'||p.ocr_effectue!==false||p.decalage!==start||p.limite!==4000||typeof p.fragment!=='string'||Array.from(p.fragment).length>4000)throw Error('Page indexée non conforme ou index changé ; relancer la recherche.');
        pageView.textContent='Copie indexée non vérifiée — '+p.document_id+' — page physique '+p.page_pdf+' — décalage Unicode '+start+'\nSHA du texte : '+p.sha256_texte_utf8+'\n'+p.fragment;
      }catch(e){if(current()&&number===seq){pageView.textContent='';status.textContent=e.message||'Connexion interrompue.';}}
      finally{busy=false;if(!current())root.replaceChildren();else update();}
    }
    button.addEventListener('click',function(){search(0);});next.addEventListener('click',function(){if(offset!==null&&lastQuery&&lastQuery.q===q.value&&lastQuery.doc===doc.value&&lastQuery.kind===mode.value)search(offset);});clear();
  }
  window.UniOCRCustomsLegalPages=Object.freeze({mount:mount});
})();
