import sys,struct,uuid,re
d=open(sys.argv[1],'rb').read()
def u16(o): return struct.unpack_from('<H',d,o)[0]
# string packages
strpk=[]
for m in re.finditer(rb'en-US\x00',d):
    # header: len3 type1 hdrsize4 stroff4 window32 langname2 lang
    o=m.start()-46
    if o<0: continue
    ln=struct.unpack_from('<I',d,o)[0]
    if (ln>>24)!=4: continue
    ln&=0xFFFFFF; hs,so=struct.unpack_from('<II',d,o+4)
    p=o+so; sid=1; tab={}
    while p<o+ln:
        t=d[p]
        if t==0: break
        if t==0x14:
            e=p+1
            while d[e:e+2]!=b'\0\0': e+=2
            tab[sid]=d[p+1:e].decode('utf-16le','replace'); sid+=1; p=e+2
        elif t==0x21: sid+=u16(p+1); p+=3
        elif t==0x22: sid+=d[p+1]; p+=2
        elif t==0x20: sid+=1; p+=3
        elif t==0x30: p+=d[p+2]
        elif t==0x31: p+=u16(p+2)
        elif t==0x32: p+=struct.unpack_from('<I',d,p+2)[0]
        else: print('unknown str block',hex(t),hex(p)); break
    strpk.append((o,tab)); print('# string pkg en-US at %X, %d strings'%(o,len(tab)))
S=max(strpk,key=lambda x:len(x[1]))[1] if strpk else {}
def s(i): return S.get(i,'#%X'%i)
# form packages
names={0x05:'OneOf',0x06:'CheckBox',0x07:'Numeric',0x0F:'Ref'}
keys=[k.lower() for k in sys.argv[2:]]
for m in re.finditer(rb'\x0e[\x26\xa6\xa7\x27\xa8\x28\xb8\x38]',d):
    o=m.start()-4
    if o<0: continue
    ln=struct.unpack_from('<I',d,o)[0]
    if (ln>>24)!=2: continue
    ln&=0xFFFFFF; end=o+ln; p=o+4
    vs={}; stack=[]; form='?'
    fsguid=str(uuid.UUID(bytes_le=d[p+2:p+18])).upper()
    print('# formset at %X len %X title=%s guid=%s'%(o,ln,s(u16(p+18)),fsguid))
    cur=None
    while p<end:
        op=d[p]; l=d[p+1]&0x7f; sc=d[p+1]>>7
        if l==0: break
        if op==0x24:
            vid=u16(p+18); vs[vid]=d[p+22:p+l].split(b'\0')[0].decode('ascii','replace')
        elif op==0x26:
            vid=u16(p+2); vs[vid]=d[p+26:p+l].split(b'\0')[0].decode('ascii','replace')
        elif op==0x01: form=s(u16(p+4))
        elif op in names:
            pr,hp,qid,vid,off,fl=struct.unpack_from('<HHHHHB',d,p+2)
            name=s(pr)
            cur=None
            if any(k in name.lower() for k in keys):
                supp=[x for x in stack if x.startswith(('SuppressIf','GrayOutIf','DisableIf'))]
                print('%-8s "%s" | form="%s" | VarStore=%s(id %X) | VarOffset=0x%X | QId=0x%X | conds=%s'%(names[op],name,form,vs.get(vid,'?'),vid,off,qid,supp))
                cur=op
        elif op==0x09 and cur:
            print('     option "%s" value=%s%s'%(s(u16(p+2)),d[p+6:p+l].hex(),' (default)' if d[p+4]&0x30 else ''))
        if op==0x29:
            if stack: x=stack.pop()
            if x in names.values(): cur=None
            if x=='Form': form='?'
        elif sc:
            nm={0x0A:'SuppressIf',0x19:'GrayOutIf',0x1E:'DisableIf',0x01:'Form',0x0E:'FormSet'}.get(op, names.get(op,'op%02X'%op))
            if op in (0x0A,0x19,0x1E):
                q=p+l; ex=[]
                while d[q] in (0x12,0x13,0x14,0x15,0x16,0x17,0x46,0x47,0x5F,0x5A,0x2D,0x2E,0x2F,0x30,0x39,0x3A,0x56,0x57):
                    o2=d[q]; l2=d[q+1]&0x7f
                    if o2==0x12: ex.append('Q%X==%d'%(u16(q+2),u16(q+4)))
                    elif o2==0x14: ex.append('Q%X in %s'%(u16(q+2),[u16(q+6+2*i) for i in range(u16(q+4))]))
                    else: ex.append({0x15:'AND',0x16:'OR',0x17:'NOT',0x46:'TRUE',0x47:'FALSE'}.get(o2,'op%02X'%o2))
                    q+=l2
                nm+='('+' '.join(ex)+')'
            stack.append(nm)
        p+=l
