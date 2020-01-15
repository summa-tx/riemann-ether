import abc
import ssl
import json
import aiohttp
import asyncio
import websockets

from ether.transactions import EthTx, SignedEthTx

from logging import Logger
from asyncio import Future
from websockets.client import WebSocketClientProtocol
from ether.ether_types import Receipt, RPCRequest
from ether.ether_types import RPCSubscription, UnparsedEtherEvent
from typing import Any, cast, Dict, Generator, List, Optional, Tuple, Union


def _id(start: int) -> Generator[int, None, None]:
    '''Infinite generator for unique request IDs'''
    index = start
    while True:
        yield index
        index += 1


def get_client(
        network: str,
        **kwargs: Any) -> 'BaseRPC':
    '''
    Convenience method for getting a client.
    Prefer instantiating directly

    Args:
        network (str): mainnet, ropsten, rinkeby, etc.
        force_https (bool): set true to disable websockets
    '''
    use_infura = 'infura_key' in kwargs \
                 and kwargs['infura_key'] is not None \
                 and len(kwargs['infura_key']) > 0
    force_https = 'force_https' in kwargs and kwargs['force_https']
    if use_infura:
        return InfuraWSRPC(network=network, **kwargs)
    if use_infura and force_https:
        return InfuraHTTPRPC(network=network, **kwargs)

    uri = ''
    if 'uri' in kwargs:
        uri = kwargs.pop('uri')
    else:
        raise ValueError('Must specify URI or infura key')
    if uri[0:3] == 'wss' and force_https:
        return WSRPC(uri, network, **kwargs)
    return HTTPRPC(uri, network, **kwargs)


class BaseRPC(metaclass=abc.ABCMeta):

    _ids: Generator[int, None, None]
    uri: str
    network: str
    connected: bool

    params: Dict[str, Any]

    def __repr__(self) -> str:
        return f'Eth RPC {self.mode} client: {self.network} via {self.uri}'

    def __init__(
            self,
            uri: str,
            network: str,
            logger: Optional[Logger] = None,
            **kwargs: Any) -> None:

        self._ids = _id(kwargs['_id'] if '_id' in kwargs else 0)
        self.connected = False

        self.uri = uri
        self.network = network
        self.mode = uri[0:3]
        self.params = kwargs

        self._logger = logger

    def info(self, *args: Any, **kwargs: Any) -> None:
        if self._logger is not None:
            self._logger.info(*args, **kwargs)

    def debug(self, *args: Any, **kwargs: Any) -> None:
        if self._logger is not None:
            self._logger.debug(*args, **kwargs)

    def warn(self, *args: Any, **kwargs: Any) -> None:
        if self._logger is not None:
            self._logger.warn(*args, **kwargs)

    def error(self, *args: Any, **kwargs: Any) -> None:
        if self._logger is not None:
            self._logger.error(*args, **kwargs)

    @abc.abstractmethod
    async def open(self) -> None:
        ...

    @abc.abstractmethod
    async def close(self) -> None:
        ...

    @abc.abstractmethod
    async def _RPC(self, method: str, params: List) -> Any:
        ...

    @staticmethod
    def _encode_if_int(v: Any) -> Any:
        if isinstance(v, int):
            return hex(cast(int, v))
        return v

    @staticmethod
    def _shallow_prep_params(params: List[Any]) -> List[Any]:
        return list(map(BaseRPC._encode_if_int, params))

    async def send_transaction(
            self,
            from_addr: str,
            tx: EthTx) -> str:
        '''Send a transaction, let the node sign it if it wants'''
        if hasattr(self, 'infura_key'):
            raise RuntimeError('Tried to sign tx with infura connection')

        param = cast(dict, tx.to_json_dict())
        param['from'] = from_addr
        param['data'] = f'0x{param["data"].hex()}'

        for key, value in param.items():
            param[key] = BaseRPC._encode_if_int(value)

        res = await self._RPC(
            method='eth_sendTransaction',
            params=[param]
        )

        return cast(str, res)

    async def get_balance(
            self,
            address: str,
            block: Union[str, int] = 'latest') -> int:
        '''Gets the number of wei at an address'''
        res = await self._RPC(
            'eth_getBalance',
            [address, BaseRPC._encode_if_int(block)])
        return int(res, 16)

    async def get_logs(
            self,
            address: Optional[str] = None,
            from_block: Union[str, int] = 'earliest',
            to_block: Union[str, int] = 'latest',
            topics: Optional[List[Optional[str]]] = None,
            blockhash: Optional[str] = None) -> List[UnparsedEtherEvent]:
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
            params['fromBlock'] = BaseRPC._encode_if_int(from_block)
            params['toBlock'] = BaseRPC._encode_if_int(to_block)

        events = await self._RPC(method='eth_getLogs', params=[params])

        return cast(List[UnparsedEtherEvent], events)

    async def get_past_contract_logs(
            self,
            address: str,
            topics: Optional[List[Optional[str]]]) -> List[UnparsedEtherEvent]:
        '''Simpler method to get contract logs'''
        return await self.get_logs(address=address, topics=topics)

    async def broadcast(self, tx: str) -> str:
        '''Broadcast a transaction to the network'''
        if tx[0:2] != '0x':
            tx = f'0x{tx}'
        result = await self._RPC(
            method='eth_sendRawTransaction',
            params=[tx])
        return cast(str, result)

    async def get_tx_receipt(
            self,
            tx_id: str) -> Optional[Receipt]:
        '''Get the receipt of a transaction. None if not confirmed'''
        if tx_id[:2] != '0x':
            tx_id = f'0x{tx_id}'

        result = await self._RPC(
            method='eth_getTransactionReceipt',
            params=[tx_id])

        return cast(Optional[Receipt], result)

    async def get_nonce(self, account: str) -> int:
        res = await self._RPC(
            method='eth_getTransactionCount',
            params=[account, 'pending'])
        appropriate_nonce = int(res, 16)
        return appropriate_nonce

    async def preflight_tx(
            self,
            tx: EthTx,
            sender: Optional[str] = None) -> str:
        '''Preflight a transaction'''
        try:
            # if it doesn't have that name
            sender = cast(SignedEthTx, tx).recover_sender()
        except AttributeError:
            sender = '0x' + '11' * 20

        res = await self._RPC(
            method='eth_call',
            params=[
                {
                    'from': sender,
                    'to': tx.to,
                    'data': f'0x{tx.data.hex()}'
                },
                'latest'  # block height parameter
            ])
        return cast(str, res)


class WSRPC(BaseRPC):

    _ws: WebSocketClientProtocol

    _inflight: Dict[int, RPCRequest] = {}  # requests awaiting responses
    _subscriptions: Dict[str, RPCSubscription] = {}  # subscription queues

    _ping_task: Future
    _handle_task: Future

    def __init__(
            self,
            uri: str,
            network: str,
            **kwargs: Any) -> None:
        super().__init__(uri, network, **kwargs)

    def __repr__(self) -> str:
        '''Override repr to add connection status'''
        return f'{super().__repr__()}\tConnected: {self.connected}'

    async def open(self) -> None:
        self._ws = await websockets.connect(self.uri, ssl=ssl.SSLContext())
        self.connected = True
        self._ping_task = asyncio.ensure_future(self._ping())
        self._handle_task = asyncio.ensure_future(self._handle_incoming())

    async def _handle_incoming(self) -> None:
        '''Router for incoming messages. Distributes them to futures/queues'''
        try:
            while True:
                msg = await self._ws.recv()
                payload = json.loads(msg)
                # if it has a request ID, it's an RPC response
                if 'error' in payload:
                    self._inflight[payload['id']]['fut'].set_exception(
                        RuntimeError(str(payload['error'])))
                    continue
                elif 'id' in payload and payload['id'] in self._inflight:
                    future = self._inflight[payload['id']]['fut']
                    future.set_result(payload['result'])
                # otherwise it's a subscript notification
                # add it to the subscription's queue
                elif ('params' in payload
                      and 'subscription' in payload['params']):
                    sub_id = payload['params']['subscription']
                    q = self._subscriptions[sub_id]['queue']
                    await q.put(payload['params']['result'])
        except websockets.exceptions.ConnectionClosed:
            if self.connected:
                # if the forloop breaks due to a connection closed error
                await self.close()

        except asyncio.CancelledError:
            pass

    async def close(self) -> None:
        '''Close the socket and cancel associated tasks'''
        if not hasattr(self, '_ws'):
            return

        if not self.connected:
            return

        await self._ws.close()
        self.connected = False

        # prevent error loops
        if not self._ping_task.cancelled():
            self._ping_task.cancel()
            await self._ping_task

        # prevent error loops
        if not self._handle_task.cancel():
            self._handle_task.cancel()
            await self._handle_task

    def get_pending(
            self) -> Tuple[int, List[RPCRequest], List[RPCSubscription]]:
        if self.connected:
            raise RuntimeError(
                'Tried to retrive pending requests from active socket')

        pending: List[RPCRequest] = []
        subs: List[RPCSubscription] = []

        for _, r in self._inflight.items():
            if not r['fut'].done():
                pending.append(r)
        for _, s in self._subscriptions.items():
            subs.append(s)

        # what's a safe ID to resume from to prevent collisions
        next_id = max(self._inflight.keys()) + 1

        return next_id, pending, subs

    @classmethod
    async def from_pending(
            C,
            uri: str,
            network: str,
            start_id: int,
            pending: List[RPCRequest] = [],
            subs: List[RPCSubscription] = [],
            **kwargs: Any) -> 'WSRPC':
        '''
        Returns an open connection, using requests and subscriptions from
        another WSRPC instance. Subscriptions are restarted, and inflight reqs
        are remade. If you pass a pending request from another closed socket,
        the new socket will handle resolving the associated futures.

        Useful for seamlessly(ish) resuming a faulted session
        '''
        _id = start_id
        new = C(uri=uri, network=network, _id=_id, **kwargs)

        await new.open()

        reqs = [new._RPC(r['method'], r['params'], r['fut']) for r in pending]
        asyncio.ensure_future(asyncio.gather(*reqs))

        new_subs = [new._subscribe(s['params'], s['queue']) for s in subs]
        asyncio.ensure_future(asyncio.gather(*new_subs))
        return new

    async def _ping(self) -> None:
        try:
            while True:
                await self._ws.ping()
                await asyncio.sleep(15)
        except websockets.exceptions.ConnectionClosed:
            if self.connected:
                self.close()

    async def _RPC(
            self,
            method: str,
            params: List,
            fut: Optional[Future] = None) -> Any:
        '''Internal method for handling RPC calls'''
        # get a new ID and the websket
        req_id = next(self._ids)

        # Create a new future store it in our pendings and send it
        if fut is None:
            future = asyncio.get_event_loop().create_future()
        else:
            future = cast(Future, fut)
        self._inflight[req_id] = RPCRequest(
            method=method,
            params=params,
            fut=future)

        # send the request
        payload = {
            'jsonrpc': '2.0',
            'id': req_id,
            'method': method,
            'params': params
        }

        self.debug(f'dispatching ws payload {payload}')
        try:
            await self._ws.send(json.dumps(payload))
        except websockets.exceptions.ConnectionClosed:
            if self.connected:
                await self.close()
            raise RuntimeError('Websocket connection closed unexpectedly')

        # await the result
        res = await future
        return res

    async def _subscribe(
            self,
            params: List,
            queue: Optional[asyncio.Queue] = None) \
            -> Tuple[str, asyncio.Queue]:
        '''Internal method for setting up subscriptions'''
        method = 'eth_subscribe'

        # set up the queue
        q: asyncio.Queue
        if queue is None:
            q = asyncio.Queue()
        else:
            q = cast(asyncio.Queue, queue)

        # get the subscription ID and store the q
        sub_id = await self._RPC(method, params)
        self._subscriptions[sub_id] = RPCSubscription(
            method=method,
            params=params,
            queue=q)
        return sub_id, q

    async def unsubscribe(self, sub_ids: List[str]) -> bool:
        '''Cancel a list of subscriptions'''

        res = await self._RPC('eth_unsubscribe', sub_ids)
        for sub in sub_ids:
            self._subscriptions.pop(sub)
        return cast(bool, res)

    async def subscribe_to_address_events(
            self,
            addresses: List[str],
            topics: Optional[List[str]]) -> Tuple[str, asyncio.Queue]:
        '''Subscribes to event logs at specific addresses'''
        param_dict = {'address': addresses}
        if topics:
            param_dict['topics'] = topics

        return await self._subscribe(['logs', param_dict])

    async def subscribe_to_headers(self) -> Tuple[str, asyncio.Queue]:
        '''Subscribes to new headers on the network'''
        return await self._subscribe(['newHeads'])


class HTTPRPC(BaseRPC):

    _session: aiohttp.ClientSession

    def __init__(
            self,
            uri: str,
            network: str,
            **kwargs: Any) -> None:
        super().__init__(uri, network, **kwargs)

    async def open(self) -> None:
        if self.connected:
            return
        # close the connection after each request
        # some overhead, but less likely to get server-side disconnects
        self._session = aiohttp.ClientSession(
            headers={"Connection": "close"}
        )
        self.connected = True

    async def close(self) -> None:
        await self._session.close()
        self.connected = False

    async def _RPC(self, method: str, params: List[Any]) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": next(self._ids),
            "method": method,
            "params": BaseRPC._shallow_prep_params(params)}
        self.debug(f'dispatching post request {payload}')
        resp = await self._session.post(self.uri, json=payload)
        if resp.status != 200:
            raise RuntimeError(f'Bad status during RPC request: {resp.status}')
        resp_json = await resp.json()
        result = resp_json['result'] if 'result' in resp_json else resp_json
        return result


class InfuraHTTPRPC(HTTPRPC):

    def __init__(self, network: str, infura_key: str, **kwargs: Any) -> None:
        uri = f'https://{network}.infura.io/v3/{infura_key}'
        kwargs['uri'] = uri
        self.infura_key = infura_key
        super().__init__(network=network, infura_key=infura_key, **kwargs)


class InfuraWSRPC(WSRPC):
    def __init__(self, network: str, infura_key: str, **kwargs: Any) -> None:
        uri = f'wss://{network}.infura.io/ws/v3/{infura_key}'
        kwargs['uri'] = uri
        self.infura_key = infura_key
        super().__init__(network=network, infura_key=infura_key, **kwargs)
