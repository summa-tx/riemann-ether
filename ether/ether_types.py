from typing import Any, Dict, List, Tuple
from mypy_extensions import TypedDict

SignedEthTx = TypedDict(
    'SignedEthTx',
    {
        'to': str,
        'value': int,
        'gas': int,
        'gasPrice': int,
        'nonce': int,
        'data': bytes,
        'v': int,
        's': int,
        'r': int
    }
)

UnsignedEthTx = TypedDict(
    'UnsignedEthTx',
    {
        'to': str,
        'value': int,
        'gas': int,
        'gasPrice': int,
        'nonce': int,
        'data': bytes,
        'chainId': int
    }
)


EthSig = Tuple[int, int, int]

EthABI = List[Dict[str, Any]]
