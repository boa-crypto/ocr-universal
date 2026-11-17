/* Recherche explicite dans des pages natives indexées, pas dans des articles validés. */
(function(){
  'use strict';
  function mount(parent,lot,active){
    function node(tag,text){var n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;}
    function token(){try{return sessionStorage.getItem('uniocr_token')||'';}catch(e){return '';}}
    var initialToken=token(),seq=0,busy=false,revoked=false;
    var root=node('fieldset'),legend=node('legend','Rechercher dans les pages PDF reçues — non validées'),label=node('label','Termes littéraux (même page)'),q=node('input'),docLabel=node('label','ID du document exact (facultatif)'),doc=node('input'),button=node('button','Rechercher les pages'),next=node('button','Pages de résultats suivantes'),status=node('p'),output=node('pre');
    q.maxLength=doc.maxLength=256;q.dir=doc.dir=output.dir='auto';button.type=next.type='button';status.setAttribute('role','status');label.append(q);docLabel.append(doc);root.append(legend,label,docLabel,button,next,status,output);parent.append(root);
    var modeLabel=node('label','Mode de consultation'),mode=node('select');mode.dataset.pdfMode='';['texte','reperes','catalogue'].forEach(function(k){var o=node('option',k==='texte'?'Recherche de texte':k==='reperes'?'Repères d’articles candidats':'Catalogue des pages physiques');o.value=k;mode.append(o);});modeLabel.append(mode);root.insertBefore(modeLabel,button);
    var physicalLabel=node('label','Page physique exacte (facultative, catalogue seulement)'),physicalPage=node('input');physicalPage.type='number';physicalPage.min='1';physicalPage.max='10000';physicalPage.step='1';physicalPage.disabled=true;physicalPage.dataset.physicalPage='';physicalLabel.append(physicalPage);root.insertBefore(physicalLabel,button);
    var technical=node('details'),technicalTitle=node('summary','Provenance et réponse technique');technical.className='document-provenance';technical.append(technicalTitle,output);root.append(technical);
    var navigation=node('div'),pageView=node('pre');navigation.className='document-results';pageView.dir='auto';pageView.dataset.indexPage='';root.append(navigation,pageView);
    var pageControls=node('div'),previousFragment=node('button','Fragment précédent'),nextFragment=node('button','Fragment suivant'),anchorFragment=node('button','Revenir au contexte sélectionné'),pageInfo=node('p');
    [previousFragment,nextFragment,anchorFragment].forEach(function(b){b.type='button';pageControls.append(b);});
    pageControls.setAttribute('role','group');pageControls.setAttribute('aria-label','Navigation du texte indexé non vérifié');
    previousFragment.dataset.previousFragment='';nextFragment.dataset.nextFragment='';anchorFragment.dataset.anchorFragment='';pageInfo.setAttribute('role','status');root.insertBefore(pageControls,pageView);root.insertBefore(pageInfo,pageView);
    var offset=null,lastQuery=null,pageState=null;
    function resetPage(){pageState=null;pageView.textContent='';pageInfo.textContent='';pageControls.hidden=true;}
    mode.addEventListener('change',function(){q.value=physicalPage.value='';q.disabled=mode.value==='catalogue';physicalPage.disabled=mode.value!=='catalogue';button.textContent=mode.value==='catalogue'?'Afficher le catalogue':'Rechercher les pages';q.maxLength=mode.value==='texte'?256:32;label.firstChild.textContent=mode.value==='texte'?'Termes littéraux (même page)':mode.value==='reperes'?'Numéro littéral exact (facultatif, pas article validé)':'Aucun terme nécessaire pour le catalogue';clear();});
    function current(){return !revoked&&root.isConnected&&active()&&token()===initialToken;}
    function update(){root.disabled=busy||!lot.selectedOptions.length||lot.selectedOptions[0].dataset.lotType!=='code';next.disabled=busy||offset===null;pageControls.hidden=pageState===null;previousFragment.disabled=busy||!pageState||pageState.start===0;nextFragment.disabled=busy||!pageState||pageState.next===null;anchorFragment.disabled=busy||!pageState||pageState.start===pageState.anchor;}
    function clear(){seq++;offset=null;lastQuery=null;output.textContent='';navigation.replaceChildren();resetPage();status.textContent='Recherche documentaire uniquement, sans correction du texte ni droit à date.';update();}
    lot.addEventListener('change',function(){q.value=doc.value=physicalPage.value='';clear();});
    [q,doc,physicalPage].forEach(function(i){i.addEventListener('input',clear);});
    async function search(start){
      if(!current()){root.replaceChildren();return;}
      if(busy||(mode.value==='texte'&&!q.value.trim()))return;
      var number=++seq,selection=lot.value,query=q.value,documentId=doc.value,kind=mode.value,pageNumber=physicalPage.value;
      if(kind==='catalogue'&&pageNumber&&(!/^[0-9]{1,5}$/.test(pageNumber)||Number(pageNumber)<1||Number(pageNumber)>10000)){clear();status.textContent='Page physique invalide (1 à 10000).';return;}
      busy=true;update();output.textContent='';navigation.replaceChildren();resetPage();status.textContent='Recherche…';
      try{
        var params=new URLSearchParams({limit:'20',offset:String(start)});if(kind==='texte')params.set('q',query);else if(kind==='reperes'&&query)params.set('numero',query);if(kind==='catalogue'&&pageNumber)params.set('page',pageNumber);if(documentId)params.set('document_id',documentId);
        var headers={Accept:'application/json'};if(initialToken)headers.Authorization='Bearer '+initialToken;
        var response=await fetch('/api/v1/customs-review/lots/'+encodeURIComponent(selection)+(kind==='texte'?'/pdf-search?':kind==='reperes'?'/pdf-article-markers?':'/pdf-index-catalog?')+params,{headers:headers,method:'GET',credentials:'same-origin',cache:'no-store'});
        if(!current()||number!==seq||lot.value!==selection)return;
        if(!response.ok){if(response.status===401||response.status===403){revoked=true;root.replaceChildren();return;}throw Error(response.status===409?'Index absent, non épinglé ou incohérent ; aucune recherche dégradée automatique.':'Recherche refusée ('+response.status+').');}
        var data=await response.json();if(!current()||number!==seq)return;
        var r=data.resultat;
        if(data.lecture_seule!==true||data.publication_active!==false||data.validation_juridique!=='non_validee'||data.perimetre!=='revue_administrative_quarantaine'||!r||r.type_recherche!==(kind==='texte'?'pages_pdf_natives':kind==='reperes'?'reperes_articles_pdf':'catalogue_pages_pdf')||r.lot_id!==selection||r.requete!==query||r.decalage!==start||r.limite!==20||r.publication_active!==false||r.validation_juridique!=='non_validee'||r.classement_douanier_valide!==false||r.restitution_juridique_a_date!==false||r.ocr_effectue!==false||r.articles_localises_automatiquement!==false||(kind==='reperes'&&r.reperes_detectes_automatiquement!==true)||!r.archive||!/^[a-f0-9]{64}$/.test(r.archive.manifest_sha256)||!/^[a-f0-9]{64}$/.test(r.index_sha256)||!Array.isArray(r.resultats)||r.resultats.length>20||!Number.isInteger(r.total_correspondances)||r.total_correspondances<r.resultats.length||!(r.decalage_suivant===null||(Number.isInteger(r.decalage_suivant)&&r.decalage_suivant===start+r.resultats.length&&r.decalage_suivant>start)))throw Error('Réponse documentaire non conforme.');
        if(start>0&&(!lastQuery||lastQuery.index!==r.index_sha256||lastQuery.manifest!==r.archive.manifest_sha256))throw Error('Index changé pendant la pagination ; relancer la recherche.');
        if(kind==='catalogue'&&(!Number.isInteger(r.pages_indexees)||r.pages_indexees<1||r.pages_indexees>1000||r.total_correspondances>r.pages_indexees||r.resultats.length!==Math.min(20,Math.max(0,r.total_correspondances-start))||r.decalage_suivant!==(start+r.resultats.length<r.total_correspondances?start+r.resultats.length:null)||!r.filtres||r.filtres.document_id_exact!==(documentId||null)||r.filtres.page_physique_exacte!==(pageNumber?Number(pageNumber):null)||r.resultats.some(function(item){return !item||typeof item.document_id!=='string'||(documentId&&item.document_id!==documentId)||!Number.isInteger(item.page_pdf)||item.page_pdf<1||!Number.isInteger(item.nombre_pages_pdf)||item.nombre_pages_pdf<item.page_pdf||(pageNumber&&item.page_pdf!==Number(pageNumber))||!Number.isInteger(item.total_caracteres)||item.total_caracteres<0||item.total_caracteres>200000||item.texte_indexe_present!==(item.total_caracteres>0)||!/^[a-f0-9]{64}$/.test(item.pdf_sha256)||!/^[a-f0-9]{64}$/.test(item.sha256_texte_utf8);})))throw Error('Catalogue de pages non conforme.');
        offset=r.decalage_suivant;lastQuery={q:query,doc:documentId,kind:kind,page:pageNumber,index:r.index_sha256,manifest:r.archive.manifest_sha256};output.textContent=JSON.stringify(r,null,2);status.textContent=r.total_correspondances+(kind==='reperes'?' repère(s) candidat(s)':' page(s) correspondante(s)')+', pas articles validés ni occurrences juridiquement qualifiées. Aucun résultat ne prouve une absence de droit.';
        r.resultats.forEach(function(item){
          if(typeof item.document_id!=='string'||!Number.isInteger(item.page_pdf)||item.page_pdf<1||!/^[a-f0-9]{64}$/.test(item.pdf_sha256)||!/^[a-f0-9]{64}$/.test(item.sha256_texte_utf8))return;
          var b=node('button','Lire la page '+item.page_pdf+' — '+(item.numero_litteral||item.document_id)+(item.texte_indexe_present===false?' — sans texte indexé':''));b.type='button';b.dataset.readIndexPage='';b.addEventListener('click',function(){readPage(item,r,selection);});var card=node('article'),meta=node('p',item.document_id),title=node('h3','Page physique '+item.page_pdf+(item.numero_litteral?' · Repère '+item.numero_litteral:'')),excerpt=node('p',item.entete_litteral||(Array.isArray(item.extraits)&&item.extraits[0]&&typeof item.extraits[0].fragment==='string'?item.extraits[0].fragment:null)|| (item.total_caracteres!==undefined?item.total_caracteres+' points de code indexés · '+item.nombre_pages_pdf+' pages dans ce document':'Copie native indexée · texte non vérifié'));card.className='document-result';meta.className='document-result-source';card.append(meta,title,excerpt,b);navigation.append(card);
        });
      }catch(e){if(current()&&number===seq){offset=null;lastQuery=null;output.textContent='';status.textContent=e.message||'Connexion interrompue.';}}
      finally{busy=false;if(!current())root.replaceChildren();else update();}
    }
    async function readPage(item,origin,selection,requestedStart,expectedTotal){
      if(!current()){root.replaceChildren();return;}if(busy||lot.value!==selection)return;
      var anchor=Number.isInteger(item.debut)?Math.max(0,item.debut-200):0;
      var number=++seq,start=requestedStart===undefined?anchor:requestedStart;
      busy=true;resetPage();update();
      try{
        var params=new URLSearchParams({document_id:item.document_id,page:String(item.page_pdf),offset:String(start),limit:'4000'}),headers={Accept:'application/json'};if(initialToken)headers.Authorization='Bearer '+initialToken;
        var response=await fetch('/api/v1/customs-review/lots/'+encodeURIComponent(selection)+'/pdf-index-page?'+params,{headers:headers,method:'GET',credentials:'same-origin',cache:'no-store'});
        if(!current()||number!==seq||lot.value!==selection)return;
        if(!response.ok){if(response.status===401||response.status===403){revoked=true;root.replaceChildren();return;}throw Error('Lecture de page refusée ('+response.status+').');}
        var data=await response.json();if(!current()||number!==seq)return;var p=data.resultat;
        if(data.lecture_seule!==true||data.publication_active!==false||data.validation_juridique!=='non_validee'||data.perimetre!=='revue_administrative_quarantaine'||!p||p.type_rapport!=='lecture_page_pdf_indexee'||p.lot_id!==selection||p.document_id!==item.document_id||p.page_pdf!==item.page_pdf||p.pdf_sha256!==item.pdf_sha256||p.sha256_texte_utf8!==item.sha256_texte_utf8||p.index_sha256!==origin.index_sha256||!p.archive||p.archive.manifest_sha256!==origin.archive.manifest_sha256||p.publication_active!==false||p.validation_juridique!=='non_validee'||p.ocr_effectue!==false||p.decalage!==start||p.limite!==4000||typeof p.fragment!=='string'||Array.from(p.fragment).length>4000)throw Error('Page indexée non conforme ou index changé ; relancer la recherche.');
        var length=Array.from(p.fragment).length;
        if(p.lecture_seule!==true||p.transcription_verification!=='non_verifiee'||p.unite_decalage!=='points_de_code_unicode_python'||!Number.isInteger(p.nombre_pages_pdf)||p.nombre_pages_pdf<item.page_pdf||!Number.isInteger(p.total_caracteres)||p.total_caracteres<start||p.total_caracteres>67108864||length!==Math.min(4000,p.total_caracteres-start)||p.decalage_suivant!==(start+length<p.total_caracteres?start+length:null)||(expectedTotal!==undefined&&expectedTotal!==p.total_caracteres)||(item.total_caracteres!==undefined&&item.total_caracteres!==p.total_caracteres)||(item.nombre_pages_pdf!==undefined&&item.nombre_pages_pdf!==p.nombre_pages_pdf))throw Error('Pagination de page non conforme ; relancer la recherche.');
        pageState={item:item,origin:origin,selection:selection,start:start,next:p.decalage_suivant,anchor:anchor,total:p.total_caracteres};
        pageInfo.textContent='Fragment Unicode ['+start+', '+(start+length)+'[ sur '+p.total_caracteres+' points de code — page physique '+p.page_pdf+' sur '+p.nombre_pages_pdf+'. Les fragments ne délimitent pas des articles.';
        pageView.textContent='Copie indexée non vérifiée — '+p.document_id+' — page physique '+p.page_pdf+' — décalage Unicode '+start+'\nSHA du texte : '+p.sha256_texte_utf8+'\n'+p.fragment;
      }catch(e){if(current()&&number===seq){resetPage();status.textContent=e.message||'Connexion interrompue.';}}
      finally{busy=false;if(!current())root.replaceChildren();else update();}
    }
    function moveFragment(kind){if(!pageState||busy)return;var s=pageState,target=kind==='previous'?Math.max(0,s.start-4000):kind==='next'?s.next:s.anchor;if(target!==null)readPage(s.item,s.origin,s.selection,target,s.total);}
    previousFragment.addEventListener('click',function(){moveFragment('previous');});nextFragment.addEventListener('click',function(){moveFragment('next');});anchorFragment.addEventListener('click',function(){moveFragment('anchor');});
    button.addEventListener('click',function(){search(0);});next.addEventListener('click',function(){if(offset!==null&&lastQuery&&lastQuery.q===q.value&&lastQuery.doc===doc.value&&lastQuery.kind===mode.value&&lastQuery.page===physicalPage.value)search(offset);});clear();
  }
  window.UniOCRCustomsLegalPages=Object.freeze({mount:mount});
})();
