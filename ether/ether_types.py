from typing import Any, Dict, List, Optional, Tuple
from mypy_extensions import TypedDict

EthSig = Tuple[int, int, int]

EthABI = List[Dict[str, Any]]


class EthTx(TypedDict):
    to: str
    value: int
    gas: int
    gasPrice: int
    nonce: int
    data: bytes


class SignedEthTx(EthTx):
    v: int
    s: int
    r: int


class UnsignedEthTx(EthTx):
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


# we declare it in this style because "from" is a keyword
Receipt = TypedDict(
    'Receipt',
    {
        'blockHash': str,
        'blockNumber': str,
        'contractAddress': Optional[str],
        'cumulativeGasUsed': str,
        'from': str,
        'gasUsed': str,
        'logs': List[EtherEvent],
        'logsBloom': str,
        'status': str,
        'to': str,
        'transactionHash': str,
        'transactionIndex': str

    }
)
