from typing import Any, Dict, List, Tuple
from mypy_extensions import TypedDict

EthSig = Tuple[int, int, int]

EthABI = List[Dict[str, Any]]


class SignedEthTx(TypedDict):
    to: str
    value: int
    gas: int
    gasPrice: int
    nonce: int
    data: bytes
    v: int
    s: int
    r: int


class UnsignedEthTx(TypedDict):
    to: str
    value: int
    gas: int
    gasPrice: int
    nonce: int
    data: bytes
    chainId: int


class EtherEvent(TypedDict):
    address: str
    blockHash: str
    blockNumber: str
    logIndex: str
    removed: bool
    topics: List[str]
    transactionHash: str
    transactionIndex: str


class UnparsedEtherEvent(EtherEvent):
    data: str


class ParsedEtherEvent(EtherEvent):
    data: Dict[str, Any]
