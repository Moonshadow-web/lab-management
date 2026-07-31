# Stub for cos-python-sdk-v5 (C extension unavailable on this platform)
import binascii

# _crcfun: SDK imports "from crcmod import _crcfun" for CRC64
# Provide a dummy function
def _crcfun(*args, **kwargs):
    return 0

def mkCrcFun(poly, initCrc=0, rev=True, xorOut=0):
    """Stub: returns a function that computes CRC32."""
    return lambda data: binascii.crc32(data) & 0xFFFFFFFF
