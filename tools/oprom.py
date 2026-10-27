import sys,os,struct
def scan(d, base=0):
    out=[]; i=0
    while True:
        i=d.find(b'\x55\xaa',i)
        if i<0 or i+0x1a>len(d): break
        p=struct.unpack_from('<H',d,i+0x18)[0]
        j=i+p
        if p and j+0x18<=len(d) and d[j:j+4]==b'PCIR':
            ven,dev=struct.unpack_from('<HH',d,j+4)
            ln=struct.unpack_from('<H',d,j+0x10)[0]*512
            ct=d[j+0x14]; ind=d[j+0x15]
            extra=''
            if ct==3:
                sub,mach=struct.unpack_from('<HH',d,i+8); extra='EFI subsys=%d machine=%04X'%(sub,mach)
            cc=d[j+0xd:j+0x10][::-1].hex()
            out.append((base+i,'%04X:%04X'%(ven,dev),ct,ln,ind,cc,extra))
        i+=2
    return out
for f in sys.argv[1:]:
    d=open(f,'rb').read()
    for r in scan(d):
        print(os.path.basename(f), 'off=%X ven:dev=%s code=%d len=%X last=%X class=%s %s'%r)
