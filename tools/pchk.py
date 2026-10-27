import sys,re,glob,os
dd=sys.argv[2]
for line in open(sys.argv[1]):
    line=line.strip()
    if not line or line.startswith('#'): continue
    g,t,pp=line.split(None,2)
    pat=pp[2:].split(':')[0]
    rx=re.compile(b''.join(b'.' if pat[i:i+2]=='..' else re.escape(bytes.fromhex(pat[i:i+2])) for i in range(0,len(pat),2)),re.S)
    fs=glob.glob(os.path.join(dd,'Section_PE32_image_%s_*body.bin'%g))
    if not fs: print(g, 'MODULE ABSENT', pat[:24]); continue
    n=sum(len(rx.findall(open(f,'rb').read())) for f in fs)
    # also near-match: first 6 bytes
    n6=sum(len(re.findall(re.escape(bytes.fromhex(pat[:12])) if '..' not in pat[:12] else b'^$',open(f,'rb').read())) for f in fs)
    print(g, os.path.basename(fs[0])[56:].replace('_body.bin',''), 'hits=%d'%n, 'prefix6=%d'%n6, pat[:24])
