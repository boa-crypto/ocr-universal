/* Real Chromium, GET-only: never exercises mutations against a user's data.
 * npm run ui:product -- http://127.0.0.1:8000 /absolute/artifact/directory
 * Chromium ships through npm, including the required NSS runtime libraries. */
const {chromium}=require('playwright-core');
const binary=require('@sparticuz/chromium').default;
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),z=require('node:zlib'),cp=require('node:child_process'),assert=require('node:assert/strict');
async function main(){
 const base=process.argv[2]||'http://127.0.0.1:8000',out=path.resolve(process.argv[3]||path.join(os.tmpdir(),'uniocr-product-browser'));
 fs.mkdirSync(out,{recursive:true});
 const libs=path.join(os.tmpdir(),'uniocr-chromium-libs');fs.mkdirSync(libs,{recursive:true});
 const archive=path.resolve(path.dirname(require.resolve('@sparticuz/chromium')),'../bin/al2023.tar.br');
 if(process.platform==='linux'&&fs.existsSync(archive)){const tar=path.join(libs,'runtime.tar');fs.writeFileSync(tar,z.brotliDecompressSync(fs.readFileSync(archive)));cp.execFileSync('tar',['xf',tar,'-C',libs]);}
 const args=binary.args.filter(a=>!a.includes('disable-web-security')&&!a.includes('allow-running-insecure-content'));
 const launchOptions={executablePath:await binary.executablePath(),args,headless:true,env:{...process.env,LD_LIBRARY_PATH:[path.join(libs,'lib'),process.env.LD_LIBRARY_PATH].filter(Boolean).join(':')}};
 let browser=null;
 const report={routes:[],errors:[],blockedWrites:[],interactions:[],screenshots:[],limitations:['GET-only audit, not a production write-flow test.','Absent dedicated pages remain explicitly marked by existing routing.']};
 try{
  for(const size of [{width:1440,height:1000},{width:834,height:1112},{width:390,height:844}].filter(x=>!process.env.UI_WIDTH||x.width===Number(process.env.UI_WIDTH))){
   browser=await chromium.launch(launchOptions);
   const context=await browser.newContext({viewport:size,serviceWorkers:'block'}),page=await context.newPage();
   page.on('pageerror',e=>report.errors.push({width:size.width,message:e.message}));
   await page.route('**/*',r=>{if(!['GET','HEAD'].includes(r.request().method())){report.blockedWrites.push({method:r.request().method(),url:new URL(r.request().url()).pathname});return r.abort();}return r.continue();});
   await page.goto(base,{waitUntil:'networkidle'});
   await page.evaluate(()=>document.fonts.ready);assert(await page.evaluate(()=>document.fonts.check('14px Inter')),'Local Inter font unavailable');
   const config=await page.evaluate(()=>Navigation.getConfig());
   for(const route of config.flatMap(g=>[g.route,...g.subitems.map(s=>s.route)])){
    await page.goto(base+'/'+route);await page.waitForTimeout(250);
    const result=await page.evaluate(route=>({route,width:innerWidth,title:document.getElementById('pageTitle').textContent,visible:[...document.querySelectorAll('section.page')].filter(x=>getComputedStyle(x).display!=='none').map(x=>x.id),overflow:document.documentElement.scrollWidth>innerWidth+1}),route);
    report.routes.push(result);assert(result.visible.length>0,'No visible page: '+route);if(!process.env.UI_AUDIT)assert(!result.overflow,'Horizontal overflow '+size.width+' '+route);if(route!=='#dossiers/nouveau')assert(!(await page.locator('#dos-create').evaluate(d=>d.open)),'Route-bound dialog remained modal');
   }
   for(const route of (process.env.UI_SKIPSHOTS?[]:['#cockpit','#workspace/taches','#documents/import','#dossiers/tous','#controle/anomalies','#douane','#finance','#admin/revue-douaniere'])){
    await page.goto(base+'/'+route);await page.waitForTimeout(350);const name=size.width+'-'+route.slice(1).replaceAll('/','-')+'.png';await page.screenshot({path:path.join(out,name),fullPage:false,animations:'disabled',timeout:60000});report.screenshots.push(name);
   }
   await page.goto(base+'/#cockpit');await page.waitForTimeout(300);assert(await page.locator('#globalSearch').isVisible(),'Global search unavailable');
   await page.evaluate(()=>{const c=document.querySelector('ocr-toast-container');c.show({title:'<img src=x onerror=evil()>',message:'<script>evil()</script>',duration:0});if(c.shadowRoot.querySelector('img,script'))throw Error('Toast XSS');if(typeof window.toast!=='function')throw Error('Legacy toast API broken');c.shadowRoot.querySelector('.toast__close').click();});
   await page.locator('.intent-trigger').click();await page.locator('.intent-input').fill('importer');
   await page.keyboard.press('Enter');await page.waitForTimeout(300);assert.equal(new URL(page.url()).hash,'#documents/import');assert(!(await page.locator('.intent-dialog').evaluate(d=>d.open)));
   await page.keyboard.press('Control+j');assert(await page.locator('.intent-dialog').evaluate(d=>d.open));await page.keyboard.press('Escape');assert(!(await page.locator('.intent-dialog').evaluate(d=>d.open)));
   await page.goto(base+'/#dossiers/nouveau');await page.waitForTimeout(250);assert(await page.locator('#dos-create').evaluate(d=>d.open));await page.locator('#dos-create-cancel').click();await page.waitForTimeout(250);assert.equal(new URL(page.url()).hash,'#dossiers');assert(!(await page.locator('#dos-create').evaluate(d=>d.open)));
   report.interactions.push({width:size.width,commandSearch:true,keyboard:true,dialogRecovery:true,localFont:true,toastEscaped:true});
   if(size.width<1025){await page.locator('#navBurger').click();assert(await page.locator('#app').evaluate(a=>a.classList.contains('nav-open')));await page.locator('#themeToggle').click();}else await page.locator('#themeToggle').click();
   await page.waitForTimeout(150);assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');await page.screenshot({path:path.join(out,size.width+'-dark.png'),fullPage:false,animations:'disabled',timeout:60000});
   await context.close();await browser.close();browser=null;
  }
 }catch(error){const pages=browser?browser.contexts().flatMap(c=>c.pages()):[];if(pages.length){const p=pages.at(-1);await p.screenshot({path:path.join(out,'failure.png')});console.error(await p.evaluate(()=>{let e=document.querySelector('.intent-trigger'),r=e.getBoundingClientRect();return {scrollY,rect:r.toJSON(),hit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.outerHTML.slice(0,150)}}));}throw error;}finally{fs.writeFileSync(path.join(out,'browser-report.json'),JSON.stringify(report,null,2));if(browser)await browser.close();}
 assert.equal(report.errors.length,0,JSON.stringify(report.errors));assert.equal(report.blockedWrites.length,0,'Unexpected mutations');
 console.log(JSON.stringify({routes:report.routes.length,viewports:new Set(report.routes.map(r=>r.width)).size,screenshots:report.screenshots.length,errors:report.errors.length,mutations:report.blockedWrites.length,artifacts:out}));
}
main().catch(e=>{console.error(e);process.exit(1)});
