from ether import crypto, rlp

from ether.ether_types import EthSig, EthTx, SignedEthTx, UnsignedEthTx

from typing import cast, List


def hash_to_sign(tx: EthTx) -> bytes:
    '''Get the hash to sign. keccak256 of serialized tx with chainId'''
    return crypto.keccak256(serialize(strip_signature(tx)))


def strip_signature(tx: EthTx) -> UnsignedEthTx:
    '''Strip the signature from a tx. Recover chainId from v if necessary'''
    tmp_tx = cast(dict, tx).copy()
    if 'v' in tx:
        tmp_tx.pop('r')
        tmp_tx.pop('s')
        v = tmp_tx.pop('v')
        tmp_tx['chainId'] = (v - (35 if v % 2 else 36)) // 2
    return cast(UnsignedEthTx, tmp_tx)


def get_signature(tx: UnsignedEthTx, key: bytes) -> EthSig:
    '''Get a signature on a tx under a certain key'''
    if not tx['chainId']:
        raise ValueError('This library enforces EIP-155.')
    return crypto.sign(hash_to_sign(tx), key)


def sign_transaction(
        tx: UnsignedEthTx,
        key: bytes) -> SignedEthTx:
    '''
    Signs an ethereum transaction with a specified key
    '''
    sig = get_signature(tx, key)

    return SignedEthTx(
        to=tx['to'],
        value=tx['value'],
        gas=tx['gas'],
        gasPrice=tx['gasPrice'],
        nonce=tx['nonce'],
        data=tx['data'],
        v=sig[0], r=sig[1], s=sig[2])


def serialize_hex(t: EthTx) -> str:
    return f'0x{serialize(t).hex()}'


def serialize(t: EthTx) -> bytes:
    '''
    serialize a signed Ethereum transaction
    '''
    tx = cast(dict, t)
    v = tx['v'] if 'v' in tx else tx['chainId']
    r = tx['r'] if 'r' in tx else 0
    s = tx['s'] if 's' in tx else 0

    to_serialize: List[bytes] = [
        rlp.i2be_rlp_padded(tx['nonce']),
        rlp.i2be_rlp_padded(tx['gasPrice']),
        rlp.i2be_rlp_padded(tx['gas']),
        bytes.fromhex(tx['to'][2:]),
        rlp.i2be_rlp_padded(tx['value']),
        tx['data'],
        rlp.i2be_rlp_padded(v),
        rlp.i2be_rlp_padded(r),
        rlp.i2be_rlp_padded(s)
    ]

    return rlp.encode(to_serialize)


def deserialize(raw: bytes) -> EthTx:
    decoded = cast(List[bytes], rlp.decode(raw))

    # post-processing step
    nonce = rlp.be2i_rlp(decoded[0])
    gas_price = rlp.be2i_rlp(decoded[1])
    gas = rlp.be2i_rlp(decoded[2])
    to = f'0x{decoded[3].hex()}'
    value = rlp.be2i_rlp(decoded[4])
    data = decoded[5]
    (v, r, s) = [rlp.be2i_rlp(i) for i in decoded[6:]]

    tx = {
        'nonce': nonce,
        'gasPrice': gas_price,
        'gas': gas,
        'to': to,
        'value': value,
        'data': data
    }

    if r == 0:  # unsigned, but serialized with chainId as v
        tx['chainId'] = v
        return cast(UnsignedEthTx, tx)

    # signed
    tx['v'] = v
    tx['r'] = r
    tx['s'] = s
    return cast(SignedEthTx, tx)


def deserialize_hex(hex_raw: str) -> EthTx:
    h = hex_raw if hex_raw[:2] != '0x' else hex_raw[2:]
    return deserialize(bytes.fromhex(h))


def recover_sender(tx: SignedEthTx) -> str:
    pubkey = crypto.recover_pubkey(
        (tx['v'], tx['r'], tx['s']),
        hash_to_sign(tx))
    return crypto.pub_to_addr(pubkey)
