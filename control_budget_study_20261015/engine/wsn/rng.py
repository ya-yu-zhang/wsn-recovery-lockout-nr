import hashlib

def uniform(seed,*key):
    data=(str(seed)+':'+repr(key)).encode();value=int.from_bytes(hashlib.sha256(data).digest()[:8],'big')
    return (value+.5)/(2**64)
