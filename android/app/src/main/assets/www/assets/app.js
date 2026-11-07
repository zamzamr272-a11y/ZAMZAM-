(() => {
  'use strict';
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const fmt = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 });
  const money = value => 'Rp ' + fmt.format(Number(value || 0));
  const shortMoney = value => {
    const n = Number(value || 0);
    if (n >= 1e9) return 'Rp ' + (n / 1e9).toLocaleString('id-ID', {maximumFractionDigits:1}) + ' M';
    if (n >= 1e6) return 'Rp ' + (n / 1e6).toLocaleString('id-ID', {maximumFractionDigits:1}) + ' jt';
    if (n >= 1e3) return 'Rp ' + (n / 1e3).toLocaleString('id-ID', {maximumFractionDigits:1}) + ' rb';
    return money(n);
  };
  const dateFmt = value => {
    try { return new Date(value).toLocaleDateString('id-ID', {day:'2-digit',month:'short',year:'numeric'}); }
    catch { return '—'; }
  };
  const dateTimeFmt = value => {
    try { return new Date(value).toLocaleString('id-ID', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}); }
    catch { return ''; }
  };
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const today = new Date();
  const dateInput = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
  const startOfYear = new Date(today.getFullYear(), 0, 1);
  const DEMO = {
    user: { username: 'NEXORA Guest', profile_code: 'NX-DEMO-2026' },
    accounts: [
      {id:'demo-cash',name:'Tunai',kind:'cash',balance:'1850000',opening_balance:'1200000',currency:'IDR'},
      {id:'demo-bank',name:'Rekening utama',kind:'bank',balance:'28600000',opening_balance:'17500000',currency:'IDR'},
      {id:'demo-ewallet',name:'E-Wallet',kind:'ewallet',balance:'2200000',opening_balance:'900000',currency:'IDR'}
    ],
    categories: [
      {id:'d-cat-food',name:'Makanan',kind:'expense',color:'#F2B35E',icon:'◒'},
      {id:'d-cat-trans',name:'Transportasi',kind:'expense',color:'#67B8E8',icon:'↗'},
      {id:'d-cat-bills',name:'Tagihan',kind:'expense',color:'#F16D72',icon:'▤'},
      {id:'d-cat-shop',name:'Belanja',kind:'expense',color:'#A78BFA',icon:'◇'},
      {id:'d-cat-fun',name:'Hiburan',kind:'expense',color:'#E28BC4',icon:'♫'},
      {id:'d-cat-salary',name:'Gaji',kind:'income',color:'#39C98A',icon:'↗'},
      {id:'d-cat-free',name:'Freelance',kind:'income',color:'#42D6C5',icon:'✦'}
    ],
    transactions: [
      {id:'d1',kind:'income',amount:'12500000',currency:'IDR',source_account_id:'demo-bank',category_id:'d-cat-salary',description:'Gaji bulanan',occurred_at:dateInput(new Date(today.getFullYear(),today.getMonth(),2))+'T08:10:00+08:00',notes:''},
      {id:'d2',kind:'expense',amount:'85000',currency:'IDR',source_account_id:'demo-ewallet',category_id:'d-cat-food',description:'Makan siang — Kopi & Roti',occurred_at:dateInput(new Date(today.getFullYear(),today.getMonth(),6))+'T12:15:00+08:00',notes:''},
      {id:'d3',kind:'expense',amount:'175000',currency:'IDR',source_account_id:'demo-bank',category_id:'d-cat-trans',description:'Transportasi online',occurred_at:dateInput(new Date(today.getFullYear(),today.getMonth(),5))+'T18:30:00+08:00',notes:''},
      {id:'d4',kind:'expense',amount:'425000',currency:'IDR',source_account_id:'demo-bank',category_id:'d-cat-bills',description:'Tagihan internet & listrik',occurred_at:dateInput(new Date(today.getFullYear(),today.getMonth(),4))+'T10:00:00+08:00',notes:''},
      {id:'d5',kind:'income',amount:'2500000',currency:'IDR',source_account_id:'demo-bank',category_id:'d-cat-free',description:'Proyek desain freelance',occurred_at:dateInput(new Date(today.getFullYear(),today.getMonth(),3))+'T14:00:00+08:00',notes:''},
      {id:'d6',kind:'expense',amount:'620000',currency:'IDR',source_account_id:'demo-cash',category_id:'d-cat-shop',description:'Belanja kebutuhan rumah',occurred_at:dateInput(new Date(today.getFullYear(),today.getMonth(),1))+'T16:00:00+08:00',notes:''},
      {id:'d7',kind:'expense',amount:'145000',currency:'IDR',source_account_id:'demo-ewallet',category_id:'d-cat-fun',description:'Streaming & hiburan',occurred_at:dateInput(new Date(today.getFullYear(),today.getMonth(),2))+'T20:30:00+08:00',notes:''}
    ],
    groups: [{id:'demo-group',name:'Money Talks',description:'Belajar finansial bareng, saling berbagi insight.',rules:'Diskusi santun, sertakan sumber, bukan ajakan trading.',role:'owner'}],
    messages: [
      {id:'dm1',user_id:'member-a',username:'Alya',body:'Aku mulai catat semua pengeluaran kecil minggu ini. Ternyata lumayan juga kalau dikumpulkan.',created_at:new Date(Date.now()-3600000).toISOString()},
      {id:'dm2',user_id:'demo-self',username:'NEXORA Guest',body:'Setuju. Insight yang jelas bikin kita lebih sadar pola belanja.',created_at:new Date(Date.now()-1800000).toISOString()}
    ],
    watchlist: [{id:'dw1',symbol:'BBCA',asset_name:'Bank Central Asia',note:'Pantau fundamental dan valuasi.'},{id:'dw2',symbol:'TLKM',asset_name:'Telkom Indonesia',note:'Pantau perkembangan bisnis.'}],
    theses: []
  };
  const state = {
    view: 'home', theme: localStorage.getItem('nexora_theme') || 'dark',
    apiBase: localStorage.getItem('nexora_api_base') || (location.protocol.startsWith('http') ? `${location.origin}/api/v1` : ''),
    token: sessionStorage.getItem('nexora_access') || '', refresh: sessionStorage.getItem('nexora_refresh') || '',
    user: null, online: false, demo: true, busy: false, period: 'month',
    start: dateInput(monthStart), end: dateInput(today),
    accounts: DEMO.accounts.map(x=>({...x})), categories: DEMO.categories.map(x=>({...x})),
    transactions: JSON.parse(localStorage.getItem('nexora_demo_transactions') || 'null') || DEMO.transactions.map(x=>({...x})),
    summary: null, categoryReport: [], cashflow: [], budgets: [], groups: [],
    activeGroup: null, messages: [], joinRequests: [], watchlist: DEMO.watchlist.map(x=>({...x})),
    theses: [], tickets: [], socket: null, socketGroup: null
  };
  document.documentElement.dataset.theme = state.theme;

  function toast(message, type='') {
    const root = $('#toast-root'); const node = document.createElement('div');
    node.className = `toast ${type}`; node.textContent = message; root.append(node);
    setTimeout(()=>node.remove(), 3600);
  }
  function openModal(title, subtitle, body, options={}) {
    $('#modal-root').innerHTML = `<div class="modal-backdrop" data-modal-backdrop><div class="modal ${options.wide?'wide':''}" role="dialog" aria-modal="true"><div class="modal-head"><div><h2>${esc(title)}</h2><p>${esc(subtitle || '')}</p></div><button class="modal-close" data-action="close-modal" aria-label="Tutup">×</button></div>${body}</div></div>`;
    const backdrop = $('[data-modal-backdrop]');
    backdrop.addEventListener('click', e=>{ if(e.target===backdrop) closeModal(); });
    const first = $('input,select,textarea,button', backdrop); if(first) setTimeout(()=>first.focus(),50);
  }
  function closeModal(){ $('#modal-root').innerHTML=''; }
  function apiUrl(path){ return `${state.apiBase.replace(/\/$/,'')}${path.startsWith('/')?path:'/'+path}`; }
  async function api(path, options={}) {
    if(!state.apiBase) throw new Error('Alamat server belum diatur. Hubungkan URL backend terlebih dahulu.');
    const headers = {'Content-Type':'application/json', ...(options.headers||{})};
    if(state.token) headers.Authorization = `Bearer ${state.token}`;
    const response = await fetch(apiUrl(path), {...options, headers});
    const type = response.headers.get('content-type') || '';
    const payload = type.includes('application/json') ? await response.json() : await response.text();
    if(!response.ok) {
      if(response.status===401 && state.refresh && path!='/auth/refresh') {
        await refreshAuth();
        return api(path, options);
      }
      throw new Error(payload?.detail || payload?.message || `Permintaan gagal (${response.status}).`);
    }
    return payload;
  }
  async function refreshAuth(){
    const r = await fetch(apiUrl('/auth/refresh'), {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({refresh_token:state.refresh})});
    if(!r.ok){ logoutLocal(false); throw new Error('Sesi berakhir. Silakan masuk kembali.'); }
    const data=await r.json(); state.token=data.access_token; state.refresh=data.refresh_token;
    sessionStorage.setItem('nexora_access',state.token);sessionStorage.setItem('nexora_refresh',state.refresh);
  }
  function saveTokens(data){
    state.token=data.access_token;state.refresh=data.refresh_token;state.user=data.user;
    sessionStorage.setItem('nexora_access',state.token);sessionStorage.setItem('nexora_refresh',state.refresh);
  }
  function logoutLocal(show=true){
    state.token='';state.refresh='';state.user=null;state.online=false;state.demo=true;
    sessionStorage.removeItem('nexora_access');sessionStorage.removeItem('nexora_refresh');
    if(state.socket){state.socket.close();state.socket=null;state.socketGroup=null;}
    state.transactions=JSON.parse(localStorage.getItem('nexora_demo_transactions')||'null')||DEMO.transactions.map(x=>({...x}));
    state.accounts=DEMO.accounts.map(x=>({...x}));state.categories=DEMO.categories.map(x=>({...x}));
    state.watchlist=DEMO.watchlist.map(x=>({...x}));state.groups=DEMO.groups.map(x=>({...x}));
    render(); if(show) toast('Kamu sudah keluar dari NEXORA.');
  }
  async function loadData(){
    if(!state.token){state.demo=true;return;}
    const [me,accounts,categories,transactions,summary,categoriesReport,cashflow,budgets,groups,watchlist,theses,tickets] = await Promise.all([
      api('/me'),api('/accounts'),api('/categories'),api(`/transactions?start=${state.start}&end=${state.end}&limit=100`),
      api(`/reports/summary?start=${state.start}&end=${state.end}`),
      api(`/reports/categories?start=${state.start}&end=${state.end}`),
      api(`/reports/cashflow?start=${state.start}&end=${state.end}&bucket=day`),
      api('/budgets'),api('/groups'),api('/watchlist'),api('/investment/theses'),api('/support/tickets')
    ]);
    state.user=me;state.accounts=accounts;state.categories=categories;state.transactions=transactions;
    state.summary=summary;state.categoryReport=categoriesReport;state.cashflow=cashflow;state.budgets=budgets;
    state.groups=groups;state.watchlist=watchlist;state.theses=theses;state.tickets=tickets;
    state.demo=false;state.online=true;
    if(!state.activeGroup || !state.groups.some(g=>g.id===state.activeGroup)) state.activeGroup=state.groups[0]?.id||null;
  }
  async function start(){
    $('#today-label').textContent = today.toLocaleDateString('id-ID',{weekday:'short',day:'2-digit',month:'short',year:'numeric'});
    if(state.token && state.apiBase){
      try{await loadData();}catch(e){if(/sesi|login|masuk/i.test(e.message)) logoutLocal(false);else {state.online=false;toast(`Server belum terjangkau: ${e.message}`,'error');}}
    } else if(!state.apiBase){state.demo=true;}
    updateStatus();render();
    if('serviceWorker' in navigator && location.protocol.startsWith('http')) navigator.serviceWorker.register('./sw.js').catch(()=>{});
  }
  function updateStatus(){
    $('#connection-label').textContent=state.online?'Terhubung ke server':state.demo?'Mode pratinjau':'Server tidak terjangkau';
    $('#connection-detail').textContent=state.online?'Data akun tersinkron':'Data contoh lokal · tidak tersinkron';
    $('#preview-banner').hidden=!state.demo;
    const name=state.user?.username||'NEXORA Guest';
    $('#sidebar-name').textContent=name;$('#top-avatar').textContent=(name[0]||'N').toUpperCase();
    $('#sidebar-avatar').textContent=(name[0]||'N').toUpperCase();
    $('#sidebar-role').textContent=state.online?'Personal workspace':'Preview workspace';
  }
  function setView(view){
    state.view=view; $$('.nav-item,[data-view]',document).forEach(el=>el.classList.toggle('active',el.dataset.view===view));
    const labels={home:'Beranda',finance:'Keuangan',invest:'Investasi',community:'Komunitas',profile:'Profil & keamanan'};
    $('#breadcrumb-current').textContent=labels[view]||'Beranda';
    if(view==='community' && state.online) loadCommunity();
    render();
  }
  function totalDemo(){
    let income=0,expense=0;
    for(const t of state.transactions){if(t.kind==='income')income+=+t.amount;else if(t.kind==='expense')expense+=+t.amount;}
    return {income,expense,net:income-expense,balance:42650000,budget:2500000,top:'Makanan',count:state.transactions.length};
  }
  function summary(){
    if(state.online && state.summary) return {income:+state.summary.income,expense:+state.summary.expense,net:+state.summary.net_cashflow,balance:+state.summary.recorded_balance,budget:+state.summary.budget_remaining,top:state.summary.top_category?.name||'—',count:state.summary.transaction_count};
    return totalDemo();
  }
  function txCategory(t){return state.categories.find(c=>c.id===t.category_id)?.name || (t.kind==='transfer'?'Transfer internal':'Lainnya');}
  function accountName(id){return state.accounts.find(a=>a.id===id)?.name || 'Akun';}
  function txIcon(t){const name=txCategory(t).toLowerCase(); if(t.kind==='income')return '↗';if(t.kind==='transfer')return '⇄';if(name.includes('makan'))return '◒';if(name.includes('trans'))return '↗';if(name.includes('tagih'))return '▤';return '◇';}
  function txAmount(t){return `${t.kind==='income'?'+':t.kind==='expense'?'−':''}${money(t.amount)}`;}
  function svgLineChart(rows){
    const max=Math.max(1,...rows.flatMap(r=>[+r.income,+r.expense]));
    const width=640,height=185,left=28,right=8,top=15,bottom=23;
    const usableW=width-left-right,usableH=height-top-bottom;
    const points=[];
    rows.forEach((r,i)=>{
      const x=left+(rows.length<=1?usableW/2:i*usableW/(rows.length-1));
      const yI=top+usableH-(+r.income/max)*usableH;const yE=top+usableH-(+r.expense/max)*usableH;
      points.push({x,yI,yE});
    });
    const path=arr=>arr.map((p,i)=>`${i?'L':'M'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
    const pi=path(points.map(p=>({x:p.x,y:p.yI}))), pe=path(points.map(p=>({x:p.x,y:p.yE})));
    const labels=rows.map((r,i)=>i%Math.max(1,Math.ceil(rows.length/6))===0?`<text x="${points[i].x}" y="${height-4}" text-anchor="middle" class="chart-tick">${esc(String(r.period).slice(-2))}</text>`:'').join('');
    const grid=[0,1,2,3].map(i=>{const y=top+i*usableH/3;return `<line x1="${left}" y1="${y}" x2="${width-right}" y2="${y}" class="chart-grid"/>`;}).join('');
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Grafik pemasukan dan pengeluaran">${grid}<path d="${pi}" class="line-income"/><path d="${pe}" class="line-expense"/>${points.map(p=>`<circle cx="${p.x}" cy="${p.yI}" r="3" class="dot-income"/><circle cx="${p.x}" cy="${p.yE}" r="3" class="dot-expense"/>`).join('')}${labels}</svg>`;
  }
  function categoriesForChart(){
    if(state.online) return state.categoryReport||[];
    const map={};state.transactions.filter(t=>t.kind==='expense').forEach(t=>{const k=txCategory(t);map[k]=(map[k]||0)+Number(t.amount);});
    const colors=['#F2B35E','#67B8E8','#F16D72','#A78BFA','#E28BC4','#42D6C5'];
    return Object.entries(map).sort((a,b)=>b[1]-a[1]).map(([name,amount],i)=>({name,amount:String(amount),percent:0,color:colors[i%colors.length]})).map((v,_,a)=>({...v,percent:a.reduce((s,x)=>s+ +x.amount,0)?+(+v.amount/a.reduce((s,x)=>s+ +x.amount,0)*100).toFixed(1):0}));
  }
  function donutChart(rows){
    const colors=['#F2B35E','#67B8E8','#F16D72','#A78BFA','#E28BC4','#42D6C5','#39C98A'];
    const total=rows.reduce((s,x)=>s+Number(x.amount),0);let offset=0;
    const circles=rows.slice(0,7).map((r,i)=>{const pct=total?Number(r.amount)/total*100:0;const dash=pct*2.01;const markup=`<circle cx="80" cy="80" r="60" fill="none" stroke="${colors[i%colors.length]}" stroke-width="15" stroke-dasharray="${dash} ${201-dash}" stroke-dashoffset="${-offset}" transform="rotate(-90 80 80)"/>`;offset+=dash;return markup;}).join('');
    return `<svg class="donut" viewBox="0 0 160 160" role="img" aria-label="Komposisi pengeluaran">${circles||'<circle cx="80" cy="80" r="60" fill="none" stroke="var(--surface-3)" stroke-width="15"/>'}<text x="80" y="77" text-anchor="middle" class="donut-center">${shortMoney(total)}</text><text x="80" y="93" text-anchor="middle" class="donut-label">Total keluar</text></svg>`;
  }
  function chartRows(){
    if(state.online && state.cashflow.length) return state.cashflow.slice(-12);
    const rows=[];for(let i=6;i>=0;i--){const d=new Date(today);d.setDate(today.getDate()-i);rows.push({period:dateInput(d),income:0,expense:0});}
    state.transactions.forEach(t=>{const day=String(t.occurred_at).slice(0,10);const row=rows.find(r=>r.period===day);if(row&&t.kind==='income')row.income+=+t.amount;if(row&&t.kind==='expense')row.expense+=+t.amount;});
    return rows;
  }
  function transactionRows(list){
    if(!list.length)return '<div class="empty-state"><b>Belum ada transaksi</b>Mulai dengan mencatat pemasukan atau pengeluaran pertamamu.</div>';
    return `<div class="transaction-list">${list.slice(0,6).map(t=>`<div class="transaction-row"><div class="transaction-icon">${txIcon(t)}</div><div class="transaction-copy"><b>${esc(t.description)}</b><small>${esc(txCategory(t))} · ${esc(dateTimeFmt(t.occurred_at))}</small></div><div class="transaction-amount ${t.kind==='income'?'positive':t.kind==='expense'?'negative':''}">${esc(txAmount(t))}<small>${esc(accountName(t.source_account_id))}</small></div></div>`).join('')}</div>`;
  }
  function renderHome(){
    const s=summary(), cats=categoriesForChart(), rows=chartRows(), txs=state.transactions.slice().sort((a,b)=>new Date(b.occurred_at)-new Date(a.occurred_at));
    const monthLabel=today.toLocaleDateString('id-ID',{month:'long',year:'numeric'});
    const budgetRows=state.online?state.budgets.slice(0,3):[
      {id:'b1',category:'Makanan',amount:'1500000',spent:'860000'},
      {id:'b2',category:'Transportasi',amount:'800000',spent:'520000'},
      {id:'b3',category:'Hiburan',amount:'500000',spent:'395000'}
    ];
    const budgetsHtml=budgetRows.length?budgetRows.map(b=>{
      const spent=b.spent?+b.spent:0, pct=b.amount?Math.min(100,spent/+b.amount*100):0, cls=pct>=100?'danger':pct>=80?'warn':'';
      return `<div class="budget-row"><div class="budget-info"><b>${esc(b.category||'Anggaran')}</b><span>${money(spent)} / ${money(b.amount)}</span></div><div class="progress ${cls}"><span style="width:${pct}%"></span></div></div>`;
    }).join(''):'<div class="empty-state">Belum ada anggaran. Buat batas pengeluaran per kategori untuk mulai mengontrol rencana.</div>';
    $('#view-container').innerHTML=`
      <div class="page-head"><div><div class="eyebrow">OVERVIEW / PERSONAL FINANCE</div><h1>Selamat ${greeting()}, ${esc(state.user?.username||'kamu')}.</h1><p>Ringkasan aktivitas keuanganmu untuk ${esc(monthLabel)}. Angka dihitung dari transaksi terkonfirmasi.</p></div><div class="head-actions"><select class="select-control" id="period-select" aria-label="Periode"><option value="month">Bulan ini</option><option value="week">7 hari terakhir</option><option value="year">Tahun ini</option></select><button class="btn btn-primary" data-action="new-transaction">＋ Catat transaksi</button></div></div>
      <div class="grid kpi-grid">
        <article class="panel kpi-card"><div class="kpi-top"><span>Total pemasukan</span><span class="kpi-symbol positive">↗</span></div><div class="kpi-value mono">${shortMoney(s.income)}</div><div class="kpi-foot"><span class="trend-up">●</span> Pemasukan terkonfirmasi</div></article>
        <article class="panel kpi-card"><div class="kpi-top"><span>Total pengeluaran</span><span class="kpi-symbol negative">↘</span></div><div class="kpi-value mono">${shortMoney(s.expense)}</div><div class="kpi-foot"><span class="trend-down">●</span> Tidak termasuk transfer</div></article>
        <article class="panel kpi-card"><div class="kpi-top"><span>Arus kas bersih</span><span class="kpi-symbol">⌁</span></div><div class="kpi-value mono ${s.net>=0?'positive':'negative'}">${shortMoney(s.net)}</div><div class="kpi-foot">Pemasukan dikurangi pengeluaran</div></article>
        <article class="panel kpi-card"><div class="kpi-top"><span>Saldo tercatat</span><span class="kpi-symbol amber">▣</span></div><div class="kpi-value mono">${shortMoney(s.balance)}</div><div class="kpi-foot">Gabungan akun aktif</div></article>
      </div>
      <div class="grid dashboard-grid">
        <section class="panel chart-card"><div class="panel-head"><div><h2 class="panel-title">Arus kas</h2><div class="panel-sub">Pemasukan dan pengeluaran · ${esc(monthLabel)}</div></div><button class="text-link" data-view="finance">Lihat laporan →</button></div><div class="chart-legend"><span><i class="legend-dot" style="background:var(--green)"></i>Pemasukan</span><span><i class="legend-dot" style="background:var(--red)"></i>Pengeluaran</span></div><div class="chart-area">${svgLineChart(rows)}</div><div class="chart-summary"><div><b class="positive mono">${shortMoney(s.income)}</b><small>Total masuk</small></div><div><b class="negative mono">${shortMoney(s.expense)}</b><small>Total keluar</small></div><div><b class="mono ${s.net>=0?'positive':'negative'}">${shortMoney(s.net)}</b><small>Net cashflow</small></div></div></section>
        <section class="panel chart-card"><div class="panel-head"><div><h2 class="panel-title">Komposisi pengeluaran</h2><div class="panel-sub">Kategori transaksi terkonfirmasi</div></div><button class="text-link" data-view="finance">Detail →</button></div><div class="donut-wrap">${donutChart(cats)}<div class="category-legend">${cats.slice(0,5).map((c,i)=>`<div class="category-row"><span class="category-name"><i style="background:${c.color||['#F2B35E','#67B8E8','#F16D72','#A78BFA','#E28BC4'][i%5]}"></i>${esc(c.name)}</span><b>${Number(c.percent||0).toLocaleString('id-ID')}%</b></div>`).join('')||'<span class="muted">Belum ada pengeluaran</span>'}</div></div><div class="panel-sub">${money(cats.reduce((a,c)=>a+Number(c.amount),0))} total kategori</div></section>
      </div>
      <div class="grid dashboard-lower">
        <section class="panel"><div class="panel-head"><div><h2 class="panel-title">Transaksi terbaru</h2><div class="panel-sub">Aktivitas terakhir di semua akun</div></div><button class="text-link" data-view="finance">Semua transaksi →</button></div>${transactionRows(txs)}</section>
        <div class="grid" style="gap:15px"><section class="panel"><div class="panel-head"><div><h2 class="panel-title">Anggaran aktif</h2><div class="panel-sub">Pantau batas pengeluaranmu</div></div><button class="text-link" data-action="new-budget">＋ Atur</button></div>${budgetsHtml}</section><section class="panel"><div class="panel-head"><div><h2 class="panel-title">Insight yang bisa ditindaklanjuti</h2><div class="panel-sub">Ringkasan berbasis data yang tersedia</div></div><span class="status-tag">TRANSPARAN</span></div><div class="insight-card"><span class="insight-symbol">✦</span><div><b>${s.expense?'Perhatikan kategori terbesar':'Mulai bangun pola pencatatan'}</b><p>${s.expense?`Kategori terbesar pada periode ini: ${esc(s.top)}. Tinjau transaksi terkait sebelum menetapkan batas anggaran.`:'Catat transaksi terkonfirmasi untuk menghasilkan perbandingan periode dan insight yang bisa ditelusuri.'}</p></div></div></section></div>
      </div>`;
    $('#period-select').value=state.period;
  }
  function greeting(){const h=new Date().getHours();return h<11?'pagi':h<15?'siang':h<19?'sore':'malam';}
  function filteredTransactions(){
    const q=($('#transaction-search')?.value||'').toLowerCase();const kind=$('#transaction-kind')?.value||'all';
    return state.transactions.filter(t=>(kind==='all'||t.kind===kind)&&(!q||`${t.description} ${txCategory(t)}`.toLowerCase().includes(q)));
  }
  function transactionActions(t){
    return `<div class="tx-actions"><button class="btn btn-ghost btn-small" data-action="edit-transaction" data-id="${esc(t.id)}" aria-label="Edit ${esc(t.description)}">Edit</button><button class="btn btn-ghost btn-small danger-text" data-action="delete-transaction" data-id="${esc(t.id)}" aria-label="Hapus ${esc(t.description)}">Hapus</button></div>`;
  }
  function updateTransactionListing(){
    const txs=filteredTransactions();
    const rows=txs.map(t=>`<tr><td>${esc(dateFmt(t.occurred_at))}</td><td><b>${esc(t.description)}</b><div class="muted">${esc(t.notes||'')}</div></td><td>${esc(txCategory(t))}</td><td>${esc(accountName(t.source_account_id))}</td><td><span class="type-pill ${t.kind}">${t.kind==='income'?'Pemasukan':t.kind==='expense'?'Pengeluaran':'Transfer'}</span></td><td class="mono ${t.kind==='income'?'positive':t.kind==='expense'?'negative':''}">${esc(txAmount(t))}</td><td>${transactionActions(t)}</td></tr>`).join('');
    const cards=txs.map(t=>`<div class="transaction-card"><div class="transaction-icon">${txIcon(t)}</div><div class="transaction-copy"><b>${esc(t.description)}</b><small>${esc(txCategory(t))} · ${esc(dateFmt(t.occurred_at))}</small>${transactionActions(t)}</div><b class="transaction-amount ${t.kind==='income'?'positive':t.kind==='expense'?'negative':''}">${esc(txAmount(t))}</b></div>`).join('');
    const tbody=$('#transactions-table tbody');if(tbody)tbody.innerHTML=rows||'<tr><td colspan="7"><div class="empty-state">Tidak ada transaksi yang cocok.</div></td></tr>';
    const mobile=$('.mobile-table-cards');if(mobile)mobile.innerHTML=cards||'<div class="empty-state">Tidak ada transaksi yang cocok.</div>';
    const sub=$('.transaction-count');if(sub)sub.textContent=`${txs.length} transaksi ditampilkan · nominal Rupiah`;
  }
  function renderFinance(){
    const s=summary(),cats=categoriesForChart(),txs=filteredTransactions();
    const categories = state.online?state.categoryReport:cats;
    const categoryTable = categories.length?`<div class="table-wrap"><table class="data-table"><thead><tr><th>Kategori</th><th>Total</th><th>Proporsi</th></tr></thead><tbody>${categories.map(c=>`<tr><td>${esc(c.name)}</td><td class="mono">${money(c.amount)}</td><td>${Number(c.percent||0).toLocaleString('id-ID')}%</td></tr>`).join('')}</tbody></table></div>`:'<div class="empty-state">Belum ada kategori pengeluaran pada periode ini.</div>';
    const rows = txs.map(t=>`<tr><td>${esc(dateFmt(t.occurred_at))}</td><td><b>${esc(t.description)}</b><div class="muted">${esc(t.notes||'')}</div></td><td>${esc(txCategory(t))}</td><td>${esc(accountName(t.source_account_id))}</td><td><span class="type-pill ${t.kind}">${t.kind==='income'?'Pemasukan':t.kind==='expense'?'Pengeluaran':'Transfer'}</span></td><td class="mono ${t.kind==='income'?'positive':t.kind==='expense'?'negative':''}">${esc(txAmount(t))}</td><td>${transactionActions(t)}</td></tr>`).join('');
    const mobileRows = txs.map(t=>`<div class="transaction-card"><div class="transaction-icon">${txIcon(t)}</div><div class="transaction-copy"><b>${esc(t.description)}</b><small>${esc(txCategory(t))} · ${esc(dateFmt(t.occurred_at))}</small>${transactionActions(t)}</div><b class="transaction-amount ${t.kind==='income'?'positive':t.kind==='expense'?'negative':''}">${esc(txAmount(t))}</b></div>`).join('');
    $('#view-container').innerHTML=`<div class="page-head"><div><div class="eyebrow">FINANCE / CONTROL CENTER</div><h1>Keuangan</h1><p>Semua angka bersumber dari transaksi yang dikonfirmasi. Transfer internal tidak menambah income/expense.</p></div><div class="head-actions"><button class="btn btn-ghost" data-action="upload-receipt">▧ Unggah mutasi</button><button class="btn btn-primary" data-action="new-transaction">＋ Transaksi baru</button></div></div>
      <div class="grid kpi-grid"><article class="panel kpi-card"><div class="kpi-top">Pemasukan <span class="kpi-symbol positive">↗</span></div><div class="kpi-value mono positive">${shortMoney(s.income)}</div><div class="kpi-foot">Periode terpilih</div></article><article class="panel kpi-card"><div class="kpi-top">Pengeluaran <span class="kpi-symbol negative">↘</span></div><div class="kpi-value mono negative">${shortMoney(s.expense)}</div><div class="kpi-foot">Periode terpilih</div></article><article class="panel kpi-card"><div class="kpi-top">Arus kas bersih <span class="kpi-symbol">⌁</span></div><div class="kpi-value mono ${s.net>=0?'positive':'negative'}">${shortMoney(s.net)}</div><div class="kpi-foot">Net cashflow</div></article><article class="panel kpi-card"><div class="kpi-top">Anggaran tersisa <span class="kpi-symbol amber">▣</span></div><div class="kpi-value mono">${shortMoney(s.budget)}</div><div class="kpi-foot">Berdasarkan anggaran yang dibuat</div></article></div>
      <div class="filters-bar"><select class="select-control" id="finance-period"><option value="month">Bulan ini</option><option value="week">7 hari</option><option value="year">Tahun ini</option><option value="custom">Rentang khusus</option></select><input class="input-control" type="date" id="filter-start" value="${state.start}" style="max-width:145px"><span class="muted">—</span><input class="input-control" type="date" id="filter-end" value="${state.end}" style="max-width:145px"><button class="btn" data-action="apply-filters">Terapkan</button><button class="btn btn-ghost" data-action="export-csv">↓ CSV</button></div>
      <div class="grid report-grid"><section class="panel report-chart"><div class="panel-head"><div><h2 class="panel-title">Pengeluaran per kategori</h2><div class="panel-sub">Donut dan tabel memakai dataset yang sama</div></div><span class="status-tag">CONFIRMED</span></div><div class="donut-wrap">${donutChart(categories)}<div class="category-legend">${categories.slice(0,6).map((c,i)=>`<div class="category-row"><span class="category-name"><i style="background:${c.color||['#F2B35E','#67B8E8','#F16D72','#A78BFA','#E28BC4','#42D6C5'][i%6]}"></i>${esc(c.name)}</span><b>${shortMoney(c.amount)}</b></div>`).join('')||'<span class="muted">Belum ada data</span>'}</div></div></section><section class="panel report-chart"><div class="panel-head"><div><h2 class="panel-title">Kategori teratas</h2><div class="panel-sub">Peringkat berdasarkan nilai transaksi</div></div></div>${categoryTable}</section></div>
      <section class="panel"><div class="panel-head"><div><h2 class="panel-title">Daftar transaksi</h2><div class="panel-sub transaction-count">${txs.length} transaksi ditampilkan · nominal Rupiah</div></div><div class="head-actions"><select class="select-control" id="transaction-kind"><option value="all">Semua jenis</option><option value="income">Pemasukan</option><option value="expense">Pengeluaran</option><option value="transfer">Transfer</option></select></div></div><div class="filters-bar"><div class="search-control"><span class="search-symbol">⌕</span><input id="transaction-search" class="input-control" placeholder="Cari deskripsi atau kategori..."></div><span class="muted" style="font-size:9px">Pilih periode di atas untuk membatasi laporan.</span></div><div class="table-wrap"><table class="data-table" id="transactions-table"><thead><tr><th>Tanggal</th><th>Deskripsi</th><th>Kategori</th><th>Akun</th><th>Jenis</th><th>Nominal</th><th>Aksi</th></tr></thead><tbody>${rows||'<tr><td colspan="7"><div class="empty-state">Belum ada transaksi.</div></td></tr>'}</tbody></table></div><div class="mobile-table-cards">${mobileRows||'<div class="empty-state">Belum ada transaksi.</div>'}</div></section>
      <div class="grid dashboard-lower" style="margin-top:15px"><section class="panel"><div class="panel-head"><div><h2 class="panel-title">Akun & dompet</h2><div class="panel-sub">Saldo dihitung dari transaksi masuk, keluar, dan transfer</div></div><button class="text-link" data-action="new-account">＋ Tambah akun</button></div>${state.accounts.map(a=>`<div class="transaction-row"><div class="transaction-icon">${a.kind==='cash'?'◉':a.kind==='bank'?'▣':'◇'}</div><div class="transaction-copy"><b>${esc(a.name)}</b><small>${esc(a.kind)} · ${esc(a.currency||'IDR')}</small></div><div class="transaction-amount mono">${money(a.balance??a.opening_balance)}</div></div>`).join('')}</section><section class="panel"><div class="panel-head"><div><h2 class="panel-title">Input cepat dengan suara</h2><div class="panel-sub">Rilis 1.1 · perlu izin mikrofon dan konfirmasi</div></div><span class="status-tag" style="color:var(--amber)">ROADMAP</span></div><div class="empty-state" style="padding:18px 10px"><div style="font-size:24px;color:var(--teal)">◖</div><b>Transaksi dari suara</b>Input suara Bahasa Indonesia akan menghasilkan draft yang dapat diperiksa. Belum diaktifkan di build ini; tidak ada perekaman di latar belakang.</div></section></div>`;
    $('#finance-period').value=state.period;
    $('#transaction-kind').value='all';
  }
  function renderInvest(){
    $('#view-container').innerHTML=`<div class="page-head"><div><div class="eyebrow">INVEST / DECISION JOURNAL</div><h1>Investasi</h1><p>Ruang untuk watchlist, tesis, skenario, dan faktor risiko. NEXORA tidak mengeksekusi order atau menjanjikan return.</p></div><div class="head-actions"><button class="btn btn-primary" data-action="new-thesis">＋ Tulis tesis</button></div></div>
      <div class="notice-box"><b>Data pasar belum tersambung.</b> Harga dan berita tidak ditampilkan sampai provider resmi/berlisensi dikonfigurasi. Catatan di bawah adalah riset pribadi, bukan rekomendasi beli/jual.</div>
      <div class="grid invest-grid"><section class="panel"><div class="panel-head"><div><h2 class="panel-title">Watchlist aset</h2><div class="panel-sub">Aset yang sedang kamu pelajari</div></div><button class="text-link" data-action="new-watchlist">＋ Tambah aset</button></div>${state.watchlist.length?state.watchlist.map(a=>`<div class="asset-row"><div class="asset-symbol">${esc(a.symbol.slice(0,4))}</div><div class="asset-copy"><b>${esc(a.asset_name||a.symbol)} <span class="muted">${esc(a.symbol)}</span></b><small>${esc(a.note||'Belum ada catatan')}</small></div><div class="asset-side"><b class="amber">Data tidak tersedia</b><small>belum ada provider</small></div></div>`).join(''):'<div class="empty-state"><b>Watchlist masih kosong</b>Tambahkan ticker atau aset yang ingin dipelajari.</div>'}</section>
      <section class="panel"><div class="panel-head"><div><h2 class="panel-title">Profil risiko & horizon</h2><div class="panel-sub">Tentukan parameter sebelum mengevaluasi ide</div></div></div><div class="setting-row"><div class="setting-main"><span class="setting-icon">⌛</span><div><b>Horizon waktu</b><small>Jangka pendek, menengah, atau panjang.</small></div></div><span class="status-tag">Ditentukan pengguna</span></div><div class="setting-row"><div class="setting-main"><span class="setting-icon">◈</span><div><b>Toleransi risiko</b><small>Konservatif, moderat, atau agresif.</small></div></div><span class="status-tag">Ditentukan pengguna</span></div><div class="setting-row"><div class="setting-main"><span class="setting-icon">⌁</span><div><b>Sumber data</b><small>Harga dan berita provider eksternal.</small></div></div><span class="status-tag" style="color:var(--amber)">Belum tersedia</span></div></section></div>
      <section class="panel" style="margin-top:15px"><div class="panel-head"><div><h2 class="panel-title">Jurnal tesis investasi</h2><div class="panel-sub">Pisahkan alasan, risiko, asumsi, dan kondisi yang membatalkan tesis.</div></div><button class="text-link" data-action="new-thesis">＋ Buat tesis</button></div>${state.theses.length?state.theses.map(t=>`<article class="thesis-card"><div style="display:flex;justify-content:space-between;gap:12px"><h3>${esc(t.symbol)} · ${esc(t.horizon)}</h3><span class="status-tag" style="color:var(--amber)">Edukasi / riset pribadi</span></div><p>${esc(t.thesis)}</p><div class="thesis-meta"><span>Risiko: ${esc(t.risk_profile)}</span><span>Data pasar: unavailable</span><span>${esc(dateFmt(t.created_at))}</span></div><p><b>Risiko utama:</b> ${esc(t.risks||'Belum dicatat')}</p><p><b>Faktor pembatal:</b> ${esc(t.invalidation||'Belum dicatat')}</p><div class="grid" style="grid-template-columns:repeat(3,1fr);gap:7px"><div class="notice-box"><b>Optimistis</b><br>${esc(t.optimistic_case||'Belum diisi')}</div><div class="notice-box"><b>Dasar</b><br>${esc(t.base_case||'Belum diisi')}</div><div class="notice-box"><b>Pesimistis</b><br>${esc(t.pessimistic_case||'Belum diisi')}</div></div></article>`).join(''):'<div class="empty-state"><b>Belum ada tesis tersimpan</b>Dokumentasikan alasan, downside, dan kondisi yang akan membuatmu mengubah pandangan.</div>'}</section>`;
  }
  async function loadCommunity(){
    if(!state.online)return;
    try{
      state.groups=await api('/groups');
      if(!state.activeGroup||!state.groups.some(g=>g.id===state.activeGroup))state.activeGroup=state.groups[0]?.id||null;
      if(state.activeGroup){state.messages=await api(`/groups/${state.activeGroup}/messages`);}
    }catch(e){toast(e.message,'error');}
    renderCommunity();
  }
  async function loadRequests(){
    if(!state.online||!state.activeGroup)return;
    try{state.joinRequests=await api(`/groups/${state.activeGroup}/requests`);}catch(e){state.joinRequests=[];}
  }
  async function connectGroupSocket(){
    if(!state.online||!state.token||!state.activeGroup)return;
    const groupId=state.activeGroup;
    if(state.socket && state.socketGroup===groupId && state.socket.readyState<2)return;
    if(state.socket){state.socket.close();state.socket=null;state.socketGroup=null;}
    try{
      const ticket=await api(`/groups/${groupId}/ws-ticket`,{method:'POST'});
      if(!state.online||state.activeGroup!==groupId)return;
      const base=new URL(state.apiBase);base.protocol=base.protocol==='https:'?'wss:':'ws:';
      base.pathname=base.pathname.replace(/\/$/,'')+`/groups/${groupId}/ws`;
      base.search=new URLSearchParams({ticket:ticket.ticket}).toString();
      state.socket=new WebSocket(base.toString());state.socketGroup=groupId;
      state.socket.onmessage=e=>{try{const p=JSON.parse(e.data);if(p.event==='message.created'&&!state.messages.some(m=>m.id===p.message.id)){state.messages.push(p.message);renderChatBody();}}catch{}};
      state.socket.onclose=()=>{if(state.socketGroup===groupId){state.socket=null;state.socketGroup=null;}};
    }catch(err){toast(`Chat live tidak tersambung: ${err.message}`,'error');}
  }
  function renderCommunity(){
    const groups=state.online?state.groups:DEMO.groups;
    const active=groups.find(g=>g.id===state.activeGroup)||groups[0];
    if(active&&!state.activeGroup)state.activeGroup=active.id;
    if(!state.online)state.messages=DEMO.messages;
    $('#view-container').innerHTML=`<div class="page-head"><div><div class="eyebrow">COMMUNITY / PRIVATE GROUPS</div><h1>Komunitas</h1><p>Ruang diskusi yang sehat. Keuangan pribadi tidak pernah terlihat oleh anggota grup secara default.</p></div><div class="head-actions"><button class="btn btn-ghost" data-action="join-group">⌗ Masukkan kode</button><button class="btn btn-primary" data-action="create-group">＋ Buat grup</button></div></div>
      <div class="community-layout"><section class="panel group-panel"><div class="panel-head"><div><h2 class="panel-title">Grup kamu</h2><div class="panel-sub">${groups.length} grup</div></div><span class="status-tag">PRIVATE</span></div><div class="group-list">${groups.map(g=>`<button class="group-item ${active?.id===g.id?'active':''}" data-group-id="${esc(g.id)}"><span class="group-avatar">${esc(g.name.slice(0,1).toUpperCase())}</span><span><b>${esc(g.name)}</b><small>${esc(g.role||'member')} · ${esc(g.description||'Komunitas')}</small></span></button>`).join('')||'<div class="empty-state">Belum ada grup.<br>Buat grup atau masukkan kode undangan.</div>'}</div>${active?.role==='owner'||active?.role==='admin'?`<div style="margin-top:14px"><button class="btn btn-ghost" style="width:100%" data-action="view-requests">Permintaan bergabung <span class="muted">${state.joinRequests.length||''}</span></button></div>`:''}<div class="notice-box" style="margin-top:14px">Voice room dan video call direncanakan setelah otorisasi serta infrastruktur real-time stabil.</div></section>
      <section class="panel chat-panel">${active?`<div class="chat-head"><div style="display:flex;gap:10px;align-items:center"><span class="group-avatar">${esc(active.name.slice(0,1).toUpperCase())}</span><div><b style="font-size:11px">${esc(active.name)}</b><div class="panel-sub">${esc(active.description||'Diskusi komunitas')}</div></div></div><span class="status-tag">TEXT CHAT</span></div><div class="chat-body" id="chat-body">${(state.messages.length?state.messages:[]).map(chatBubble).join('')||'<div class="group-empty"><img src="/assets/mascot.svg" alt=""><b>Mulai percakapan</b><p>Bagikan pertanyaan, ide, atau sumber yang bermanfaat untuk komunitas.</p></div>'}</div><form class="chat-compose" id="chat-form"><input class="input-control" name="body" maxlength="2000" placeholder="Tulis pesan yang membangun..." required><button class="btn btn-primary" type="submit" aria-label="Kirim pesan">Kirim ↑</button></form>`:`<div class="group-empty"><img src="/assets/mascot.svg" alt=""><b>Belum ada grup</b><p>Buat grup baru atau gabung menggunakan kode undangan.</p></div>`}</section></div>`;
    if(state.online&&active)connectGroupSocket();
  }
  function chatBubble(m){return `<div class="chat-message ${m.user_id===(state.user?.id||'demo-self')?'mine':''}"><div class="chat-avatar">${esc((m.username||'?')[0].toUpperCase())}</div><div class="chat-bubble"><b>${esc(m.username||'Member')}</b><p>${esc(m.body)}</p><small>${esc(dateTimeFmt(m.created_at))}${m.edited?' · diedit':''}</small></div></div>`;}
  function renderChatBody(){const body=$('#chat-body');if(!body)return;body.innerHTML=state.messages.map(chatBubble).join('')||'<div class="empty-state">Belum ada pesan.</div>';body.scrollTop=body.scrollHeight;}
  function renderProfile(){
    const u=state.user||DEMO.user;
    $('#view-container').innerHTML=`<div class="page-head"><div><div class="eyebrow">PROFILE / SECURITY CENTER</div><h1>Profil & keamanan</h1><p>Kontrol akun, sesi, preferensi, dan cara data kamu digunakan.</p></div><div class="head-actions">${state.online?'<button class="btn btn-danger" data-action="logout">Keluar akun</button>':'<button class="btn btn-primary" data-action="auth">Masuk / Daftar</button>'}</div></div>
      <div class="grid profile-grid"><section class="panel profile-card"><div class="profile-big-avatar">${esc((u.username||'N')[0].toUpperCase())}</div><h2>${esc(u.username)}</h2><p>${state.online?'Akun NEXORA aktif':'Pratinjau tanpa akun'}</p><div class="profile-code">${esc(u.profile_code||'—')} <button class="text-link" data-action="copy-profile-code">Salin</button></div><div class="panel-sub" style="margin-top:11px">Kode profil hanya untuk menemukan profil, bukan untuk login atau membuka data finansial.</div></section>
      <section class="panel"><div class="panel-head"><div><h2 class="panel-title">Pengaturan akun</h2><div class="panel-sub">Simpan preferensi yang nyaman untukmu</div></div></div><div class="setting-row"><div class="setting-main"><span class="setting-icon">◐</span><div><b>Tampilan aplikasi</b><small>Dark charcoal atau light clean theme.</small></div></div><button class="btn" data-action="toggle-theme">${state.theme==='dark'?'Dark mode':'Light mode'} · Ganti</button></div><div class="setting-row"><div class="setting-main"><span class="setting-icon">⌘</span><div><b>Koneksi backend</b><small>${state.apiBase?esc(state.apiBase):'Belum ada alamat server yang diatur.'}</small></div></div><button class="btn" data-action="connect-server">Konfigurasi</button></div><div class="setting-row"><div class="setting-main"><span class="setting-icon">♧</span><div><b>Sesi login</b><small>Access token singkat dengan refresh token berotasi.</small></div></div><span class="status-tag">${state.online?'Aktif':'Tidak aktif'}</span></div><div class="setting-row"><div class="setting-main"><span class="setting-icon">⇩</span><div><b>Ekspor transaksi</b><small>Unduh CSV dari data terkonfirmasi milikmu.</small></div></div><button class="btn" data-action="export-csv" ${state.online?'':'disabled'}>Unduh CSV</button></div><div class="setting-row"><div class="setting-main"><span class="setting-icon">⌖</span><div><b>Hapus akun & data</b><small>Fitur penghapusan akun perlu endpoint dan verifikasi tambahan sebelum rilis publik.</small></div></div><span class="status-tag" style="color:var(--amber)">Belum tersedia</span></div></section></div>
      <div class="grid dashboard-lower"><section class="panel"><div class="panel-head"><div><h2 class="panel-title">Privasi secara default</h2><div class="panel-sub">Data sensitif tetap berada di ruang privat pengguna.</div></div><span class="status-tag">PRIVACY FIRST</span></div><div class="insight-card"><span class="insight-symbol">◈</span><div><b>Keuangan pribadi tidak dibagikan ke grup</b><p>Anggota komunitas hanya melihat pesan dan informasi grup. Transaksi, saldo, dan dokumen tidak terbuka untuk anggota lain.</p></div></div><div class="insight-card"><span class="insight-symbol">▧</span><div><b>Dokumen tidak digunakan untuk training</b><p>File mutasi yang diunggah disimpan privat dan harus dihapus sesuai kebijakan retensi; OCR otomatis belum dikonfigurasi.</p></div></div></section><section class="panel"><div class="panel-head"><div><h2 class="panel-title">Pusat bantuan</h2><div class="panel-sub">Hubungi tim support tanpa mengirim data finansial otomatis.</div></div></div><button class="btn btn-primary" style="width:100%;margin-bottom:9px" data-action="support-ticket">Buat tiket bantuan</button><button class="btn" style="width:100%" data-action="help">Buka WhatsApp customer service</button><div class="panel-sub" style="margin-top:9px">WhatsApp hanya dibuka setelah konfirmasi. Tidak ada mutasi/chat privat yang dilampirkan otomatis.</div></section></div>`;
  }
  function render(){
    updateStatus();
    const views={home:renderHome,finance:renderFinance,invest:renderInvest,community:renderCommunity,profile:renderProfile};
    (views[state.view]||renderHome)();
  }
  function showConnectModal(){
    openModal('Hubungkan server NEXORA','Masukkan base URL API backend yang sudah di-deploy. Gunakan HTTPS untuk lingkungan online.',`<form id="connect-form"><div class="field"><label class="label">API Base URL</label><input class="input-control" name="apiBase" type="url" placeholder="https://api.domainmu.com/api/v1" value="${esc(state.apiBase)}" required><div class="field-hint">Untuk development lokal: http://10.0.2.2:8000/api/v1 pada emulator Android atau http://localhost:8000/api/v1 pada browser laptop.</div></div><div class="notice-box"><b>Catatan:</b> file APK dan backend adalah dua komponen berbeda. APK perlu URL backend yang dapat dijangkau perangkat agar sinkronisasi akun, transaksi, dan chat berfungsi.</div><div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Batal</button><button class="btn btn-primary" type="submit">Simpan & uji koneksi</button></div></form>`);
    $('#connect-form').addEventListener('submit',async e=>{
      e.preventDefault();const url=$('[name="apiBase"]',e.target).value.trim().replace(/\/$/,'');
      try{const test=await fetch(url.replace(/\/api\/v1$/,'')+'/health');if(!test.ok)throw new Error('Health check gagal.');await test.json();state.apiBase=url;localStorage.setItem('nexora_api_base',url);closeModal();toast('Server berhasil dijangkau.','success');if(state.token){await loadData();}render();}
      catch(err){toast(`Koneksi gagal: ${err.message}`,'error');}
    });
  }
  function showAuthModal(){
    openModal('Masuk ke NEXORA','Username dan password saja. Tanpa email wajib.',`<div class="head-actions" style="margin-bottom:14px"><button class="btn btn-primary" id="auth-login-tab">Masuk</button><button class="btn" id="auth-register-tab">Buat akun</button></div><form id="auth-form"><input type="hidden" name="mode" value="login"><div class="field"><label class="label">Username</label><input class="input-control" name="username" autocomplete="username" minlength="3" maxlength="32" placeholder="contoh: zamzam_01" required></div><div class="field"><label class="label">Password</label><input class="input-control" name="password" type="password" autocomplete="current-password" minlength="10" maxlength="128" placeholder="Minimal 10 karakter" required></div><div class="notice-box" id="auth-note">Belum punya akun? Pilih Buat akun. Password disimpan dalam bentuk hash Argon2id di backend.</div><div class="modal-actions"><button type="button" class="btn btn-ghost" data-action="recovery">Pulihkan akun</button><button type="submit" class="btn btn-primary" id="auth-submit">Masuk</button></div></form>`);
    const setMode=mode=>{const form=$('#auth-form');form.mode.value=mode;$('#auth-login-tab').className=mode==='login'?'btn btn-primary':'btn';$('#auth-register-tab').className=mode==='register'?'btn btn-primary':'btn';$('#auth-submit').textContent=mode==='login'?'Masuk':'Buat akun';$('#auth-note').innerHTML=mode==='login'?'Password diperiksa oleh backend. Jangan bagikan password atau recovery code.':'Recovery code acak hanya muncul sekali setelah pendaftaran. Simpan dengan aman; tanpa kode ini akun mungkin tidak dapat dipulihkan.';const p=$('[name="password"]',form);p.autocomplete=mode==='login'?'current-password':'new-password';};
    $('#auth-login-tab').onclick=()=>setMode('login');$('#auth-register-tab').onclick=()=>setMode('register');
    $('#auth-form').addEventListener('submit',async e=>{
      e.preventDefault();const f=e.target,mode=f.mode.value;const data={username:f.username.value.trim(),password:f.password.value};
      try{
        const result=await api(`/auth/${mode==='login'?'login':'register'}`,{method:'POST',body:JSON.stringify(data)});
        saveTokens(result);await loadData();closeModal();render();
        if(result.recovery_code){openModal('Simpan recovery code','Kode pemulihan ditampilkan satu kali. Salin dan simpan di tempat aman.',`<div class="profile-code" style="font-size:16px;letter-spacing:.07em">${esc(result.recovery_code)}</div><div class="notice-box"><b>Penting:</b> ${esc(result.recovery_warning||'Simpan kode ini sekarang. Kode tidak dapat ditampilkan ulang.')}</div><div class="modal-actions"><button class="btn" data-action="copy-recovery" data-copy="${esc(result.recovery_code)}">Salin kode</button><button class="btn btn-primary" data-action="close-modal">Saya sudah menyimpan</button></div>`);}
        toast(mode==='login'?'Berhasil masuk.':'Akun berhasil dibuat.','success');
      }catch(err){toast(err.message,'error');}
    });
  }
  function showRecovery(){
    closeModal();openModal('Pulihkan akun','Masukkan recovery code sekali pakai dan password baru.',`<form id="recovery-form"><div class="field"><label class="label">Username</label><input class="input-control" name="username" required></div><div class="field"><label class="label">Recovery code</label><input class="input-control" name="recovery_code" placeholder="NX-XXXXXX-XXXXXX-XXXXXX" required></div><div class="field"><label class="label">Password baru</label><input class="input-control" name="new_password" type="password" minlength="10" maxlength="128" required></div><div class="notice-box">Recovery code akan diganti setelah digunakan, dan semua sesi aktif akan dicabut.</div><div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Batal</button><button type="submit" class="btn btn-primary">Pulihkan</button></div></form>`);
    $('#recovery-form').onsubmit=async e=>{e.preventDefault();const f=e.target;try{const r=await api('/auth/recovery/redeem',{method:'POST',body:JSON.stringify({username:f.username.value,recovery_code:f.recovery_code.value,new_password:f.new_password.value})});openModal('Password diperbarui','Simpan recovery code baru.',`<div class="profile-code">${esc(r.new_recovery_code)}</div><div class="notice-box">${esc(r.warning)}</div><div class="modal-actions"><button class="btn btn-primary" data-action="close-modal">Selesai</button></div>`);toast('Pemulihan akun berhasil.','success');}catch(err){toast(err.message,'error');}};
  }
  function newTransactionModal(existing=null){
    if(!state.online){toast('Mode pratinjau: sambungkan server dan masuk untuk menyimpan transaksi pribadi.','error');return;}
    const accounts=state.accounts.filter(a=>!a.archived);const incomeCats=state.categories.filter(c=>c.kind==='income'),expenseCats=state.categories.filter(c=>c.kind==='expense');
    const localDate = d => { const x=new Date(d); return new Date(x.getTime()-x.getTimezoneOffset()*60000).toISOString().slice(0,16); };
    const tx=existing||{kind:'expense',amount:'',occurred_at:new Date().toISOString(),description:'',source_account_id:accounts[0]?.id||'',target_account_id:'',category_id:expenseCats[0]?.id||'',notes:''};
    const formTitle=existing?'Edit transaksi':'Catat transaksi';
    const formIntro=existing?'Perubahan akan langsung memperbarui laporan setelah disimpan.':'Masukkan transaksi secara manual. Data baru dihitung setelah dikonfirmasi.';
    openModal(formTitle,formIntro,`<form id="transaction-form"><div class="field"><label class="label">Jenis transaksi</label><select class="select-control" name="kind"><option value="expense">Pengeluaran</option><option value="income">Pemasukan</option><option value="transfer">Transfer antar akun</option></select></div><div class="form-grid"><div class="field"><label class="label">Nominal (IDR)</label><input class="input-control" name="amount" type="number" min="1" step="1" placeholder="0" required></div><div class="field"><label class="label">Tanggal</label><input class="input-control" name="occurred_at" type="datetime-local" required></div></div><div class="field"><label class="label">Deskripsi</label><input class="input-control" name="description" maxlength="140" placeholder="Contoh: makan siang" required></div><div class="field"><label class="label">Akun asal / akun penerima</label><select class="select-control" name="source_account_id" required>${accounts.map(a=>`<option value="${esc(a.id)}">${esc(a.name)}</option>`).join('')}</select></div><div class="field" id="target-account-field" hidden><label class="label">Akun tujuan transfer</label><select class="select-control" name="target_account_id">${accounts.map(a=>`<option value="${esc(a.id)}">${esc(a.name)}</option>`).join('')}</select></div><div class="field" id="category-field"><label class="label">Kategori</label><select class="select-control" name="category_id">${expenseCats.map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('')}</select></div><div class="field"><label class="label">Catatan (opsional)</label><textarea class="textarea-control" name="notes" maxlength="2000" placeholder="Detail tambahan..."></textarea></div><div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Batal</button><button type="submit" class="btn btn-primary">${existing?'Simpan perubahan':'Simpan transaksi'}</button></div></form>`,{wide:true});
    const form=$('#transaction-form');
    form.kind.value=tx.kind; form.amount.value=tx.amount||''; form.occurred_at.value=localDate(tx.occurred_at); form.description.value=tx.description||''; form.source_account_id.value=tx.source_account_id||accounts[0]?.id||''; form.notes.value=tx.notes||'';
    form.kind.onchange=()=>{const transfer=form.kind.value==='transfer',kind=form.kind.value;$('#target-account-field').hidden=!transfer;$('#category-field').hidden=transfer;const cat=form.category_id;cat.innerHTML=(kind==='income'?incomeCats:expenseCats).map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('');form.target_account_id.required=transfer;cat.required=!transfer;};
    form.kind.onchange();
    if(tx.category_id)form.category_id.value=tx.category_id;
    if(tx.target_account_id)form.target_account_id.value=tx.target_account_id;
    form.onsubmit=async e=>{e.preventDefault();const f=e.target;const payload={kind:f.kind.value,amount:f.amount.value,currency:tx.currency||'IDR',source_account_id:f.source_account_id.value,target_account_id:f.kind.value==='transfer'?f.target_account_id.value:null,category_id:f.kind.value==='transfer'?null:f.category_id.value,description:f.description.value,notes:f.notes.value,tags:tx.tags||[],occurred_at:new Date(f.occurred_at.value).toISOString()};
      try{await api(existing?`/transactions/${existing.id}`:'/transactions',{method:existing?'PATCH':'POST',body:JSON.stringify(payload)});closeModal();await loadData();render();toast(existing?'Perubahan transaksi tersimpan.':'Transaksi tersimpan dan laporan diperbarui.','success');}catch(err){toast(err.message,'error');}
    };
  }
  function newAccountModal(){
    if(!state.online){toast('Sambungkan server untuk mengelola akun sungguhan.','error');return;}
    openModal('Tambah akun / dompet','Buat sumber saldo pencatatan. Jangan masukkan PIN atau password bank.',`<form id="account-form"><div class="field"><label class="label">Nama akun</label><input class="input-control" name="name" required maxlength="60" placeholder="Contoh: BCA utama"></div><div class="field"><label class="label">Jenis akun</label><select class="select-control" name="kind"><option value="cash">Tunai</option><option value="bank">Rekening bank</option><option value="ewallet">E-wallet</option><option value="card">Kartu</option><option value="investment">Akun investasi</option></select></div><div class="field"><label class="label">Saldo awal</label><input class="input-control" name="opening_balance" type="number" value="0" step="1"></div><div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Batal</button><button class="btn btn-primary">Simpan akun</button></div></form>`);
    $('#account-form').onsubmit=async e=>{e.preventDefault();const f=e.target;try{await api('/accounts',{method:'POST',body:JSON.stringify({name:f.name.value,kind:f.kind.value,opening_balance:f.opening_balance.value,currency:'IDR'})});closeModal();await loadData();render();toast('Akun berhasil dibuat.','success');}catch(err){toast(err.message,'error');}};
  }
  function newBudgetModal(){
    if(!state.online){toast('Sambungkan server untuk mengelola anggaran sungguhan.','error');return;}
    const cats=state.categories.filter(c=>c.kind==='expense');
    openModal('Buat anggaran','Tentukan batas kategori pada periode tertentu.',`<form id="budget-form"><div class="field"><label class="label">Kategori</label><select class="select-control" name="category_id">${cats.map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('')}</select></div><div class="field"><label class="label">Batas anggaran (IDR)</label><input class="input-control" name="amount" type="number" min="1" required></div><div class="form-grid"><div class="field"><label class="label">Mulai</label><input class="input-control" name="starts_on" type="date" value="${dateInput(monthStart)}" required></div><div class="field"><label class="label">Berakhir</label><input class="input-control" name="ends_on" type="date" value="${dateInput(new Date(today.getFullYear(),today.getMonth()+1,0))}" required></div></div><div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Batal</button><button class="btn btn-primary">Simpan anggaran</button></div></form>`);
    $('#budget-form').onsubmit=async e=>{e.preventDefault();const f=e.target;try{await api('/budgets',{method:'POST',body:JSON.stringify({category_id:f.category_id.value,amount:f.amount.value,starts_on:f.starts_on.value,ends_on:f.ends_on.value,threshold_percent:80})});closeModal();await loadData();render();toast('Anggaran dibuat.','success');}catch(err){toast(err.message,'error');}};
  }
  function newWatchlistModal(){
    openModal('Tambah aset ke watchlist','Harga belum tersedia karena provider resmi belum tersambung.',`<form id="watchlist-form"><div class="field"><label class="label">Kode ticker / simbol</label><input class="input-control" name="symbol" maxlength="24" placeholder="BBCA, TLKM, BTC-IDR..." required></div><div class="field"><label class="label">Nama aset (opsional)</label><input class="input-control" name="asset_name" maxlength="80" placeholder="Nama perusahaan atau aset"></div><div class="field"><label class="label">Catatan</label><input class="input-control" name="note" maxlength="240" placeholder="Hal yang ingin dipantau"></div><div class="notice-box">NEXORA tidak akan membuat harga atau berita pasar. Data pasar diberi status unavailable sampai provider berlisensi dikonfigurasi.</div><div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Batal</button><button class="btn btn-primary">Simpan watchlist</button></div></form>`);
    $('#watchlist-form').onsubmit=async e=>{e.preventDefault();const f=e.target;try{if(state.online){await api('/watchlist',{method:'POST',body:JSON.stringify({symbol:f.symbol.value,asset_name:f.asset_name.value,note:f.note.value})});await loadData();}else{state.watchlist.push({id:crypto.randomUUID(),symbol:f.symbol.value.toUpperCase(),asset_name:f.asset_name.value,note:f.note.value});}closeModal();render();toast('Aset ditambahkan ke watchlist.','success');}catch(err){toast(err.message,'error');}};
  }
  function newThesisModal(){
    if(!state.online){toast('Login dan hubungkan server untuk menyimpan jurnal pribadi.','error');return;}
    openModal('Tulis tesis investasi','Pisahkan fakta, asumsi, skenario, risiko, dan faktor pembatal.',`<form id="thesis-form"><div class="form-grid"><div class="field"><label class="label">Simbol aset</label><input class="input-control" name="symbol" required maxlength="24" placeholder="BBCA"></div><div class="field"><label class="label">Horizon waktu</label><select class="select-control" name="horizon"><option>Jangka pendek</option><option>Jangka menengah</option><option>Jangka panjang</option></select></div><div class="field"><label class="label">Profil risiko</label><select class="select-control" name="risk_profile"><option>Konservatif</option><option>Moderat</option><option>Agresif</option></select></div></div><div class="field"><label class="label">Tesis / alasan utama</label><textarea class="textarea-control" name="thesis" required minlength="10" placeholder="Apa yang ingin diuji dan mengapa?"></textarea></div><div class="field"><label class="label">Risiko yang perlu diperhatikan</label><textarea class="textarea-control" name="risks"></textarea></div><div class="field"><label class="label">Faktor pembatal tesis</label><textarea class="textarea-control" name="invalidation"></textarea></div><div class="form-grid"><div class="field"><label class="label">Skenario optimistis</label><textarea class="textarea-control" name="optimistic_case"></textarea></div><div class="field"><label class="label">Skenario dasar</label><textarea class="textarea-control" name="base_case"></textarea></div></div><div class="field"><label class="label">Skenario pesimistis</label><textarea class="textarea-control" name="pessimistic_case"></textarea></div><div class="notice-box">Ini jurnal edukasi/riset pribadi, bukan saran beli/jual. Harga pasar tidak disediakan dalam versi ini.</div><div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Batal</button><button class="btn btn-primary">Simpan tesis</button></div></form>`,{wide:true});
    $('#thesis-form').onsubmit=async e=>{e.preventDefault();const f=e.target,payload=Object.fromEntries(new FormData(f));try{await api('/investment/theses',{method:'POST',body:JSON.stringify(payload)});closeModal();await loadData();render();toast('Tesis tersimpan.','success');}catch(err){toast(err.message,'error');}};
  }
  function createGroupModal(){
    if(!state.online){toast('Login dan hubungkan server untuk membuat grup sungguhan.','error');return;}
    openModal('Buat grup komunitas','Buat ruang diskusi dengan aturan yang jelas.',`<form id="group-form"><div class="field"><label class="label">Nama grup</label><input class="input-control" name="name" minlength="3" maxlength="80" required placeholder="Contoh: Financial Growth Circle"></div><div class="field"><label class="label">Deskripsi</label><textarea class="textarea-control" name="description" maxlength="320" placeholder="Apa tujuan grup ini?"></textarea></div><div class="field"><label class="label">Aturan grup</label><textarea class="textarea-control" name="rules" maxlength="2000">Saling menghormati, sertakan sumber saat berbagi informasi, dan hindari janji keuntungan.</textarea></div><div class="notice-box">Kode undangan grup berbeda dari kode profil. Kode hanya digunakan untuk mengajukan permintaan bergabung.</div><div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Batal</button><button class="btn btn-primary">Buat grup</button></div></form>`);
    $('#group-form').onsubmit=async e=>{e.preventDefault();const f=e.target;try{const r=await api('/groups',{method:'POST',body:JSON.stringify({name:f.name.value,description:f.description.value,rules:f.rules.value})});state.activeGroup=r.id;await loadCommunity();openModal('Grup dibuat','Salin kode undangan ini. Kode hanya ditampilkan sekali.',`<div class="profile-code">${esc(r.invite_code)}</div><div class="notice-box"><b>Jaga kode ini.</b> Bagikan hanya kepada orang yang ingin kamu undang. Anggota tetap perlu meminta bergabung sesuai kebijakan approval.</div><div class="modal-actions"><button class="btn" data-action="copy-code" data-copy="${esc(r.invite_code)}">Salin kode</button><button class="btn btn-primary" data-action="close-modal">Selesai</button></div>`);toast('Grup berhasil dibuat.','success');}catch(err){toast(err.message,'error');}};
  }
  function joinGroupModal(){
    if(!state.online){toast('Login dan hubungkan server untuk bergabung.','error');return;}
    openModal('Gabung dengan kode','Masukkan kode undangan grup. Kamu akan melihat preview sebelum meminta bergabung.',`<form id="join-preview-form"><div class="field"><label class="label">Kode grup</label><input class="input-control" name="invite_code" required placeholder="NXG-..."></div><div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Batal</button><button class="btn btn-primary">Lihat grup</button></div></form>`);
    $('#join-preview-form').onsubmit=async e=>{e.preventDefault();const code=e.target.invite_code.value.trim();try{const g=await api(`/groups/preview/${encodeURIComponent(code)}`);openModal('Preview grup', 'Periksa informasi sebelum mengirim permintaan.',`<h3 style="margin:0 0 7px;font:800 14px Manrope">${esc(g.name)}</h3><p class="muted" style="font-size:10px">${esc(g.description)}</p><div class="notice-box"><b>Owner:</b> ${esc(g.owner_username)}<br><b>Aturan:</b> ${esc(g.rules)}</div><div class="modal-actions"><button class="btn" data-action="close-modal">Batal</button><button class="btn btn-primary" data-action="request-join" data-invite="${esc(code)}">Minta bergabung</button></div>`);}catch(err){toast(err.message,'error');}};
  }
  function showJoinRequests(){
    if(!state.online||!state.activeGroup){toast('Pilih grup milikmu terlebih dahulu.','error');return;}
    loadRequests().then(()=>{
      openModal('Permintaan bergabung','Owner/admin dapat menyetujui atau menolak permintaan.',`${state.joinRequests.map(r=>`<div class="setting-row"><div><b>${esc(r.username)}</b><small>${esc(dateTimeFmt(r.created_at))}</small></div><div class="head-actions"><button class="btn btn-primary" data-action="approve-request" data-request="${esc(r.id)}">Terima</button><button class="btn btn-danger" data-action="reject-request" data-request="${esc(r.id)}">Tolak</button></div></div>`).join('')||'<div class="empty-state">Tidak ada permintaan yang menunggu.</div>'}<div class="modal-actions"><button class="btn" data-action="close-modal">Tutup</button></div>`);
    });
  }
  function supportTicketModal(){
    if(!state.online){toast('Login dan hubungkan server untuk membuat tiket.','error');return;}
    openModal('Buat tiket bantuan','Hanya informasi yang kamu tulis di tiket ini yang dikirim ke support.',`<form id="ticket-form"><div class="field"><label class="label">Kategori</label><select class="select-control" name="category"><option>Masalah akun</option><option>Transaksi</option><option>Laporan</option><option>Komunitas</option><option>Bug aplikasi</option><option>Lainnya</option></select></div><div class="field"><label class="label">Judul tiket</label><input class="input-control" name="title" maxlength="120" required></div><div class="field"><label class="label">Deskripsi</label><textarea class="textarea-control" name="description" minlength="10" maxlength="4000" required></textarea></div><div class="notice-box">Jangan menulis password, PIN, CVV, atau mengunggah foto mutasi kecuali memang diperlukan dan kamu sadar apa yang dibagikan.</div><div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Batal</button><button class="btn btn-primary">Kirim tiket</button></div></form>`);
    $('#ticket-form').onsubmit=async e=>{e.preventDefault();const f=e.target;try{const r=await api('/support/tickets',{method:'POST',body:JSON.stringify({category:f.category.value,title:f.title.value,description:f.description.value})});closeModal();toast(`Tiket ${r.ticket_code} berhasil dibuat.`,'success');}catch(err){toast(err.message,'error');}};
  }
  function receiptModal(){
    if(!state.online){toast('Login dan hubungkan server untuk mengunggah dokumen pribadi.','error');return;}
    openModal('Unggah mutasi / struk','File disimpan privat sebagai draft. OCR otomatis belum dikonfigurasi.',`<form id="receipt-form"><div class="field"><label class="label">Pilih foto atau PDF</label><input class="input-control" name="file" type="file" accept="image/jpeg,image/png,application/pdf" required></div><div class="notice-box"><b>Privasi:</b> JPG, PNG, PDF maksimal 8 MB. Dokumen tidak dipakai untuk training. Versi ini menyimpan file sebagai draft manual; isi transaksi harus diperiksa dan dikonfirmasi.</div><div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Batal</button><button class="btn btn-primary">Unggah</button></div></form>`);
    $('#receipt-form').onsubmit=async e=>{e.preventDefault();const file=e.target.file.files[0];if(!file)return;if(file.size>8*1024*1024){toast('Ukuran file maksimal 8 MB.','error');return;}const base64=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(String(r.result).split(',')[1]);r.onerror=reject;r.readAsDataURL(file);});try{const r=await api('/receipts',{method:'POST',body:JSON.stringify({filename:file.name,mime_type:file.type,content_base64:base64})});closeModal();showReceiptReview(r);toast('Dokumen diunggah sebagai draft.','success');}catch(err){toast(err.message,'error');}};
  }
  async function showReceiptReview(receipt){
    openModal('Tinjau draft dokumen','OCR belum aktif. Isi detail transaksi secara manual lalu konfirmasi.',`<div class="notice-box"><b>${esc(receipt.filename)}</b><br>${esc(receipt.message)}</div><form id="receipt-review-form"><div class="field"><label class="label">Jenis transaksi</label><select class="select-control" name="kind"><option value="expense">Pengeluaran</option><option value="income">Pemasukan</option></select></div><div class="form-grid"><div class="field"><label class="label">Nominal</label><input class="input-control" type="number" name="amount" min="1" required></div><div class="field"><label class="label">Tanggal</label><input class="input-control" type="datetime-local" name="occurred_at" value="${new Date().toISOString().slice(0,16)}" required></div></div><div class="field"><label class="label">Deskripsi</label><input class="input-control" name="description" required></div><div class="field"><label class="label">Akun</label><select class="select-control" name="account_id">${state.accounts.map(a=>`<option value="${esc(a.id)}">${esc(a.name)}</option>`).join('')}</select></div><div class="field"><label class="label">Kategori</label><select class="select-control" name="category_id">${state.categories.filter(c=>c.kind==='expense').map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('')}</select></div><div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Simpan sebagai draft</button><button class="btn btn-primary">Konfirmasi transaksi</button></div></form>`,{wide:true});
    const form=$('#receipt-review-form');form.kind.onchange=()=>{const kind=form.kind.value;form.category_id.innerHTML=state.categories.filter(c=>c.kind===kind).map(c=>`<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('');};
    form.onsubmit=async e=>{e.preventDefault();const f=e.target;try{await api(`/receipts/${receipt.id}/confirm`,{method:'POST',body:JSON.stringify({kind:f.kind.value,amount:f.amount.value,occurred_at:new Date(f.occurred_at.value).toISOString(),account_id:f.account_id.value,category_id:f.category_id.value,description:f.description.value})});closeModal();await loadData();render();toast('Transaksi dikonfirmasi dan masuk ke laporan.','success');}catch(err){toast(err.message,'error');}};
  }
  function showHelp(){
    openModal('Pusat bantuan','Hubungi customer service melalui WhatsApp atau buat tiket internal.',`<div class="notice-box"><b>Privasi:</b> WhatsApp hanya dibuka setelah kamu menyetujui. NEXORA tidak akan menyertakan laporan keuangan, foto mutasi, atau pesan privat secara otomatis.</div><div class="setting-row"><div><b>WhatsApp customer service</b><small>Nomor bantuan yang disediakan pemilik aplikasi.</small></div><button class="btn btn-primary" data-action="open-whatsapp">Buka WhatsApp ↗</button></div><div class="setting-row"><div><b>Tiket bantuan internal</b><small>Nomor tiket dan status dapat ditelusuri.</small></div><button class="btn" data-action="support-ticket">Buat tiket</button></div>`);
  }
  async function exportCsv(){
    if(!state.online){toast('Ekspor tersedia setelah kamu masuk ke server.','error');return;}
    try{const res=await fetch(apiUrl('/export/transactions.csv'),{headers:{Authorization:`Bearer ${state.token}`}});if(!res.ok)throw new Error('Ekspor gagal.');const blob=await res.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='nexora-transactions.csv';a.click();URL.revokeObjectURL(url);toast('CSV berhasil diunduh.','success');}catch(e){toast(e.message,'error');}
  }
  async function applyFilters(){
    const start=$('#filter-start')?.value||state.start,end=$('#filter-end')?.value||state.end;
    if(start>end){toast('Tanggal awal harus sebelum tanggal akhir.','error');return;}
    state.start=start;state.end=end;
    if(state.online){try{await loadData();}catch(e){toast(e.message,'error');}}
    render();
  }
  async function applyPeriod(period){
    state.period=period;const now=new Date();let start=new Date(now);
    if(period==='week')start.setDate(now.getDate()-6);else if(period==='year')start=new Date(now.getFullYear(),0,1);else start=new Date(now.getFullYear(),now.getMonth(),1);
    state.start=dateInput(start);state.end=dateInput(now);
    if(state.online){try{await loadData();}catch(e){toast(e.message,'error');}}
    render();
  }
  async function doAction(action, el){
    switch(action){
      case 'close-modal':closeModal();break;
      case 'new-transaction':newTransactionModal();break;
      case 'edit-transaction':{const tx=state.transactions.find(t=>t.id===el.dataset.id);if(tx)newTransactionModal(tx);else toast('Transaksi tidak ditemukan.','error');break;}
      case 'delete-transaction':{const tx=state.transactions.find(t=>t.id===el.dataset.id);if(tx&&confirm(`Hapus transaksi \"${tx.description}\"? Laporan akan dihitung ulang.`)){try{await api(`/transactions/${tx.id}`,{method:'DELETE'});await loadData();render();toast('Transaksi dihapus.','success');}catch(err){toast(err.message,'error');}}break;}
      case 'new-account':newAccountModal();break;
      case 'new-budget':newBudgetModal();break;
      case 'new-watchlist':newWatchlistModal();break;
      case 'new-thesis':newThesisModal();break;
      case 'create-group':createGroupModal();break;
      case 'join-group':joinGroupModal();break;
      case 'view-requests':showJoinRequests();break;
      case 'connect-server':case 'connect':showConnectModal();break;
      case 'auth':showAuthModal();break;
      case 'recovery':showRecovery();break;
      case 'logout':try{await api('/auth/logout',{method:'POST'});}catch{}logoutLocal();break;
      case 'help':showHelp();break;
      case 'support-ticket':closeModal();supportTicketModal();break;
      case 'upload-receipt':receiptModal();break;
      case 'export-csv':exportCsv();break;
      case 'apply-filters':applyFilters();break;
      case 'toggle-theme':toggleTheme();break;
      case 'copy-profile-code':copyText(state.user?.profile_code||DEMO.user.profile_code);break;
      case 'copy-code':case 'copy-recovery':copyText(el.dataset.copy||'');break;
      case 'open-whatsapp':if(confirm('Buka WhatsApp customer service? Tidak ada data keuangan atau chat privat yang akan dilampirkan.'))window.location.href='https://wa.me/628871144516';break;
      case 'request-join':try{const r=await api('/groups/join-requests',{method:'POST',body:JSON.stringify({invite_code:el.dataset.invite})});closeModal();toast(r.message||'Permintaan dikirim.','success');}catch(e){toast(e.message,'error');}break;
      case 'approve-request':case 'reject-request':try{await api(`/groups/${state.activeGroup}/requests/${el.dataset.request}/${action==='approve-request'?'approve':'reject'}`,{method:'POST'});await loadRequests();showJoinRequests();toast(action==='approve-request'?'Anggota diterima.':'Permintaan ditolak.','success');}catch(e){toast(e.message,'error');}break;
      default:break;
    }
  }
  async function copyText(text){try{await navigator.clipboard.writeText(text);toast('Berhasil disalin.','success');}catch{toast(text,'');}}
  function toggleTheme(){state.theme=state.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=state.theme;localStorage.setItem('nexora_theme',state.theme);if(state.online)api('/me',{method:'PATCH',body:JSON.stringify({theme:state.theme})}).catch(()=>{});render();}

  document.addEventListener('click',e=>{
    const view=e.target.closest('[data-view]');if(view){e.preventDefault();setView(view.dataset.view);return;}
    const action=e.target.closest('[data-action]');if(action){e.preventDefault();doAction(action.dataset.action,action);return;}
    const group=e.target.closest('[data-group-id]');if(group){state.activeGroup=group.dataset.groupId;if(state.online){api(`/groups/${state.activeGroup}/messages`).then(m=>{state.messages=m;renderCommunity();}).catch(err=>toast(err.message,'error'));}else{state.messages=DEMO.messages;}renderCommunity();}
  });
  document.addEventListener('submit',async e=>{
    if(e.target.id==='chat-form'){
      e.preventDefault();const body=e.target.body.value.trim();if(!body)return;
      if(!state.online){toast('Chat pratinjau tidak tersimpan ke server. Hubungkan akun untuk chat real-time.','error');return;}
      try{const msg=await api(`/groups/${state.activeGroup}/messages`,{method:'POST',body:JSON.stringify({body})});if(!state.messages.some(m=>m.id===msg.id))state.messages.push(msg);e.target.reset();renderChatBody();}
      catch(err){toast(err.message,'error');}
    }
  });
  document.addEventListener('input',e=>{if(e.target.id==='transaction-search')updateTransactionListing();});
  document.addEventListener('change',e=>{
    if(e.target.id==='period-select')applyPeriod(e.target.value);
    if(e.target.id==='finance-period')applyPeriod(e.target.value);
    if(e.target.id==='transaction-kind')updateTransactionListing();
  });
  $('#theme-toggle').addEventListener('click',toggleTheme);
  $('#banner-connect').addEventListener('click',()=>state.apiBase?showAuthModal():showConnectModal());
  $('#banner-close').addEventListener('click',()=>{$('#preview-banner').hidden=true;});
  $('#notification-button').addEventListener('click',()=>toast('Tidak ada notifikasi baru. Notifikasi push belum diaktifkan di versi ini.'));

  start();
})();
