from eth_utils import to_checksum_address
from eth_account import Account
from eth_account.internal import transactions

from ether.ether_types import UnsignedEthTx, SignedEthTx, EthSig

from typing import cast, Union


def get_signature(tx: UnsignedEthTx, key: bytes) -> EthSig:
    '''
    Gets a signature for an ethereum transaction under a specified key
    '''
    tmp_tx = tx.copy()
    tmp_tx['to'] = to_checksum_address(tx['to'])
    t = Account.signTransaction(tmp_tx, key)

    return t['v'], t['r'], t['s']


def sign_transaction(
        tx: UnsignedEthTx,
        key: bytes) -> SignedEthTx:
    '''
    Signs an ethereum transaction with a specified key
    '''

    sig = get_signature(tx, key)

    tmp_dict = tx.copy()
    tmp_dict.pop('chainId')

    return SignedEthTx(v=sig[0], r=sig[1], s=sig[2], **tmp_dict)


def serialize(tx: SignedEthTx) -> str:
    '''
    serialize a signed Ethereum transaction
    '''
    temp_tx = tx.copy()

    # NB: serializer wants bytes ¯\_(ツ)_/¯
    #     strip prefix and convert to bytes
    if 'x' in temp_tx['to']:
        temp_tx['to'] = bytes.fromhex(temp_tx['to'][2:])
    else:
        temp_tx['to'] = bytes.fromhex(temp_tx['to'])

    temp_tx_obj = transactions.Transaction.from_dict(temp_tx)

    v = temp_tx.pop('v')
    r = temp_tx.pop('r')
    s = temp_tx.pop('s')

    # NB: the serializer wants the signature passed through
    #     both inside AND outside the object ಠ_ಠ
    return transactions.encode_transaction(temp_tx_obj, (v, r, s)).hex()


def recover_sender(tx: Union[SignedEthTx, str]) -> str:
    '''
    Recover the sender from a signed ethereum transaction
    '''
    if type(tx) == dict:
        t = serialize(cast(SignedEthTx, tx))
    else:
        t = cast(str, tx)

    return Account.recoverTransaction(t)
