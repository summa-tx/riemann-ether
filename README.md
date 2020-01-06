### riemann-ether

This is a simple library for building, signing, and reading logs from Ether
transactions quickly. It also includes geth and infura RPC clients.

It is intended for quickly developing MVP applications, and may not be suitable
for production applications or use at scale.

### Development

Clone and then run `pipenv install -d`

#### Basic Usage

```python
from ether import transactions

my_tx = transactions.UnsignedEthTx(
    to='0x' + '20' * 20,
    value=10**18,
    gas=21000,
    gasPrice=15 * 1000000000,  # 15 GWEI
    nonce=0,
    data=b'',
    chainId=1)

signed_tx = transactions.sign_transaction(my_tx, key=b'\x32' * 32)

hex_tx = transactions.serialize(signed_tx)

sender_address = transactions.recover_sender(signed_tx)
```

```python
import json
from ether import calldata

abi = json.loads(f'{SOME_ABI_DATA_HERE}')

tx_data = calldata.call('transfer', ['0x' + '20' * 20, 60000000], abi)
```

```python
import json
from ether import events

event = {'data': '0xdeadbeef'}  # event dict from api or wherever
abi = json.loads('SOME_ABI_DATA_HERE')

decoded_event = events.decode_event(event, abi)
```

```python
from ether import ethrpc

infura_client = ethrpc.get_client('ropsten', infura_key=f'{INFURA_KEY}')
infura_https = ethrpc.get_client(
    'ropsten',
    infura_key=f'{INFURA_KEY}',
    force_https=True)
node_client = ethrpc.get_client('ropsten', uri=f'{URI}:{PORT}')

async def do(client):
  rpc_client =
```
