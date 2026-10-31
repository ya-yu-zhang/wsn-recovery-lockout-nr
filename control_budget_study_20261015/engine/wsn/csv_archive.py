"""Lossless column/delta CSV archive. Exact original strings/hash are verified.
Used only for portable archival; no observations or simulation values change.
"""
import gzip,hashlib,json,lzma,re,struct
from pathlib import Path

MAGIC=b'WSNC1\x00'


def pack_delta(values):
    out=bytearray();previous=0
    for v in values:
        delta=int(v)-previous;previous=int(v);u=2*delta if delta>=0 else -2*delta-1
        while u>=128:out.append((u&127)|128);u>>=7
        out.append(u)
    return bytes(out)


def unpack_delta(data,n):
    out=[];u=shift=0;previous=0
    for b in data:
        u|=(b&127)<<shift
        if b&128:shift+=7;continue
        delta=u//2 if not u&1 else -(u//2)-1;previous+=delta;out.append(previous);u=shift=0
    if shift or len(out)!=n:raise ValueError('incomplete encoded column')
    return out


def encode(payload):
    text=payload.decode();newline='\r\n' if '\r\n' in text else '\n';lines=text.splitlines();header=lines[0];rows=[line.split(',') for line in lines[1:]]
    n=len(rows);width=len(header.split(','));columns=[];chunks=[]
    if any(len(r)!=width for r in rows):raise ValueError('quoted/general CSV is outside this simple trace codec')
    for k in range(width):
        tokens=[r[k] for r in rows];kind=None;values=None
        if all(re.fullmatch(r'-?\d+',t) and str(int(t))==t for t in tokens):kind='int';values=[int(t) for t in tokens]
        else:
            for fmt in ('17g','repr'):
                try:
                    fs=[float(t) for t in tokens]
                    if all((format(v,'.17g') if fmt=='17g' else repr(v))==t for v,t in zip(fs,tokens)):
                        kind=fmt;values=[struct.unpack('<Q',struct.pack('<d',v))[0] for v in fs];break
                except ValueError:pass
        if kind is None:
            dictionary=list(dict.fromkeys(tokens));lookup={t:i for i,t in enumerate(dictionary)};kind='dict';values=[lookup[t] for t in tokens]
        data=pack_delta(values);meta=dict(kind=kind,bytes=len(data))
        if kind=='dict':meta['dictionary']=dictionary
        columns.append(meta);chunks.append(data)
    meta=dict(header=header,newline=newline,trailing=text.endswith(newline),rows=n,columns=columns,sha256=hashlib.sha256(payload).hexdigest())
    raw=json.dumps(meta,separators=(',',':')).encode();packed=MAGIC+struct.pack('<I',len(raw))+raw+b''.join(chunks)
    return lzma.compress(packed,preset=6)


def decode(payload):
    data=lzma.decompress(payload)
    if not data.startswith(MAGIC):raise ValueError('wrong CSV archive version')
    pos=len(MAGIC);size=struct.unpack('<I',data[pos:pos+4])[0];pos+=4;meta=json.loads(data[pos:pos+size]);pos+=size;cols=[]
    for c in meta['columns']:
        vs=unpack_delta(data[pos:pos+c['bytes']],meta['rows']);pos+=c['bytes'];kind=c['kind']
        if kind=='int':col=[str(v) for v in vs]
        elif kind=='dict':col=[c['dictionary'][v] for v in vs]
        else:
            fs=[struct.unpack('<d',struct.pack('<Q',v))[0] for v in vs];col=[format(v,'.17g') if kind=='17g' else repr(v) for v in fs]
        cols.append(col)
    if pos!=len(data):raise ValueError('extra archive bytes')
    lines=[meta['header']]+[','.join(r) for r in zip(*cols)]
    output=(meta['newline'].join(lines)+(meta['newline'] if meta['trailing'] else '')).encode()
    if hashlib.sha256(output).hexdigest()!=meta['sha256']:raise ValueError('decoded trace hash mismatch')
    return output

