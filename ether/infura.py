import ssl
import json
import asyncio
import websockets

from ether import transactions

from websockets.client import WebSocketClientProtocol
from typing import cast, Dict, List, Optional, Tuple, Union
from ether.ether_types import EthTx, Receipt, SignedEthTx, UnparsedEtherEvent


def _encode_int(number: Union[str, int]) -> str:
    try:
        return hex(cast(int, number))
    except TypeError:
        return cast(str, number)


def _id():
    '''Infinite generator for unique request IDs'''
    index = 0
    while 1:
        yield index
        index += 1


URI = 'wss://{network}.infura.io/ws/v3/{project_id}'
_SOCKETS: Dict[str, WebSocketClientProtocol] = {}  # sockets open
_INFLIGHT: Dict[int, asyncio.Future] = {}  # requests awaiting responses
_SUBSCRIPTIONS: Dict[str, asyncio.Queue] = {}  # subscription queues
_IDS = _id()


async def close_socket(ws: WebSocketClientProtocol) -> None:
    await ws.close()


async def close_sockets() -> None:
    '''close all open connections'''
    global _SOCKETS
    tmp = _SOCKETS
    _SOCKETS = {}
    await asyncio.gather(*[close_socket(tmp[n]) for n in tmp])


async def make_socket(
        network: str,
        project_id: str) -> WebSocketClientProtocol:
    '''Sets up a new socket for the network, and registers ping and handler'''
    global _SOCKETS
    if network in _SOCKETS:
        return _SOCKETS[network]
    else:
        uri = URI.format(network=network, project_id=project_id)
        ws = await websockets.connect(uri, ssl=ssl.SSLContext())
        _SOCKETS[network] = ws
        asyncio.ensure_future(_ping(ws))
        asyncio.ensure_future(_handle_incoming(ws))


async def _get_socket(
        network: str) -> WebSocketClientProtocol:
    '''Gets a socket for the network. Blocks if none has been created'''
    while network not in _SOCKETS is None:
        await asyncio.sleep(5)
    return _SOCKETS[network]


async def _ping(
        ws: WebSocketClientProtocol) -> None:
    '''
    Periodically pings the websocket to keep it alive
    '''
    global _SOCKETS
    while True:
        try:
            await ws.ping()
            await asyncio.sleep(15)
        except websockets.exceptions.ConnectionClosed:
            break


async def _handle_incoming(ws: WebSocketClientProtocol) -> None:
    '''Router for incoming messages. Distributes them to futures/queues'''
    while True:
        try:
            msg = await ws.recv()
            payload = json.loads(msg)
            # if it has a request ID, it's an RPC response
            if 'error' in payload:
                _INFLIGHT[payload['id']].set_exception(
                    RuntimeError(str(payload['error'])))
                continue
            elif 'id' in payload and payload['id'] in _INFLIGHT:
                _INFLIGHT[payload['id']].set_result(payload['result'])
            # otherwise it's a subscript notification
            # add it to the subscription's queue
            elif 'params' in payload and 'subscription' in payload['params']:
                sub_id = payload['params']['subscription']
                q = _SUBSCRIPTIONS[sub_id]
                await q.put(payload['params']['result'])
        except websockets.exceptions.ConnectionClosed:
            break


async def _RPC(method: str, params: List, network: str):
    '''Internal method for handling RPC calls'''
    # get a new ID and the websket
    req_id = next(_IDS)
    ws = await _get_socket(network)

    # Create a new future store it in our pendings and send it
    fut = asyncio.get_event_loop().create_future()
    _INFLIGHT[req_id] = fut

    # send the request
    payload = {
        'jsonrpc': '2.0',
        'id': req_id,
        'method': method,
        'params': params}
    await ws.send(json.dumps(payload))

    # await the result
    res = await fut
    return res


async def _subscribe(
        params: List,
        network: str) -> Tuple[str, asyncio.Queue]:
    '''Internal method for setting up subscriptions'''
    # set up the queue
    q: asyncio.Queue = asyncio.Queue()

    # get the subscription ID and store the q
    sub_id = await _RPC('eth_subscribe', params, network)
    _SUBSCRIPTIONS[sub_id] = q
    return sub_id, q


async def _fake_subscribe(
        method: str,
        params: List,
        poll_time: int = 10,
        network: str = 'mainnet') -> asyncio.Queue:
    '''Turns an RPC call into a subscription by polling regularly'''
    q: asyncio.Queue = asyncio.Queue()
    task = _fake_sub_poller(q, method, params, poll_time, network)
    asyncio.ensure_future(task)
    return q


async def _fake_sub_poller(
        q: asyncio.Queue,
        method: str,
        params: List,
        poll_time: int = 10,
        network: str = 'mainnet') -> None:
    '''poll for results and add them to the queue'''
    while True:
        try:
            await q.put(await _RPC(method, params, network))
            await asyncio.sleep(poll_time)
        except websockets.exceptions.ConnectionClosed:
            break


async def unsubscribe(sub_ids: List[str], network: str = 'mainnet'):
    '''Cancel a list of subscriptions'''
    return await _RPC('eth_unsubscribe', sub_ids, network)


async def subscribe_to_address_events(
        addresses: List[str],
        topics: Optional[List[str]],
        network: str = 'mainnet') -> Tuple[str, asyncio.Queue]:
    '''Subscribes to event logs at specific addresses'''
    param_dict = {'address': addresses}
    if topics:
        param_dict['topics'] = topics

    return await _subscribe(['logs', param_dict], network)


async def subscribe_to_headers(
        network: str = 'mainnet') -> Tuple[str, asyncio.Queue]:
    '''Subscribes to new headers on the network'''
    return await _subscribe(['newHeads'], network)


async def get_balance(
        address: str,
        block: Union[str, int] = 'latest',
        network: str = 'mainnet') -> int:
    '''Gets the number of wei at an address'''
    res = await _RPC(
        'eth_getBalance',
        [address, _encode_int(block)],
        network)
    return int(res, 16)


async def get_logs(
        address: Optional[str] = None,
        from_block: Union[str, int] = 'earliest',
        to_block: Union[str, int] = 'latest',
        topics: Optional[List[Optional[str]]] = None,
        blockhash: Optional[str] = None,
        network: str = 'mainnet') -> List[UnparsedEtherEvent]:
    '''Gets logs'''
    params: Dict[str, Union[str, List[Optional[str]]]] = {}

    if address:
        params['address'] = address
    if topics:
        params['topics'] = topics

    # can't have both a hash and a height range
    if blockhash:
        params['blockhash'] = blockhash
    else:
        params['fromBlock'] = _encode_int(from_block)
        params['toBlock'] = _encode_int(to_block)

    return await _RPC('eth_getLogs', [params], network)


async def get_past_contract_logs(
        address: str,
        topics: Optional[List[Optional[str]]],
        network: str = 'mainnet') -> List[UnparsedEtherEvent]:
    '''Simpler method to get contract logs'''
    return await get_logs(address=address, topics=topics, network=network)


async def broadcast(tx: str, network: str = 'mainnet') -> str:
    '''Broadcast a transaction to the network'''
    if tx[0:2] != '0x':
        tx = f'0x{tx}'
    return await _RPC(
        method='eth_sendRawTransaction',
        params=[tx],
        network=network)


async def get_tx_receipt(
        tx_id: str,
        network: str = 'mainnet') -> Optional[Receipt]:
    '''Get the receipt of a transaction. None if not confirmed'''
    if tx_id[:2] != '0x':
        tx_id = f'0x{tx_id}'

    return await _RPC(
        method='eth_getTransactionReceipt',
        params=[tx_id],
        network=network)


async def get_nonce(account: str, network: str = 'mainnet') -> int:
    res = await _RPC(
        method='eth_getTransactionCount',
        params=[account, 'pending'],
        network=network)
    appropriate_nonce = int(res, 16)
    return appropriate_nonce


async def preflight_tx(
        tx: EthTx,
        sender: Optional[str] = None,
        network: str = 'mainnet'):
    '''Preflight a transaction'''
    if sender is None and 'v' in tx:
        sender = transactions.recover_sender(cast(SignedEthTx, tx))
    else:
        sender = '0x' + '11' * 20

    res = await _RPC(
        method='eth_call',
        params=[
            {
                'from': sender,
                'to': tx['to'],
                'data': f'0x{tx["data"].hex()}'
            },
            'latest'  # block height parameter
        ],
        network=network)
    return res
