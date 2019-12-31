from ether import abi, crypto

from typing import Any, cast, Dict, List
from ether.ether_types import EthABI, ParsedEtherEvent, UnparsedEtherEvent


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


def decode_event(
        encoded_event: UnparsedEtherEvent,
        contract_abi: EthABI) -> Dict[str, Any]:
    '''
    Decodes an event using the provided abi
    Args:
        encoded_event (dict): the etherscan/full node event Dict
        abi           (dict): the abi as a dict (use json.loads)
    Returns:
        (dict): the decoded dict
    '''
    ret = {}

    events = [entry for entry in contract_abi if entry['type'] == 'event']

    # find the appropriate event interface
    event_abi = _match_topic0_to_event(encoded_event['topics'][0], events)

    # get the indexed args
    indexed = _find_indexed(event_abi)
    for signature, blob in zip(indexed, encoded_event['topics'][1:]):
        val = abi.decode(signature['type'], bytes.fromhex(blob[2:]))
        ret[signature['name']] = val

    unindexed = _find_unindexed(event_abi)
    unindexed_values = abi.decode_many(
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
