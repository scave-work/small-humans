/* Page de cheminement : lit ../cheminement.json et dessine, pour un sujet (data-sujet du <body>), l'arbre, les fiches et la visionneuse three.js. */
const SUJET=document.body.dataset.sujet;
const LIB={garde:'gardé',abandonne:'abandonné',en_attente:'en attente'};
const e=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const calme=matchMedia('(prefers-reduced-motion:reduce)').matches;
fetch('../cheminement.json').then(r=>r.json()).then(J=>{
  const S=J.sujets[SUJET],N=J.noeuds.filter(n=>n.sujet===SUJET),byId=Object.fromEntries(N.map(n=>[n.id,n]));
  document.title=S.titre+' – Small Humans';
  document.getElementById('titre').textContent=S.titre;
  document.getElementById('intro').textContent=S.intro;
  document.getElementById('sujets').innerHTML=Object.entries(J.sujets).map(([k,v])=>`<a href="../${k}/"${k===SUJET?' class="cur" aria-current="page"':''}>${e(v.titre)}</a>`).join('');
  /* arbre vertical */
  const kids={};N.forEach(n=>{(kids[n.parent]=kids[n.parent]||[]).push(n)});
  let row=0;const pos={};
  (function place(n,d){pos[n.id]={d};const k=kids[n.id]||[];if(!k.length){pos[n.id].r=row++;return}k.forEach(c=>place(c,d+1));pos[n.id].r=(pos[k[0].id].r+pos[k[k.length-1].id].r)/2})(N.find(n=>!n.parent),0);
  const W=160,H=44,GX=14,GY=26,PX=6,PY=6,maxD=Math.max(...Object.values(pos).map(p=>p.d));
  const W_=PX*2+row*(W+GX)-GX,H_=PY*2+(maxD+1)*(H+GY)-GY,X=n=>PX+pos[n.id].r*(W+GX),Y=n=>PY+pos[n.id].d*(H+GY);
  document.documentElement.style.setProperty('--wside',Math.min(620,Math.max(250,W_+22))+'px');
  let s=`<svg viewBox="0 0 ${W_} ${H_}" role="img" aria-label="Arbre des versions">`;
  N.filter(n=>n.parent).forEach(n=>{const p=byId[n.parent],x1=X(p)+W/2,y1=Y(p)+H,x2=X(n)+W/2,y2=Y(n),m=(y1+y2)/2;s+=`<path class="lien" d="M${x1} ${y1}C${x1} ${m} ${x2} ${m} ${x2} ${y2}"/>`});
  N.forEach(n=>{const t=n.titre.length>25?n.titre.slice(0,24)+'…':n.titre;
    s+=`<g class="nd ${n.statut}" data-id="${n.id}" tabindex="0" role="link" aria-label="${e(n.titre)}"><title>${e(n.titre)}</title><rect x="${X(n)}" y="${Y(n)}" width="${W}" height="${H}" rx="8"/><text x="${X(n)+9}" y="${Y(n)+19}">${e(t)}</text><text class="d" x="${X(n)+9}" y="${Y(n)+35}">${e(n.date.slice(8,10)+'/'+n.date.slice(5,7))} · ${LIB[n.statut]}</text></g>`});
  document.getElementById('arbre').innerHTML=s+'</svg>';
  /* fiches */
  const ligne=(t,v)=>v?`<dt>${t}</dt><dd>${e(v)}</dd>`:'';
  document.getElementById('fiches').innerHTML=N.map((n,i)=>{
    const r=n.rendus&&n.rendus.length;
    let cap=n.capture?`<img loading="lazy" src="../img/${e(n.capture)}" alt="Rendu : ${e(n.titre)}" onerror="this.outerHTML='<div class=nc>Capture non reconstituée</div>'">`:`<div class="nc">${e(n.legende||'Pas de capture')}</div>`;
    if(n.capture2) cap+=`<img loading="lazy" src="../img/${e(n.capture2)}" alt="Série d'états" onerror="this.remove()">`;
    if(r&&n.capture) cap=`<div class="vue" data-id="${n.id}" tabindex="0" role="button" aria-label="Voir le rendu en direct : ${e(n.titre)}">${cap}</div>`;
    const lg=n.capture&&n.legende?`<p class="aide">${e(n.legende)}</p>`:'';
    const bt=r?`<div class="btns">${n.rendus.map((x,j)=>`<button data-id="${n.id}" data-j="${j}">▶ ${e(x.label)}</button>`).join('')}</div>`:'';
    return `<article class="fiche ${n.statut}" id="n-${n.id}"><h3>${i+1}. ${e(n.titre)}<span class="badge">${LIB[n.statut]}</span></h3>
<p class="meta">${e(n.date.replace(' ',' à '))}${n.commit?' · version '+e(n.commit):''}</p>
<div class="cols"><div class="cap">${cap}${lg}${bt}</div><dl>
${ligne('Ce qu\'on cherchait',n.cherche)}<dt>La consigne</dt><dd class="p">${e(n.prompt)}</dd>${ligne('Modèle',n.modele)}${ligne('Technique',n.techno)}${ligne('Retour de Simon',n.retour)}
</dl></div><div class="gk"><div class="g"><b>Gardé</b>${e(n.garde)}</div><div class="a"><b>Abandonné</b>${e(n.abandonne)}</div></div></article>`}).join('');
  document.getElementById('lecons').innerHTML=J.lecons.map(l=>`<li>${e(l)}</li>`).join('');
  /* clic sur l'arbre */
  const go=id=>{const f=document.getElementById('n-'+id);if(!f)return;document.querySelectorAll('.sel').forEach(x=>x.classList.remove('sel'));f.classList.add('sel');document.querySelector(`.nd[data-id="${id}"]`).classList.add('sel');f.scrollIntoView({behavior:calme?'auto':'smooth',block:'start'})};
  document.querySelectorAll('.nd').forEach(g=>{g.onclick=()=>go(g.dataset.id);g.onkeydown=ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();go(g.dataset.id)}}});
  /* visionneuse : le moteur three.js ne se charge qu'à l'ouverture */
  const V=document.getElementById('visio'),F=document.getElementById('vframe');let cur=null;
  const ouvre=(id,j)=>{const n=byId[id];cur=n;const x=n.rendus[j];
    document.getElementById('vtit').textContent=n.titre;
    document.getElementById('vbtn').innerHTML=n.rendus.map((y,k)=>`<button data-k="${k}" class="${k===j?'on':''}">${e(y.label)}</button>`).join('');
    const u='../'+x.url;F.src=u;document.getElementById('vopen').href=u;V.classList.add('on');document.body.style.overflow='hidden';
    document.getElementById('vnote').textContent=/porte|planche_porte/.test(x.url)?'Faites défiler dans la fenêtre : la porte s\'ouvre au scroll.':'Le rendu tourne en direct (three.js).'};
  const ferme=()=>{V.classList.remove('on');F.src='about:blank';document.body.style.overflow=''};
  document.getElementById('fiches').addEventListener('click',ev=>{const b=ev.target.closest('button[data-id]');if(b)return ouvre(b.dataset.id,+b.dataset.j);const v=ev.target.closest('.vue');if(v)ouvre(v.dataset.id,0)});
  document.getElementById('fiches').addEventListener('keydown',ev=>{const v=ev.target.closest&&ev.target.closest('.vue');if(v&&(ev.key==='Enter'||ev.key===' ')){ev.preventDefault();ouvre(v.dataset.id,0)}});
  document.getElementById('vbtn').addEventListener('click',ev=>{const b=ev.target.closest('button[data-k]');if(b)ouvre(cur.id,+b.dataset.k)});
  document.getElementById('vclose').onclick=ferme;
  document.addEventListener('keydown',ev=>{if(ev.key==='Escape'&&V.classList.contains('on'))ferme()});
}).catch(()=>{document.getElementById('arbre').textContent='Données indisponibles (cheminement.json).'});
