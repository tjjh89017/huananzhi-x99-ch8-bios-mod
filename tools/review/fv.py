import sys,struct,uuid
def s8(b): return sum(b)&0xff
def s16(b): return sum(struct.unpack('<%dH'%(len(b)//2),b))&0xffff
d=open(sys.argv[1],'rb').read()
verbose=len(sys.argv)>2
# find volumes in BIOS region
o=0x800000
vols=[]
while o<len(d):
    if d[o+40:o+44]==b'_FVH':
        vlen,=struct.unpack_from('<Q',d,o+32)
        if 0<vlen<=len(d)-o:
            vols.append((o,vlen)); o+=vlen; continue
    o+=16
for v,vlen in vols:
    g=uuid.UUID(bytes_le=d[v+16:v+32])
    attr,hlen,cks,ext=struct.unpack_from('<IHHH',d,v+44)
    rev=d[v+55]
    hok=s16(d[v:v+hlen])==0
    # block map
    bm=[];p=v+56
    while True:
        nb,bl=struct.unpack_from('<II',d,p); p+=8
        if nb==0 and bl==0: break
        bm.append((nb,bl))
    bmtot=sum(a*b for a,b in bm)
    print('FV @%x len %x guid %s attr %08x hlen %x hdrcks_ok %s ext %x rev %d blockmap %s total_ok %s'%(v,vlen,g,attr,hlen,hok,ext,rev,bm,bmtot==vlen))
    pol=0xff if attr&0x800 else 0
    start=v+hlen
    if ext:
        es,=struct.unpack_from('<I',d,v+ext+16); start=v+ext+es
        print('  ext hdr guid',uuid.UUID(bytes_le=d[v+ext:v+ext+16]),'size',hex(es))
    off=v+((start-v+7)&~7)
    end=v+vlen; n=0; files=[]
    while off+24<=end:
        if d[off:off+24]==bytes([pol])*24: break
        hdr=d[off:off+24]
        fg=uuid.UUID(bytes_le=hdr[:16]); ft=hdr[18]; fa=hdr[19]
        size=int.from_bytes(hdr[20:23],'little'); st=hdr[23]
        h=bytearray(hdr); h[17]=0; h[23]=0
        hc=s8(h)==0
        if size<24 or off+size>end:
            print('  BAD size at %x'%off); break
        if fa&0x40: fc=s8(d[off+24:off+size]+bytes([hdr[17]]))==0
        else: fc=hdr[17]==0xAA
        # state: polarity 1 => valid file shows ~st has bits HEADER_CONSTRUCTION|HEADER_VALID|DATA_VALID set
        s = (st^0xff) if pol else st
        stok = (s & 0x07)==0x07 and not (s & 0x08) # deleted bit not set... EFI_FILE_DELETED=0x08? actually 0x08
        files.append((off,size,fg,ft,fa,st))
        if verbose or not(hc and fc and stok) or off%8!=(v%8):
            print('  file %x size %x %s type %02x attr %02x state %02x hdr %s file %s state %s'%(off,size,fg,ft,fa,st,hc,fc,stok))
        off=v+((off+size-v+7)&~7); n+=1
    free=off
    allff=d[free:end]==bytes([pol])*(end-free)
    print('  files %d, free at %x, free bytes %x, rest erased %s'%(n,free,end-free,allff))
    for f in files[-3:]:
        print('   last: %x %x %s type %02x attr %02x state %02x'%f)
