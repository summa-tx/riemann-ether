from eth_account import Account
from eth_account.internal import transactions

from ether.ether_types import UnsignedEthTx, SignedEthTx, EthSig

from typing import cast, Union


def get_signature(tx: UnsignedEthTx, key: bytes) -> EthSig:

    t = Account.signTransaction(tx, key)

    return t['v'], t['r'], t['s']


def sign_transaction(
        tx: UnsignedEthTx,
        key: bytes) -> SignedEthTx:

    sig = get_signature(tx, key)

    tmp_dict = tx.copy()
    tmp_dict.pop('chainId')

    return SignedEthTx(v=sig[0], r=sig[1], s=sig[2], **tmp_dict)


def serialize(tx: SignedEthTx) -> str:
    temp_tx = tx.copy()

    temp_tx_obj = transactions.Transaction.from_dict(temp_tx)

    v = temp_tx.pop('v')
    r = temp_tx.pop('r')
    s = temp_tx.pop('s')

    return transactions.encode_transaction(temp_tx_obj, (v, r, s)).hex()


def recover_sender(tx: Union[SignedEthTx, str]) -> str:
    if type(tx) == dict:
        t = serialize(cast(SignedEthTx, tx))
    else:
        t = cast(str, tx)

    return Account.recoverTransaction(t)
