import sys
for l in open(sys.argv[1], encoding='utf-8', errors='replace'):
    p=[x.strip() for x in l.split('|')]
    if len(p)<6: continue
    if p[0] in ('Volume','File'):
        name=p[5].lstrip('- ')
        extra=p[6] if len(p)>6 else ''
        if p[0]=='Volume': print('VOL', p[1], p[2], p[3], name)
        else: print('  ', p[2], p[3], p[1][:14].ljust(14), name, extra)
    elif p[0]=='Free space' and 'Volume free' in p[5]: print('  FREE', p[2], p[3])
