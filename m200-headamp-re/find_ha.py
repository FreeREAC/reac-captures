import sys, struct, collections
def frames(path, limit=400000):
    d=open(path,'rb').read(); off=24; n=0
    while off+16<=len(d) and n<limit:
        _,_,cap,_=struct.unpack('<IIII', d[off:off+16]); off+=16
        yield d[off:off+cap]; off+=cap; n+=1
mac=lambda b:':'.join(f'{x:02x}' for x in b)
tot=0; srcs=collections.Counter(); hits=collections.Counter(); samples={}
# Do NOT assume an offset: scan the WHOLE frame for the cdea marker.
for p in frames(sys.argv[1]):
    if len(p)<20 or p[12:14]!=b'\x88\x19': continue
    tot+=1; s=mac(p[6:12]); srcs[s]+=1
    body=p[14:]
    i=body.find(b'\xcd\xea')
    if i<0: continue
    op=body[i+2:i+4].hex()
    hits[(s,op)]+=1
    if op=='0403' and (s,op) not in samples:
        samples[(s,op)]=body[i:i+40].hex()
print(f"  0x8819 frames scanned: {tot}")
print("  src MACs:")
for m,c in srcs.most_common(4): print(f"    {m}  x{c}")
print("\n  === ANCHOR CHECK: cdea control ops found (MUST be non-empty) ===")
for (m,o),c in hits.most_common(10): print(f"    {m}  op {o}  x{c}")
if not hits: print("    NONE -> decoder still wrong, do NOT trust any zero below")
print("\n  === op 0403 samples ===")
for (m,o),h in samples.items(): print(f"    {m}: {h}")
