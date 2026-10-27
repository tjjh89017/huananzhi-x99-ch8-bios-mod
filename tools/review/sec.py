import sys,struct,uuid,hashlib,re
d=open(sys.argv[1],'rb').read()
for off in (0xb2fe10,0xb30828):
    size=int.from_bytes(d[off+20:off+23],'little')
    f=d[off:off+size]
    print('FILE %x %s size %x'%(off,uuid.UUID(bytes_le=f[:16]),size))
    p=24; secs=[]
    while p<size:
        p=(p+3)&~3
        if p>=size: break
        ss=int.from_bytes(f[p:p+3],'little'); st=f[p+3]
        print('  sec @%x type %02x size %x end %x'%(p,st,ss,p+ss))
        secs.append((st,f[p+4:p+ss])); p+=ss
    print('  sections end exactly at file end:',p==size)
    for st,b in secs:
        if st==0x15: print('  UI:',b.decode('utf-16-le'))
        if st==0x13: print('  DEPEX present', b.hex())
        if st==0x10:
            pe=b; print('  PE sha256',hashlib.sha256(pe).hexdigest(),'len',hex(len(pe)))
            open(sys.argv[2]+'/%x.efi'%off,'wb').write(pe)
            assert pe[:2]==b'MZ'
            lfa,=struct.unpack_from('<I',pe,0x3c)
            print('   PE sig',pe[lfa:lfa+4])
            mach,nsec,_,_,_,opt,ch=struct.unpack_from('<HHIIIHH',pe,lfa+4)
            o=lfa+24
            magic,=struct.unpack_from('<H',pe,o)
            ep,=struct.unpack_from('<I',pe,o+16)
            salign,falign=struct.unpack_from('<II',pe,o+32)
            soi,soh=struct.unpack_from('<II',pe,o+56)
            subsys,=struct.unpack_from('<H',pe,o+68)
            print('   machine %x nsec %d magic %x entry %x salign %x falign %x SizeOfImage %x SizeOfHeaders %x subsystem %x chars %x'%(mach,nsec,magic,ep,salign,falign,soi,soh,subsys,ch))
            nrva,=struct.unpack_from('<I',pe,o+108)
            dirs=[struct.unpack_from('<II',pe,o+112+8*i) for i in range(nrva)]
            print('   reloc dir',dirs[5] if nrva>5 else None,'sec dir',dirs[4] if nrva>4 else None)
            so=o+opt; mx=0
            for i in range(nsec):
                n,vs,va,rs,rp=struct.unpack_from('<8sIIII',pe,so+40*i)
                print('    %-8s va %x vs %x raw %x@%x %s'%(n.rstrip(b'\0').decode(),va,vs,rs,rp,'RAW OOB' if rp+rs>len(pe) else ''))
                mx=max(mx,va+max(vs,rs))
            print('   max section end %x <= SizeOfImage(%x) %s; ep in image %s'%(mx,soi,mx<=((soi+salign-1)//salign*salign),ep<soi))
            strs=set(re.findall(rb'[ -~]{5,}',pe))|set(x.decode('utf-16-le').encode() for x in re.findall(rb'(?:[ -~]\x00){5,}',pe))
            for s in sorted(strs):
                if re.search(rb'(?i)bind|support|start|stop|gop|graphics|rebar|pci|\.pdb|Name',s): print('    str',s[:100])
