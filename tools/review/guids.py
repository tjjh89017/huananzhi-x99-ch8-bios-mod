import sys,uuid,struct
G={'DriverBinding':'18A031AB-B443-4D1A-A5C0-0C09261E9F71','ComponentName2':'6A7A5CFF-E8D9-4F70-BADA-75AB3025CE14','ComponentName':'107A772C-D5E1-11D4-9A46-0090273FC14D','GOP':'9042A9DE-23DC-4A38-96FB-7ADED080516A','PciIo':'4CF5B200-68B8-4CA5-9EEC-B23E3F50029A','EdidDiscovered':'1C0C34F6-D380-41FA-A049-8AD06C1A66AA','DevicePath':'09576E91-6D3F-11D2-8E39-00A0C969723B','PciHostBridgeResAlloc':'CF8034BE-6768-4D8B-B739-7CCE683A9FBE','PciRootBridgeIo':'2F707EBB-4A1A-11D4-9A38-0090273FC14D','DxeApriori':'FC510EE7-FFDC-11D4-BD41-0080C73C8881'}
for fn in sys.argv[1:]:
    d=open(fn,'rb').read()
    print(fn, 'ImageBase', hex(struct.unpack_from('<Q',d,struct.unpack_from('<I',d,0x3c)[0]+24+24)[0]))
    for k,v in G.items():
        b=uuid.UUID(v).bytes_le
        if b in d: print('  ',k,'found')
    for pat,name in ((b'\x03\x1a',"1A03"),(b'\x00\x20\x00\x00',"")):
        pass
    import re
    # look for cmp with 0x1a03 / 0x2000 immediates
    print('   occurrences 03 1a:',[hex(m.start()) for m in re.finditer(b'\x03\x1a',d)][:10])
