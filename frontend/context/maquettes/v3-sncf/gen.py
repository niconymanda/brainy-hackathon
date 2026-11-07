import html as H
svg=lambda d,c='currentColor',w=22:f'<svg width="{w}" height="{w}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{d}</svg>'
MIC=svg('<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>','#fff',26)
HIST=svg('<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>')
KB=svg('<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>')
OK=svg('<path d="M20 6 9 17l-5-5"/>','#1c8f45',16)
CHECK_BIG=svg('<path d="M20 6 9 17l-5-5"/>','#fff',34)

CSS='''
:root{--royal:#1f4fe0;--gold:#f2b23a;--ink:#141a33;--mut:rgba(20,26,51,.55)}
*{box-sizing:border-box;margin:0}
body{background:#eceef2;font-family:Inter,system-ui,sans-serif;color:var(--ink)}
.board{padding:56px 60px 40px;display:flex;flex-direction:column;align-items:center;gap:30px}
h1{font-size:26px;font-weight:700} h1 small{display:block;text-align:center;font-size:15px;font-weight:500;color:#6b7080;margin-top:6px}
.grid{display:grid;grid-template-columns:repeat(5,360px);gap:34px 30px}
.col{display:flex;flex-direction:column;gap:12px}
.cap{font-size:13px;color:#4b5060;line-height:1.45;padding:0 4px}
.cap b{display:block;font-size:15px;color:var(--ink);margin-bottom:3px}
.cap i{color:#6b7080}
.w{width:360px;height:520px;border-radius:32px;background:#fff;box-shadow:0 20px 50px rgba(20,26,51,.13),0 0 0 1px rgba(20,26,51,.06);position:relative;overflow:hidden;display:flex;flex-direction:column;align-items:center;padding:18px 20px 0}
.top{width:100%;display:flex;justify-content:space-between;align-items:center;height:22px}
.dots{display:flex;gap:6px}.dots i{width:10px;height:10px;border-radius:50%;background:rgba(20,26,51,.12)}
.name{font-size:12px;font-weight:600;letter-spacing:.6px;color:rgba(20,26,51,.4)}
.m{display:block}.m.xl{width:290px;margin-top:4px}.m.l{width:220px}.m.s{width:130px}
.m.glow{filter:drop-shadow(0 0 18px rgba(31,79,224,.35))}
.status{font-size:18px;font-weight:700;text-align:center;margin-top:2px}
.sub{margin-top:6px;font-size:14px;color:var(--mut);text-align:center;line-height:1.45;padding:0 4px}
.live{margin-top:10px;font-size:15px;line-height:1.5;text-align:center;color:var(--ink);padding:0 6px}
.live span{color:rgba(20,26,51,.35)}
.bubble{margin-top:10px;width:100%;background:#f4f6fb;border-radius:18px;padding:12px 14px;font-size:14px;line-height:1.45}
.you{align-self:flex-end;margin-top:10px;background:var(--royal);color:#fff;border-radius:16px 16px 4px 16px;padding:9px 13px;font-size:14px;max-width:85%}
.steps{width:100%;margin-top:12px;display:flex;flex-direction:column;gap:9px;font-size:14px}
.st{display:flex;gap:10px;align-items:center}.st .d{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;background:rgba(52,199,89,.15);flex:none}
.st.run .d{background:rgba(31,79,224,.12)} .st.run .d::after{content:"";width:8px;height:8px;border-radius:50%;background:var(--royal);box-shadow:0 0 0 3px rgba(31,79,224,.25)}
.st.todo{color:rgba(20,26,51,.35)} .st.todo .d{background:rgba(20,26,51,.06)}
.prog{width:100%;height:6px;border-radius:6px;background:rgba(20,26,51,.07);margin-top:14px;overflow:hidden}.prog i{display:block;height:100%;background:var(--royal);border-radius:6px}
.opts{width:100%;margin-top:10px;display:flex;flex-direction:column;gap:7px}
.op{display:flex;justify-content:space-between;align-items:center;border-radius:14px;padding:10px 13px;background:#f4f6fb;font-size:14px}
.op small{display:block;font-size:12px;color:var(--mut);margin-top:1px}
.op b{font-size:16px}.op.best{background:#fff;border:1.5px solid var(--royal)}
.op .tag{font-size:10px;font-weight:700;color:var(--royal);letter-spacing:.4px}
.op.over{opacity:.45} .op.over b{text-decoration:line-through}
.card{width:100%;margin-top:10px;border-radius:20px;background:#fffaf0;border:1.5px solid var(--gold);padding:14px 16px;display:flex;flex-direction:column;gap:5px;font-size:13px}
.card .route{font-weight:700;font-size:15px}.card .meta{color:var(--mut)}.card .big{font-size:28px;font-weight:800}
.row2{display:flex;justify-content:space-between;align-items:flex-end}
.say{margin-top:9px;font-size:12.5px;color:var(--mut);text-align:center}.say b{color:var(--ink)}
.ticket{width:100%;margin-top:10px;border-radius:20px;background:#f4f6fb;padding:14px 16px;font-size:13px;display:flex;flex-direction:column;gap:6px}
.ticket .route{font-weight:700;font-size:15px}.ticket .meta{color:var(--mut)}
.ticket hr{border:none;border-top:1.5px dashed rgba(20,26,51,.15);margin:4px 0}
.done{width:64px;height:64px;border-radius:50%;background:#22b35e;display:grid;place-items:center;margin-top:6px;box-shadow:0 0 0 10px rgba(34,179,94,.12)}
.hist{width:100%;margin-top:12px;display:flex;flex-direction:column;gap:8px}
.hi{border-radius:16px;background:#f4f6fb;padding:11px 14px;display:flex;justify-content:space-between;align-items:center;font-size:14px}
.hi.new{background:#fff;border:1.5px solid rgba(34,179,94,.5)}
.hi small{display:block;font-size:12px;color:var(--mut);margin-top:2px}
.tag2{font-size:11px;font-weight:600;padding:3px 8px;border-radius:99px;white-space:nowrap}
.paid{background:rgba(52,199,89,.16);color:#1c8f45}.dn{background:rgba(31,79,224,.12);color:var(--royal)}
.bar{position:absolute;bottom:18px;left:20px;right:20px;display:flex;justify-content:space-between;align-items:center}
.ic{width:44px;height:44px;border-radius:50%;display:grid;place-items:center;color:rgba(20,26,51,.55);background:rgba(20,26,51,.05)}.ic.active{background:var(--ink);color:#fff}
.mic{width:64px;height:64px;border-radius:50%;background:var(--royal);display:grid;place-items:center;box-shadow:0 8px 24px rgba(31,79,224,.3)}
.mic.on{box-shadow:0 0 0 10px rgba(31,79,224,.14),0 0 0 22px rgba(31,79,224,.07),0 8px 24px rgba(31,79,224,.3)}
.mic.off{background:#c9cfdb;box-shadow:none}
.hint{position:absolute;bottom:96px;left:0;right:0;text-align:center;font-size:12px;color:rgba(20,26,51,.4)}
kbd{font-family:inherit;border:1px solid rgba(20,26,51,.18);border-bottom-width:2px;border-radius:6px;padding:0 6px}
.speak{display:inline-flex;gap:3px;align-items:center;margin-left:6px;vertical-align:middle}.speak i{width:3px;border-radius:3px;background:var(--royal)}
'''
def speak(): return '<span class="speak">'+''.join(f'<i style="height:{h}px"></i>' for h in (6,12,16,9,14,7))+'</span>'
def w(body, mic='', hist=False, title='BRAINY'):
    return f'''<div class="w"><div class="top"><div class="dots"><i></i><i></i><i></i></div><span class="name">{title}</span><span style="width:42px"></span></div>{body}
<div class="bar"><div class="ic {'active' if hist else ''}">{HIST}</div><div class="mic {mic}">{MIC}</div><div class="ic">{KB}</div></div></div>'''
M=lambda s,extra='':f'<img class="m {s} {extra}" src="mascot-noshadow.png">'

S=[]
S.append(('Repos','Brainy est ouvert, il attend.',w(M('xl')+'<div class="status">Salut, je suis Brainy</div><div class="sub">Dis-moi ce que tu veux faire</div><div class="hint">Appuie sur <kbd>H</kbd> pour parler</div>')))
S.append(('Écoute','<i>Tu appuies sur H et tu parles.</i> Ta phrase s\'affiche au fur et à mesure.',w(M('l')+'<div class="status">Je t\'écoute…</div><div class="live">« Réserve-moi un billet SNCF pour jeudi, en fin d\'après-midi, entre 17h et 22h, pour aller voir mon père. <span>Pas plus de 80 €…</span> »</div>','on')))
S.append(('Brainy reformule et demande','<i>Brainy :</i> « OK : jeudi 12 novembre, départ entre 17h et 22h, 80 € maximum. Tu pars d\'où, et ton père habite où ? »',w(M('s')+'<div class="status">J\'ai bien compris'+speak()+'</div><div class="steps"><div class="st"><span class="d">'+OK+'</span>Jeudi 12 novembre</div><div class="st"><span class="d">'+OK+'</span>Départ entre 17h et 22h</div><div class="st"><span class="d">'+OK+'</span>80 € maximum, le moins cher</div><div class="st todo"><span class="d"></span>Départ et arrivée ?</div></div><div class="bubble">Tu pars d\'où, et ton père habite où ?</div>','on')))
S.append(('Tu réponds','<i>Toi :</i> « Je pars de Paris, il habite à Lyon. »',w(M('s')+'<div class="status">Je t\'écoute…</div><div class="bubble">Tu pars d\'où, et ton père habite où ?</div><div class="you">Je pars de Paris, il habite à Lyon.</div>','on')))
S.append(('L\'agent travaille','<i>Brainy :</i> « Je m\'en occupe, ça prend quelques secondes. » Les étapes se cochent en direct.',w(M('s','glow')+'<div class="status">Je cherche ton train…</div><div class="sub">Sur SNCF Connect</div><div class="steps"><div class="st"><span class="d">'+OK+'</span>SNCF Connect ouvert</div><div class="st"><span class="d">'+OK+'</span>Paris → Lyon, jeudi 12 nov.</div><div class="st"><span class="d">'+OK+'</span>Départs entre 17h et 22h</div><div class="st run"><span class="d"></span>Je compare 7 trains…</div><div class="st todo"><span class="d"></span>Je choisis le moins cher</div></div><div class="prog"><i style="width:68%"></i></div>','off')))
S.append(('Brainy présente le résultat','<i>Brainy :</i> « J\'ai trouvé 7 trains. Le moins cher part à 19h04 et coûte 29 €. »',w(M('s')+'<div class="status">7 trains trouvés'+speak()+'</div><div class="opts"><div class="op best"><div><span class="tag">LE MOINS CHER</span><br>19:04 → 21:00<small>Ouigo · direct</small></div><b>29 €</b></div><div class="op"><div>17:30 → 19:26<small>TGV INOUI · direct</small></div><b>54 €</b></div><div class="op"><div>21:04 → 23:00<small>TGV INOUI · direct</small></div><b>61 €</b></div></div><div class="say">1 train au-dessus de 80 € écarté</div>','off')))
S.append(('Confirmation avant paiement','<i>Brainy :</i> « Je m\'apprête à payer 29 € avec ta carte enregistrée. C\'est bon pour toi ? »',w(M('s')+'<div class="status">Je paie ce billet ?'+speak()+'</div><div class="card"><div class="route">Paris Gare de Lyon → Lyon Part-Dieu</div><div class="meta">Jeudi 12 nov. · 19:04 → 21:00 · Ouigo</div><div class="row2"><div class="meta">Carte •••• 4821</div><div class="big">29 €</div></div></div><div class="say">Dis <b>« oui »</b> pour payer ou <b>« non »</b> pour annuler</div>','on')))
S.append(('Paiement','<i>Toi :</i> « Ouais carré, tu peux prendre. » <i>Brainy :</i> « Parfait, je paie. »',w(M('s','glow')+'<div class="status">Je paie…</div><div class="you">Ouais carré, tu peux prendre.</div><div class="steps"><div class="st"><span class="d">'+OK+'</span>Billet ajouté au panier</div><div class="st run"><span class="d"></span>Paiement de 29 €</div><div class="st todo"><span class="d"></span>Billet envoyé par mail</div></div><div class="prog"><i style="width:80%"></i></div>','off')))
S.append(('C\'est réservé','<i>Brainy :</i> « C\'est réservé ! Jeudi 19h04, voiture 7, place 42. Ton billet est dans tes mails. Bon voyage chez ton père ! »',w('<div class="done">'+CHECK_BIG+'</div><div class="status" style="margin-top:14px">C\'est réservé !'+speak()+'</div><div class="ticket"><div class="route">Paris Gare de Lyon → Lyon Part-Dieu</div><div class="meta">Jeudi 12 nov. · 19:04 → 21:00 · Ouigo</div><hr><div class="row2"><div>Voiture 7 · Place 42</div><b style="font-size:18px">29 €</b></div></div><div class="sub" style="margin-top:12px">Billet envoyé par mail et ajouté à l\'historique</div>')))
S.append(('Historique (au clic)','Tout ce que Brainy a fait, avec le prix et le statut.',w('<div class="hist"><div class="hi new"><div>Train Paris → Lyon<small>Jeudi 12 nov., 19:04</small></div><span class="tag2 paid">Payé · 29 €</span></div><div class="hi"><div>Pizza Hut · Uber Eats<small>Mardi, 12:15</small></div><span class="tag2 paid">18,90 €</span></div><div class="hi"><div>RDV médecin · Doctolib<small>Lundi</small></div><span class="tag2 dn">Réservé</span></div></div>',hist=True,title='HISTORIQUE')))
PLANB=('Plan B : rien sous 80 €','<i>Brainy :</i> « Je n\'ai rien trouvé sous 80 € entre 17h et 22h. Le moins cher est à 89 €, ou il y a un train à 22h34 pour 45 €. Je fais quoi ? »',w(M('s')+'<div class="status">Rien sous 80 €'+speak()+'</div><div class="opts"><div class="op"><div>18:00 → 19:56<small>TGV INOUI · au-dessus du budget</small></div><b>89 €</b></div><div class="op best"><div><span class="tag">HORS CRÉNEAU</span><br>22:34 → 00:30<small>Ouigo · direct</small></div><b>45 €</b></div></div><div class="say">Dis <b>« le premier »</b>, <b>« le deuxième »</b> ou <b>« laisse tomber »</b></div>','on'))

def page(items,title,sub):
    cells=''.join(f'<div class="col">{h}<div class="cap"><b>{i+1}. {H.escape(t)}</b>{c}</div></div>' for i,(t,c,h) in enumerate(items))
    return f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="board"><h1>{title}<small>{sub}</small></h1><div class="grid">{cells}</div></div></body></html>'
open('storyboard.html','w').write(page(S,'Brainy en action — billet SNCF','Jeudi, départ entre 17h et 22h, le moins cher, 80 € maximum'))
for i,(t,c,h) in enumerate(S+[PLANB]):
    open(f'screen-{i+1:02d}.html','w').write(f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>{CSS} body{{background:#eceef2;padding:30px}}</style></head><body>{h}</body></html>')
open('planb.html','w').write(page([PLANB],'Plan B','Aucun billet sous 80 € dans le créneau').replace('repeat(5,360px)','360px'))
print(len(S)+1,'screens')
