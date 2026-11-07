exec(open('gen.py').read().split("def page(")[0])
svgi=lambda d,c='#fff',w=30:f'<svg width="{w}" height="{w}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{d}</svg>'
APPS=[('Fichiers','linear-gradient(#6ec3ff,#2a7fff)',svgi('<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>')),
 ('Navigateur','linear-gradient(#ffffff,#e8eefc)',svgi('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>','#2a62e0')),
 ('Mail','linear-gradient(#5fb2ff,#1d6cf2)',svgi('<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>')),
 ('Calendrier','linear-gradient(#fff,#f2f2f2)','<div style="font:700 11px Inter,system-ui,sans-serif;color:#e33;margin-top:4px">JEU.</div><div style="font:600 26px Inter,system-ui,sans-serif;color:#222;line-height:1">12</div>'),
 ('Musique','linear-gradient(#ff6b8a,#f2365d)',svgi('<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>')),
 ('Notes','linear-gradient(#ffe27a,#ffcf33)',svgi('<path d="M5 4h14v16H5zM8 9h8M8 13h8M8 17h5"/>','#7a5a00')),
 ('Réglages','linear-gradient(#b9bec8,#7f8693)',svgi('<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>')),
]
DCSS='''
body{margin:0;width:1600px;height:1000px;overflow:hidden;background:url(wallpaper.png) center/cover;font-family:Inter,system-ui,sans-serif;position:relative}
.menubar{position:absolute;top:0;left:0;right:0;height:30px;background:rgba(255,255,255,.28);backdrop-filter:blur(20px);display:flex;align-items:center;padding:0 18px;gap:20px;font-size:13.5px;color:#111;font-weight:500}
.menubar b{font-weight:700}.menubar .r{margin-left:auto;display:flex;gap:18px}
.dock{position:absolute;bottom:12px;left:50%;transform:translateX(-50%);display:flex;gap:10px;align-items:flex-end;padding:10px 12px;border-radius:26px;background:rgba(255,255,255,.3);backdrop-filter:blur(24px);box-shadow:0 0 0 1px rgba(255,255,255,.35) inset,0 10px 30px rgba(0,0,0,.15)}
.app{width:62px;height:62px;border-radius:15px;display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:0 3px 8px rgba(0,0,0,.18);position:relative}
.app.brainy{background:url(brainy-icon.png) center/cover}
.app.hover{width:84px;height:84px;border-radius:20px;margin:0 6px}
.sep{width:1px;height:56px;background:rgba(0,0,0,.18);margin:0 4px}
.run::after{content:"";position:absolute;bottom:-8px;width:5px;height:5px;border-radius:50%;background:rgba(0,0,0,.55)}
.tip{position:absolute;bottom:112px;padding:6px 12px;border-radius:9px;background:rgba(40,40,48,.82);color:#fff;font-size:14px;font-weight:500;white-space:nowrap}
.cursor{position:absolute;width:26px;height:26px;z-index:50;filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))}
.win{position:absolute;border-radius:14px;background:#fff;box-shadow:0 30px 80px rgba(0,0,0,.28),0 0 0 1px rgba(0,0,0,.08);overflow:hidden}
.chrome{height:46px;background:#f1f3f6;display:flex;align-items:center;gap:14px;padding:0 16px;border-bottom:1px solid #e3e6eb}
.tl{display:flex;gap:8px}.tl i{width:12px;height:12px;border-radius:50%}
.url{flex:1;height:28px;border-radius:8px;background:#fff;border:1px solid #e1e4ea;display:flex;align-items:center;padding:0 12px;font-size:13px;color:#555}
.floating{position:absolute;z-index:20}
.floating .w{box-shadow:0 30px 80px rgba(20,26,51,.35),0 0 0 1px rgba(20,26,51,.08)}
.sn{font-size:14px;color:#1d1d1f}
.snhead{height:60px;background:#0c131f;display:flex;align-items:center;padding:0 28px;color:#fff;gap:30px}
.snlogo{font-weight:800;font-size:20px;letter-spacing:-.3px}.snlogo span{color:#7fe0c4}
.snsum{background:#f3f5f8;padding:18px 28px;display:flex;gap:14px;align-items:center;border-bottom:1px solid #e6e9ee}
.pill{background:#fff;border:1px solid #dfe3ea;border-radius:10px;padding:10px 14px;font-weight:600}
.res{padding:16px 28px;display:flex;flex-direction:column;gap:12px}
.tr{border:1px solid #e3e6eb;border-radius:12px;padding:16px 20px;display:flex;align-items:center;gap:26px;position:relative}
.tr .t{font-size:20px;font-weight:700}.tr .d{color:#6b7280;font-size:13px}.tr .p{margin-left:auto;font-size:22px;font-weight:800}
.tr.sel{border:2.5px solid #1f4fe0;box-shadow:0 0 0 6px rgba(31,79,224,.12)}
.agent{position:absolute;top:-13px;left:18px;background:#1f4fe0;color:#fff;font-size:11.5px;font-weight:700;padding:3px 9px;border-radius:99px;letter-spacing:.3px}
.cap2{position:absolute;top:44px;left:50%;transform:translateX(-50%);background:rgba(20,26,51,.78);color:#fff;font-size:15px;padding:8px 16px;border-radius:99px;z-index:60;white-space:nowrap}
'''
CUR='<svg class="cursor" viewBox="0 0 24 24"><path d="M4 2l16 10-7 1.5L9.5 21z" fill="#111" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg>'
def dock(hover=False, running=False):
    a=''.join(f'<div class="app" style="background:{bg}" title="{n}">{ic}</div>' for n,bg,ic in APPS)
    a=a.replace('<div class="app" style="background:linear-gradient(#ffffff,#e8eefc)"','<div class="app run" style="background:linear-gradient(#ffffff,#e8eefc)"',1)
    return f'<div class="dock">{a}<div class="sep"></div><div class="app brainy {"hover" if hover else ""} {"run" if running else ""}"></div></div>'
def menubar(app): return f'<div class="menubar"><b>{app}</b><span>Fichier</span><span>Édition</span><span>Fenêtre</span><span>Aide</span><span class="r"><span>Lun. 9 nov.</span><span>10:24</span></span></div>'
def browser(x,y,wd,ht,url,content): return f'<div class="win" style="left:{x}px;top:{y}px;width:{wd}px;height:{ht}px"><div class="chrome"><div class="tl"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i></div><div class="url">{url}</div></div>{content}</div>'
def doc(body,cap): return f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>{CSS}{DCSS}</style></head><body><div class="cap2">{cap}</div>{body}</body></html>'

news='<div style="padding:40px 50px;color:#222"><div style="font:700 30px Inter,system-ui,sans-serif">Bonjour Hugo</div><div style="margin-top:8px;color:#777">Tes favoris</div><div style="display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin-top:22px">'+''.join(f'<div style="height:110px;border-radius:14px;background:{c}"></div>' for c in ['#eef2ff','#fff1e6','#e9f8ef','#f5eefe','#eaf6ff','#fdf0f0','#f1f1f1','#fffbe6'])+'</div></div>'
# 1: icon before click
b1=browser(250,90,980,640,'Nouvel onglet',news)+dock(hover=True)+'<div class="tip" style="left:1058px">Brainy</div>'+CUR.replace('class="cursor"','class="cursor" style="left:1110px;top:928px"')
open('desktop-1.html','w').write(doc(menubar('Navigateur')+b1,'1. Hugo clique sur l\'icône Brainy'))
# 2: widget appears, listening
_,_,W2=S[1]
b2=browser(150,90,980,640,'Nouvel onglet',news)+f'<div class="floating" style="right:70px;top:120px">{W2}</div>'+dock(running=True)
open('desktop-2.html','w').write(doc(menubar('Brainy')+b2,'2. Brainy s\'ouvre par-dessus le bureau : Hugo appuie sur H et parle'))
# 3: agent works on SNCF
trains=[('17:30','19:26','TGV INOUI · direct · 1h56','54 €',''),('19:04','21:00','Ouigo · direct · 1h56','29 €','sel'),('21:04','23:00','TGV INOUI · direct · 1h56','61 €','')]
res=''.join(f'<div class="tr {s}">{"<span class=agent>AGENT BRAINY</span>" if s else ""}<div><div class="t">{a} → {b}</div><div class="d">{d}</div></div><div class="p">{p}</div></div>' for a,b,d,p,s in trains)
sn=f'<div class="sn"><div class="snhead"><div class="snlogo">SNCF <span>Connect</span></div><span style="opacity:.7">Train</span><span style="opacity:.7">Car</span><span style="opacity:.7">Mes voyages</span></div><div class="snsum"><div class="pill">Paris → Lyon</div><div class="pill">Jeu. 12 nov.</div><div class="pill">Dès 17:00</div><div class="pill">1 passager</div></div><div class="res">{res}</div></div>'
_,_,W5=S[4]
b3=browser(60,96,1040,700,'sncf-connect.com',sn)+f'<div class="floating" style="right:70px;top:120px">{W5}</div>'+dock(running=True)
open('desktop-3.html','w').write(doc(menubar('Brainy')+b3,'3. L\'agent cherche le train sur SNCF Connect, Brainy raconte ce qu\'il fait'))
print('ok')
