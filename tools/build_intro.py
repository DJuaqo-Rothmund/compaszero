"""Genera docs/brand/intro.svg a partir de las piezas del logo.

Uso: python tools/logo_parts.py /tmp/parts.json   (desde docs/brand)
     python tools/build_intro.py /tmp/parts.json > docs/brand/intro.svg
Ajusta los tiempos en TIMING.
"""
import json, sys, random

TIMING = dict(
    letter_start=0.7, letter_gap=0.38, letter_dur=0.7,   # escritura del grafiti
    dots=3.6, line1=(3.8, 0.55), line2=(4.2, 0.45), tagline=4.7,
)
T = TIMING
random.seed(7)
p = json.load(open(sys.argv[1]))
o, defs = [], []


def spray(d, start, dur, mid):
    defs.append(f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="0" y="0" width="487" height="454"><path d="{d}" pathLength="1" fill="none" stroke="#fff" stroke-width="18" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1 1" stroke-dashoffset="1" visibility="hidden"><set attributeName="visibility" to="visible" begin="{start:.2f}s"/><animate attributeName="stroke-dashoffset" from="1" to="0" begin="{start:.2f}s" dur="{dur}s" fill="freeze"/></path></mask>')
    o.append(f'<path fill="#fff" d="{d}" mask="url(#{mid})"/>')
    dots = ''.join(f'<circle cx="{random.uniform(-12,12):.1f}" cy="{random.uniform(-12,12):.1f}" r="{random.uniform(.3,1):.2f}" fill="#fff"/>' for _ in range(10))
    o.append(f'<g opacity="0"><circle r="9" fill="#fff" opacity=".35" filter="url(#mist)"/>{dots}'
             f'<animateMotion path="{d}" begin="{start:.2f}s" dur="{dur}s" fill="freeze"/>'
             f'<set attributeName="opacity" to="1" begin="{start:.2f}s"/><set attributeName="opacity" to="0" begin="{start+dur:.2f}s"/></g>')


o.append('<g class="sym"><path fill="#fff" d="%s"/><circle class="glow" cx="243.22" cy="153.21" r="11.89"/><circle class="rec" cx="243.22" cy="153.21" r="11.89"/></g>' % p['symbol'])
for i, d in enumerate(p['letters']):
    spray(d, T['letter_start'] + i * T['letter_gap'], T['letter_dur'], f"m{i}")
for i, d in enumerate(p['dots']):
    o.append(f'<path class="pop" d="{d}" style="animation-delay:{T["dots"]+i*0.03:.2f}s"/>')
spray(p['underlines'][0], *T['line1'], "u0")
spray(p['underlines'][1], *T['line2'], "u1")
o.append('<g class="tag">' + ''.join(f'<path d="{d}"/>' for d in p['tagline']) + '</g>')
css = f'''.sym{{opacity:0;transform-origin:243px 153px;animation:in .6s cubic-bezier(.2,.8,.2,1) forwards}}
.rec{{fill:#E5194B;animation:rec 1.6s ease-in-out .6s infinite}}
.glow{{fill:#E5194B;filter:url(#g);opacity:0;animation:halo 1.6s ease-in-out .6s infinite}}
.pop{{fill:#fff;opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .25s ease-out forwards}}
.tag{{fill:#fff;opacity:0;animation:up .5s ease-out {T["tagline"]}s forwards}}
@keyframes in{{from{{opacity:0;transform:scale(.85)}}to{{opacity:1;transform:none}}}}
@keyframes pop{{0%{{opacity:0;transform:scale(0)}}70%{{transform:scale(1.4)}}100%{{opacity:1;transform:none}}}}
@keyframes up{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
@keyframes rec{{0%,100%{{fill:#E5194B}}50%{{fill:#3D0712}}}}
@keyframes halo{{0%,100%{{opacity:.9}}50%{{opacity:0}}}}'''
print(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 486.44 453.66"><title>CompásZero intro</title><defs><filter id="g" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="5"/></filter><filter id="mist" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="4"/></filter>{"".join(defs)}<style>{css}</style></defs><rect width="100%" height="100%" fill="#000"/>' + '\n'.join(o) + '</svg>')
