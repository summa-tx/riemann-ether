import abc
from ether import crypto, rlp

from typing import Any, cast, List, Optional
from ether.ether_types import CeloTxDict, EthSig, EthTxDict


class Immutable:
    '''
    A simple inheritable class that prevents accidental changes to an object.
    '''
    __immutable: bool = False

    def _make_immutable(self) -> None:
        '''
        Prevents any future changes to the object
        '''
        self.__immutable = True

    def __setattr__(self, key: str, value: Any) -> None:
        '''Override __setattr__ to check if immutable is set before setting'''
        if self.__immutable:
            raise TypeError("%r cannot be written to." % self)
        object.__setattr__(self, key, value)


class EthTx(abc.ABC, Immutable):
    '''
    Abstract base class for Ethereum-like transactions. Contains information
    shared by signed and unsigned txns across networks.

    Args:
        nonce: the tx nonce
        gasPrice: the number of wei to pay per unit of gas
        gas: the number of units of gas
        to: the address the tx is address to
        value: the number of wei attached to the tx
        data: bytes to be included in the tx's calldata

    Attributes:
        nonce: the tx nonce
        gasPrice: the number of wei to pay per unit of gas
        gas: the number of units of gas
        to: the address the tx is address to
        value: the number of wei attached to the tx
        data: bytes to be included in the tx's calldata
    '''
    nonce: int
    gasPrice: int
    gas: int
    to: str
    value: int
    data: bytes

    def __ne__(self, other):  # type: ignore
        '''Define != operator'''
        return not self == other

    @classmethod
    @abc.abstractmethod
    def deserialize(cls, raw: bytes) -> 'EthTx':
        '''Deserialize a transaction from raw bytes'''
        ...

    @classmethod
    def deserialize_hex(cls, raw: str) -> 'EthTx':
        '''Serialize a transaction from hex.'''
        r = raw
        if r[:2] == '0x':
            r = r[2:]
        return cls.deserialize(bytes.fromhex(r))

    @abc.abstractmethod
    def serialize(self) -> bytes:
        '''Serialize the transaction to raw bytes.'''
        ...

    def serialize_hex(self) -> str:
        '''Serialize the transaction as hex.'''
        return f'0x{self.serialize().hex()}'

    @abc.abstractmethod
    def sighash(self) -> bytes:
        '''
        Calculate the signature hash of the transaction. This is the digest
        that is signed by the sender.
        '''
        ...

    def to_json_dict(self) -> EthTxDict:
        '''
        Convert the transaction into a simple json dict suitable for RPC usage.
        '''
        return EthTxDict(
            nonce=hex(self.nonce),
            gasPrice=hex(self.gasPrice),
            gas=hex(self.gas),
            to=self.to,
            value=hex(self.value),
            data=f'0x{self.data.hex()}'
        )


class CeloTx(EthTx):
    '''
    Shared base class for Celo transactions. Contains Celo-specific information
    used in Signed and Unsigned variants.

    Attributes:
        gasCurrency: the address of the token to be used as gas
        gasFeeRecipient: the address of the recipient of gas fees
    '''
    gasCurrency: Optional[str]
    gasFeeRecipient: Optional[str]

    def to_json_dict(self) -> CeloTxDict:
        '''
        Convert the transaction into a simple json dict suitable for RPC usage.
        '''
        return CeloTxDict(
            nonce=hex(self.nonce),
            gasPrice=hex(self.gasPrice),
            gas=hex(self.gas),
            gasCurrency=self.gasCurrency,
            gasFeeRecipient=self.gasFeeRecipient,
            to=self.to,
            value=hex(self.value),
            data=f'0x{self.data.hex()}'
        )


class UnsignedEthTx(EthTx):
    '''
    An unsigned Ethereum transaction intended for a specific chain.

    Args:
        nonce: the tx nonce
        gasPrice: the number of wei to pay per unit of gas
        gas: the number of units of gas
        to: the address the tx is address to
        value: the number of wei attached to the tx
        data: bytes to be included in the tx's calldata
        chainId: the EIP-155 chainId identifying the intended destination chain

    Attributes:
        nonce: the tx nonce
        gasPrice: the number of wei to pay per unit of gas
        gas: the number of units of gas
        to: the address the tx is address to
        value: the number of wei attached to the tx
        data: bytes to be included in the tx's calldata
        chainId: the EIP-155 chainId identifying the intended destination chain
    '''
    chainId: int

    def __init__(
            self,
            nonce: int,
            gasPrice: int,
            gas: int,
            to: str,
            value: int,
            data: bytes,
            chainId: int):
        self.nonce = nonce
        self.gasPrice = gasPrice
        self.gas = gas
        self.to = to
        self.value = value
        self.data = data
        self.chainId = chainId
        self._make_immutable()

    def __eq__(self, other):  # type: ignore
        '''Define == operator'''
        if not isinstance(other, type(self)):
            raise TypeError('Unsupported types for equality:'
                            f'{type(self)} and {type(other)}')
        return (
            self.nonce == other.nonce
            and self.gasPrice == other.gasPrice
            and self.gas == other.gas
            and self.to == other.to
            and self.value == other.value
            and self.data == other.data
            and self.chainId == other.chainId
        )

    @classmethod
    def deserialize(cls, raw: bytes) -> 'UnsignedEthTx':
        '''Deserialize a transaction from raw bytes'''
        fake_signed = SignedEthTx.deserialize(raw)
        return fake_signed.as_unsigned()

    def get_signature(self, key: bytes) -> EthSig:
        '''Get a signature on a tx under a certain key'''
        return crypto.sign(self.sighash(), key)

    def serialize(self) -> bytes:
        '''Serialize the transaction to raw bytes.'''
        return self._with_null_signature().serialize()

    def sighash(self) -> bytes:
        '''
        Calculate the signature hash of the transaction. This is the digest
        that is signed by the sender.
        '''
        stripped = self._with_null_signature()
        return crypto.keccak256(stripped.serialize())

    def sign(self, key: bytes) -> 'SignedEthTx':
        '''Return a copy of the transaction signed by the key'''
        signature = self.get_signature(key)
        return SignedEthTx(
            self.nonce,
            self.gasPrice,
            self.gas,
            self.to,
            self.value,
            self.data,
            *signature)

    def with_chainId(self, id: int) -> 'UnsignedEthTx':
        return UnsignedEthTx(
            self.nonce,
            self.gasPrice,
            self.gas,
            self.to,
            self.value,
            self.data,
            id)

    def _with_null_signature(self) -> 'SignedEthTx':
        return SignedEthTx(
            self.nonce,
            self.gasPrice,
            self.gas,
            self.to,
            self.value,
            self.data,
            self.chainId, 0, 0)


class UnsignedCeloTx(CeloTx, UnsignedEthTx):
    '''
    An unsigned Celo transaction intended for a specific chain.

    Args:
        nonce: the tx nonce
        gasPrice: the number of wei to pay per unit of gas
        gas: the number of units of gas
        gasCurrency: the address of the token to be used as gas
        gasFeeRecipient: the address of the recipient of gas fees
        to: the address the tx is address to
        value: the number of wei attached to the tx
        data: bytes to be included in the tx's calldata
        chainId: the EIP-155 chainId identifying the intended destination chain

    Attributes:
        nonce: the tx nonce
        gasPrice: the number of wei to pay per unit of gas
        gas: the number of units of gas
        gasCurrency: the address of the token to be used as gas
        gasFeeRecipient: the address of the recipient of gas fees
        to: the address the tx is address to
        value: the number of wei attached to the tx
        data: bytes to be included in the tx's calldata
        chainId: the EIP-155 chainId identifying the intended destination chain
    '''
    chainId: int

    def __init__(
            self,
            nonce: int,
            gasPrice: int,
            gas: int,
            gasCurrency: Optional[str],
            gasFeeRecipient: Optional[str],
            to: str,
            value: int,
            data: bytes,
            chainId: int):
        self.nonce = nonce
        self.gasPrice = gasPrice
        self.gas = gas
        self.to = to
        self.value = value
        self.data = data
        self.chainId = chainId
        self.gasCurrency = gasCurrency
        self.gasFeeRecipient = gasFeeRecipient
        self._make_immutable()

    def __eq__(self, other):  # type: ignore
        '''Define == operator'''
        if not isinstance(other, type(self)):
            raise TypeError('Unsupported types for equality:'
                            f'{type(self)} and {type(other)}')
        return (
            self.nonce == other.nonce
            and self.gasPrice == other.gasPrice
            and self.gas == other.gas
            and self.gasCurrency == other.gasCurrency
            and self.gasFeeRecipient == other.gasFeeRecipient
            and self.to == other.to
            and self.value == other.value
            and self.data == other.data
            and self.chainId == other.chainId
        )

    @classmethod
    def deserialize(cls, raw: bytes) -> 'UnsignedCeloTx':
        '''Deserialize a transaction from raw bytes'''
        fake_signed = SignedCeloTx.deserialize(raw)
        return fake_signed.as_unsigned()

    def serialize(self) -> bytes:
        '''Serialize the transaction to raw bytes.'''
        return self._with_null_signature().serialize()

    def sign(self, key: bytes) -> 'SignedCeloTx':
        '''Return a copy of the transaction signed by the key'''
        signature = self.get_signature(key)
        return SignedCeloTx(
            self.nonce,
            self.gasPrice,
            self.gas,
            self.gasCurrency,
            self.gasFeeRecipient,
            self.to,
            self.value,
            self.data,
            *signature)

    def _with_null_signature(self) -> 'SignedCeloTx':
        '''
        Return a copy of the txn with a null signature. Used for serializing
        unsigned transactions
        '''
        return SignedCeloTx(
            self.nonce,
            self.gasPrice,
            self.gas,
            self.gasCurrency,
            self.gasFeeRecipient,
            self.to,
            self.value,
            self.data,
            self.chainId, 0, 0)


class SignedEthTx(EthTx):
    '''
    A signed Ethereum transaction.

    Args:
        nonce: the tx nonce
        gasPrice: the number of wei to pay per unit of gas
        gas: the number of units of gas
        to: the address the tx is address to
        value: the number of wei attached to the tx
        data: bytes to be included in the tx's calldata
        v: EIP-155 signature v value
        r: signature r value
        s: signature s value

    Attributes:
        nonce: the tx nonce
        gasPrice: the number of wei to pay per unit of gas
        gas: the number of units of gas
        to: the address the tx is address to
        value: the number of wei attached to the tx
        data: bytes to be included in the tx's calldata
        v: EIP-155 signature v value
        r: signature r value
        s: signature s value
    '''
    v: int
    r: int
    s: int
    tx_id: bytes

    def __init__(
            self,
            nonce: int,
            gasPrice: int,
            gas: int,
            to: str,
            value: int,
            data: bytes,
            v: int,
            r: int,
            s: int):
        self.nonce = nonce
        self.gasPrice = gasPrice
        self.gas = gas
        self.to = to
        self.value = value
        self.data = data
        self.v = v
        self.r = r
        self.s = s
        self._set_tx_id()
        self._make_immutable()

    def __eq__(self, other):  # type: ignore
        '''Define == operator'''
        if not isinstance(other, type(self)):
            raise TypeError('Unsupported types for equality:'
                            f'{type(self)} and {type(other)}')
        return self.tx_id == other.tx_id

    def as_unsigned(self) -> 'UnsignedEthTx':
        '''Return an unsigned copy of the transaction'''
        # if r == 0 it's an unsigned tx anyway
        chainId = self.v if self.r == 0 \
            else (self.v - (35 if self.v % 2 else 36)) // 2
        return UnsignedEthTx(
            nonce=self.nonce,
            gasPrice=self.gasPrice,
            gas=self.gas,
            to=self.to,
            value=self.value,
            data=self.data,
            chainId=chainId)

    @classmethod
    def deserialize(cls, raw: bytes) -> 'SignedEthTx':
        '''Deserialize a transaction from raw bytes'''
        raws = cast(List[bytes], rlp.decode(raw))
        nonce = rlp.be2i_rlp(raws[0])
        gasPrice = rlp.be2i_rlp(raws[1])
        gas = rlp.be2i_rlp(raws[2])
        to = f'0x{raws[3].hex()}'
        value = rlp.be2i_rlp(raws[4])
        data = raws[5]
        (v, r, s) = [rlp.be2i_rlp(i) for i in raws[6:]]

        return SignedEthTx(
            nonce,
            gasPrice,
            gas,
            to,
            value,
            data,
            v, r, s)

    def recover_sender(self) -> str:
        '''Recover the address corresponding to the key that signed this tx'''
        pubkey = crypto.recover_pubkey(
            (self.v, self.r, self.s),
            self.sighash())
        return crypto.pub_to_addr(pubkey)

    def serialize(self) -> bytes:
        '''Serialize the transaction to raw bytes.'''
        to_serialize: List[bytes] = [
            rlp.i2be_rlp_padded(self.nonce),
            rlp.i2be_rlp_padded(self.gasPrice),
            rlp.i2be_rlp_padded(self.gas),
            bytes.fromhex(self.to[2:]),
            rlp.i2be_rlp_padded(self.value),
            self.data,
            rlp.i2be_rlp_padded(self.v),
            rlp.i2be_rlp_padded(self.r),
            rlp.i2be_rlp_padded(self.s)
        ]
        return rlp.encode(to_serialize)

    def _set_tx_id(self) -> None:
        '''Set the tx_id of the transaction object'''
        self.tx_id = crypto.keccak256(self.serialize())

    def sighash(self) -> bytes:
        '''
        Calculate the signature hash of the transaction. This is the digest
        that is signed by the sender.
        '''
        stripped = self.as_unsigned()
        return stripped.sighash()


class SignedCeloTx(CeloTx, SignedEthTx):
    '''
    A signed Ethereum transaction.

    Args:
        nonce: the tx nonce
        gasPrice: the number of wei to pay per unit of gas
        gas: the number of units of gas
        gasCurrency: the address of the token to be used as gas
        gasFeeRecipient: the address of the recipient of gas fees
        to: the address the tx is address to
        value: the number of wei attached to the tx
        data: bytes to be included in the tx's calldata
        v: EIP-155 signature v value
        r: signature r value
        s: signature s value

    Attributes:
        nonce: the tx nonce
        gasPrice: the number of wei to pay per unit of gas
        gas: the number of units of gas
        gasCurrency: the address of the token to be used as gas
        gasFeeRecipient: the address of the recipient of gas fees
        to: the address the tx is address to
        value: the number of wei attached to the tx
        data: bytes to be included in the tx's calldata
        v: EIP-155 signature v value
        r: signature r value
        s: signature s value
    '''
    def __init__(
            self,
            nonce: int,
            gasPrice: int,
            gas: int,
            gasCurrency: Optional[str],
            gasFeeRecipient: Optional[str],
            to: str,
            value: int,
            data: bytes,
            v: int,
            r: int,
            s: int):
        self.nonce = nonce
        self.gasPrice = gasPrice
        self.gas = gas
        self.gasCurrency = gasCurrency
        self.gasFeeRecipient = gasFeeRecipient
        self.to = to
        self.value = value
        self.data = data
        self.v = v
        self.r = r
        self.s = s
        self._set_tx_id()
        self._make_immutable()

    def as_unsigned(self) -> 'UnsignedCeloTx':
        '''Return an unsigned copy of the transaction'''
        # if r == 0 it's an unsigned tx anyway
        chainId = self.v if self.r == 0 \
            else (self.v - (35 if self.v % 2 else 36)) // 2
        return UnsignedCeloTx(
            nonce=self.nonce,
            gasPrice=self.gasPrice,
            gas=self.gas,
            gasCurrency=self.gasCurrency,
            gasFeeRecipient=self.gasFeeRecipient,
            to=self.to,
            value=self.value,
            data=self.data,
            chainId=chainId)

    @classmethod
    def deserialize(cls, raw: bytes) -> 'SignedCeloTx':
        '''Deserialize a transaction from raw bytes'''
        raws = cast(List[bytes], rlp.decode(raw))
        nonce = rlp.be2i_rlp(raws[0])
        gasPrice = rlp.be2i_rlp(raws[1])
        gas = rlp.be2i_rlp(raws[2])
        gasCurrency = None if raws[3] == b'' else f'0x{raws[3].hex()}'
        gasFeeRecipient = None if raws[4] == b'' else f'0x{raws[4].hex()}'
        to = f'0x{raws[3].hex()}'
        value = rlp.be2i_rlp(raws[4])
        data = raws[5]
        (v, r, s) = [rlp.be2i_rlp(i) for i in raws[6:]]

        return SignedCeloTx(
            nonce,
            gasPrice,
            gas,
            gasCurrency,
            gasFeeRecipient,
            to,
            value,
            data,
            v, r, s)

    def serialize(self) -> bytes:
        '''Serialize the transaction to raw bytes.'''
        gasCurrency = b''
        if self.gasCurrency is not None:
            gasCurrency = bytes.fromhex(self.gasCurrency[2:])

        gasFeeRecipient = b''
        if self.gasFeeRecipient is not None:
            gasFeeRecipient = bytes.fromhex(self.gasFeeRecipient[2:])

        to_serialize: List[bytes] = [
            rlp.i2be_rlp_padded(self.nonce),
            rlp.i2be_rlp_padded(self.gasPrice),
            rlp.i2be_rlp_padded(self.gas),
            gasCurrency,
            gasFeeRecipient,
            bytes.fromhex(self.to[2:]),
            rlp.i2be_rlp_padded(self.value),
            self.data,
            rlp.i2be_rlp_padded(self.v),
            rlp.i2be_rlp_padded(self.r),
            rlp.i2be_rlp_padded(self.s)
        ]
        return rlp.encode(to_serialize)
