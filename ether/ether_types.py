import asyncio

from asyncio import Future
from mypy_extensions import TypedDict
from typing import Any, Dict, List, Optional, Tuple


EthSig = Tuple[int, int, int]

EthABI = List[Dict[str, Any]]


class EthTxDict(TypedDict):
    '''Suitable for jsonrpc'''
    nonce: str
    gasPrice: str
    gas: str
    to: str
    value: str
    data: str


class CeloTxDict(EthTxDict):
    gasCurrency: Optional[str]
    gasFeeRecipient: Optional[str]


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


class RPCRequest(TypedDict):
    method: str
    params: List
    fut: Future


class RPCSubscription(TypedDict):
    method: str
    params: List
    queue: asyncio.Queue
