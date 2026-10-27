import sys,struct,re
for f in sys.argv[1:]:
    d=open(f,'rb').read(); print('==',f.split('scratchpad/')[-1],'size=0x%X'%len(d)); o=0
    while o+0x1a<=len(d) and d[o:o+2]==b'\x55\xaa':
        p=struct.unpack_from('<H',d,o+0x18)[0]; j=o+p
        if d[j:j+4]!=b'PCIR': print(' no PCIR at',hex(o)); break
        ven,dev=struct.unpack_from('<HH',d,j+4); rev=d[j+0xC]; cc=d[j+0xD:j+0x10][::-1].hex()
        ln=struct.unpack_from('<H',d,j+0x10)[0]*512; ct=d[j+0x14]; ind=d[j+0x15]
        s=' img@0x%X %04X:%04X class=%s code_type=%d len=0x%X last=%s'%(o,ven,dev,cc,ct,ln,bool(ind&0x80))
        if ct==3:
            init,sig,sub,mach,comp,peoff=struct.unpack_from('<HIHHHH',d,o+2)
            s+=' EfiSig=0x%X subsystem=%d machine=0x%04X compressed=%d peoff=0x%X'%(sig,sub,mach,comp,peoff)
            pe=o+peoff
            if d[pe:pe+2]==b'MZ':
                lf=struct.unpack_from('<I',d,pe+0x3c)[0]; m2=struct.unpack_from('<H',d,pe+lf+4)[0]; s+=' PE.Machine=0x%04X'%m2
        else:
            v=re.findall(rb'[ -~]{6,}',d[o:o+ln])[:3]; s+=' strings=%s'%v
        print(s)
        if ind&0x80 or ln==0: break
        o+=ln
    rest=d[o+ln:] if o+ln<len(d) else b''
    print(' trailing bytes after last image: 0x%X (all FF/00: %s)'%(len(rest), set(rest)<= {0xff,0}))
