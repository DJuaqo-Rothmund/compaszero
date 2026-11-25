import re, json, sys
s=open('logo.svg').read()
els=re.findall(r'<(path|circle|rect) class="cls-1"([^>]*)/>',s)
def attr(a,k):
    m=re.search(k+r'="([^"]*)"',a); return m and m.group(1)
out={'symbol':None,'letters':[],'dots':[],'underlines':[],'tagline':[]}
for t,a in els:
    if t=='path':
        d=attr(a,'d'); nums=[float(x) for x in re.findall(r'-?\d*\.?\d+',d)[:2]]; x,y=nums
        if d.startswith('M241.68,218.93'): out['symbol']=d; continue
        if d.startswith('M292.52,349.57') or d.startswith('M272.15,358.13'): out['underlines'].append(d); continue
        if y>=375: out['tagline'].append(d); continue
        L=len(d)
        (out['letters'] if L>300 else out['dots']).append((x,d))
    elif t=='circle':
        cx,cy,r=float(attr(a,'cx')),float(attr(a,'cy')),float(attr(a,'r'))
        d=f"M{cx-r},{cy}a{r},{r} 0 1,0 {2*r},0a{r},{r} 0 1,0 {-2*r},0Z"
        out['dots'].append((cx,d))
    else:
        x,y,w,h=[float(attr(a,k)) for k in 'x y width height'.split()]
        out['tagline'].append(f"M{x},{y}h{w}v{h}h{-w}Z")
out["letters"].sort(key=lambda p:(p[1].split(",")[1].split("c")[0] and float(re.findall(r"-?\d*\.?\d+",p[1])[1])>=300, p[0])); out['dots'].sort()
out['letters']=[d for _,d in out['letters']]; out['dots']=[d for _,d in out['dots']]
out['underlines'].sort(key=len,reverse=True)
json.dump(out,open(sys.argv[1],'w'))
print({k:(len(v) if isinstance(v,list) else 1) for k,v in out.items()})
