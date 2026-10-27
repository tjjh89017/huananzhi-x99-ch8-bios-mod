import sys,hashlib,zlib,struct,uuid,re
d=open(sys.argv[1],'rb').read()
m=open(sys.argv[2],'rb').read()
ranges={'mainFV':(0x880000,0x510000),'mainFV_nohdr':(0x880078,0x510000-0x78),'mainFV_used':(0x880000,0xb2fe10-0x880000),
 'mainFV_files':(0x880078,0xb2fe10-0x880078),'peiFV':(0xda0000,0x260000),'bios':(0x800000,0x800000),'bios_noNV':(0x880000,0x780000),
 'full':(0,0x1000000),'nv0':(0x800000,0x40000),'nv1':(0x840000,0x40000),'top64k':(0xff0000,0x10000),'main+fit+pei':(0x880000,0x780000)}
pats=[]
for k,(o,l) in ranges.items():
    b=d[o:o+l]
    for alg in ('sha256','sha1','md5','sha384'):
        h=hashlib.new(alg,b).digest(); pats.append((k+'/'+alg,h)); pats.append((k+'/'+alg+'/rev',h[::-1]))
    c=zlib.crc32(b)&0xffffffff; pats.append((k+'/crc32',struct.pack('<I',c)))
    pats.append((k+'/crc32be',struct.pack('>I',c)))
for name,p in pats:
    for img,label in ((d,'orig'),(m,'mod')):
        hits=[hex(x.start()) for x in re.finditer(re.escape(p),img)]
        if hits: print(name,label,hits[:5])
# FV GUID references
for g in ['5C60F367-A505-419A-859E-2A4FF6CA6FE5','61C0F511-A691-4F54-974F-B9A42172CE53']:
    b=uuid.UUID(g).bytes_le
    print(g,'refs',[hex(x.start()) for x in re.finditer(re.escape(b),d)])
# references to the end-of-used-space or free-space size
for v in (0xb2fe10,0x2601f0,0xffb2fe10,0x2b2fe10):
    print(hex(v),[hex(x.start()) for x in re.finditer(re.escape(struct.pack('<I',v)),d)][:10])
