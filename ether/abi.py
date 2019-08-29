from ether import crypto

from typing import Any, Dict, List
from ether.ether_types import EthABI


def make_type_list(f: Dict[str, Any]) -> str:
    '''
    makes a comma-delimted type list
    for use in the signature and encoding
    e.g. '(bytes,bytes,bytes)'
    '''
    inputs: List[Dict[str, Any]] = f['inputs']
    types = ','.join(t['type'] for t in inputs)
    return f'({types})'


def find(name: str, interface: EthABI) -> List[Dict[str, Any]]:
    return [e for e in interface if e['name'] == name]


def make_signature(f: Dict[str, Any]) -> str:
    '''
    Parses a function or event ABI into a signture

    Args:
        f (dict): the function or event ABI
    Returns:
        (str): the signature
    '''
    types = make_type_list(f)
    return f'{f["name"]}{types}'


def make_selector(f: Dict[str, Any]) -> bytes:
    '''
    Parses a function ABI into a function selector
    This is the first 4 bytes of the hash of the signature

    Args:
        f (dict): the function ABI
    Returns:
        (bytes): the function selector
    '''
    return crypto.keccak256(make_signature(f).encode('utf8'))[:4]
