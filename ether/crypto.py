from Cryptodome.Hash import keccak

from eth_keys.backends.native import ecdsa


def keccak256(msg: bytes) -> bytes:
    '''
    Does solidity's dumb keccak

    Args:
        msg (bytes): the message to hash
    Returns:
        (bytes): the keccak256 digest
    '''
    keccak_hash = keccak.new(digest_bits=256)
    keccak_hash.update(msg)
    return keccak_hash.digest()


def pow_mod(x: int, y: int, z: int) -> int:
    '''
    int, int, int (or float)
    returns (x^y)mod z
    '''
    number = 1
    while y:
        if y & 1:
            number = number * x % z
        y >>= 1
        x = x * x % z
    return number


def uncompress_pubkey(pubkey: bytes) -> bytes:
    '''
    takes a compressed pubkey, returns the uncompressed pubkey (64 bytes)
    '''
    p = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f
    parity = pubkey[0] - 2
    x = int.from_bytes(pubkey[1:], 'big')
    a = (pow_mod(x, 3, p) + 7) % p
    y = pow_mod(a, (p + 1) // 4, p)
    if y % 2 != parity:
        y = -y % p
    return (x.to_bytes(32, 'big')) + (y.to_bytes(32, 'big'))


def compress_pubkey(pubkey: bytes) -> bytes:
    parity = (pubkey[-1] & 1) + 2
    compressed = bytes([parity]) + pubkey[:32]
    return compressed


def priv_to_pub(privkey: bytes) -> bytes:
    return ecdsa.private_key_to_public_key(privkey)
