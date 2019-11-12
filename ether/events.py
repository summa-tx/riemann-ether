import eth_abi

from ether import abi, crypto

from typing import Any, cast, Dict, List, Union
from ether.ether_types import EthABI, ParsedEtherEvent, UnparsedEtherEvent


def _zero_pad_address(addr: str) -> str:
    '''Pads an address with 0s for event topics'''
    return '0x' + '00' * 12 + addr[2:]


def _make_topic0(event: Dict[str, Any]) -> str:
    '''
    Calculates the event topic hash frrom the event ABI
    Args:
        event (dict): the event ABI
    Returns:
        (str): the event topic as 0x prepended hex
    '''
    signature = abi.make_signature(event).encode('utf8')
    topic_hex = crypto.keccak256(signature).hex()
    return '0x{}'.format(topic_hex)


def _match_topic0_to_event(
        event_topic: str,
        events: List[Dict[str, Any]]) -> Dict[str, Any]:
    '''
    Finds the corresponding event from a topic string
    Args:
        event_topic (str): the event's 0x prepended hex topic
    Returns:
        (dict): the event ABI
    '''
    for event in events:
        if _make_topic0(event) == event_topic:
            return event
    raise ValueError('Topic not found')


def _find_indexed(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    '''
    Finds indexed arguments
    Args:
        event_topic (str): the event's 0x prepended hex topic
    Returns:
        (list): the indexed arguments
    '''
    return [t for t in event['inputs'] if t['indexed']]


def _find_unindexed(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    '''
    Finds indexed arguments
    Args:
        event_topic (str): the event's 0x prepended hex topic
    Returns:
        (list): the unindexed arguments
    '''
    return [t for t in event['inputs'] if not t['indexed']]


def _process_value(t: str, v: str) -> Union[str, int, bytes, bool]:
    '''
    Args:
        t (str): the type annotation
        v (str): the value string
    Returns:
        (t): the parsed value
    '''
    # strip prefix if necessary
    if '0x' in v:
        v = v[2:]
    if t == 'address':
        # last 20 bytes of value
        return '0x{}'.format(v[-40:])
    if 'bytes' in t:
        return bytes.fromhex(v)
    if 'uint' in t:
        return int.from_bytes(bytes.fromhex(v), 'big', signed=False)
    elif 'int' in t:
        return int.from_bytes(bytes.fromhex(v), 'big', signed=True)
    elif t == 'bool':
        return t[-1] == '1'
    raise ValueError(f'Could not deserialize type {t} with value {v}')


def decode_event(
        encoded_event: UnparsedEtherEvent,
        abi: EthABI) -> Dict[str, Any]:
    '''
    Decodes an event using the provide abi
    Args:
        encoded_event (dict): the etherscan/full node event Dict
        abi           (dict): the abi as a dict (use json.loads)
    Returns:
        (dict): the decoded dict
    '''
    ret = {}

    events = [entry for entry in abi if entry['type'] == 'event']

    # find the abi
    event_abi = _match_topic0_to_event(encoded_event['topics'][0], events)

    # get the indexed args
    indexed = _find_indexed(event_abi)
    for i in range(len(indexed)):
        signature = indexed[i]
        val = _process_value(signature['type'], encoded_event['topics'][i + 1])
        ret[signature['name']] = val

    unindexed = _find_unindexed(event_abi)
    unindexed_values = eth_abi.decode_abi(
        [t['type'] for t in unindexed],
        bytes.fromhex(encoded_event['data'][2:]))

    for k, v in zip([t['name'] for t in unindexed], unindexed_values):
        ret[k] = v

    ret['event_name'] = event_abi['name']

    return ret


def parse_event_data(
        encoded_event: UnparsedEtherEvent,
        contract_abi: EthABI) -> ParsedEtherEvent:
    '''Parses an event given a contract ABI'''
    tmp = cast(ParsedEtherEvent, encoded_event.copy())
    tmp['data'] = decode_event(encoded_event, contract_abi)
    return tmp
