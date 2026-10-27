import sys,struct
for fn in sys.argv[1:]:
    d=open(fn,'rb').read()
    print(fn, 'sig', d[0x10:0x14].hex())
    flmap0,flmap1,flmap2=struct.unpack_from('<III',d,0x14)
    frba=((flmap0>>16)&0xff)<<4; nr=(flmap0>>24)&7
    fcba=(flmap0&0xff)<<4; nc=(flmap0>>8)&3
    fmba=(flmap1&0xff)<<4
    print(' FLMAP0 %08x FRBA %x NR %d FCBA %x NC %d FMBA %x'%(flmap0,frba,nr,fcba,nc,fmba))
    for i in range(5):
        r,=struct.unpack_from('<I',d,frba+4*i)
        b=(r&0x7fff)<<12; l=((r>>16)&0x7fff)<<12|0xfff
        print('  FLREG%d %08x  %x-%x %s'%(i,r,b,l,'unused' if b>l else ''))
    m=[struct.unpack_from('<I',d,fmba+4*i)[0] for i in range(3)]
    print('  FLMSTR', [hex(x) for x in m])
    c=struct.unpack_from('<III',d,fcba)
    print('  FLCOMP', [hex(x) for x in c])
