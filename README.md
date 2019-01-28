### riemann-ether

This is a simple library for building, signing, and reading logs from Ether transactions quickly

It is in early stages of development

### Development

Clone and then run `pipenv install`

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

abi = json.loads('SOME_ABI_DATA_HERE')

tx_data = calldata.call('transfer', ['0x' + '20' * 20, 60000000], abi)
```

```python
import json
from ether import events

event = {'data': '0xdeadbeef'}  # event dict from api or wherever
abi = json.loads('SOME_ABI_DATA_HERE')

decoded_event = events.decode_event(event, abi)
```
