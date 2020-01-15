import unittest

from ether import abi, transactions

from ether.tests import helpers


class TestTxns(unittest.TestCase):

    @staticmethod
    def prep_json(j):
        vector = {}
        vector['comment'] = j['comment']
        vector['raw'] = j['raw']
        vector['tx_obj'] = transactions.SignedEthTx(
            nonce=j['tx']['nonce'],
            gasPrice=j['tx']['gasPrice'],
            gas=j['tx']['gas'],
            to=j['tx']['to'],
            value=j['tx']['value'],
            data=bytes.fromhex(j['tx']['data'][2:]),
            v=j['tx']['v'],
            r=int(j['tx']['r'], 16),
            s=int(j['tx']['s'], 16)
        )
        # vector['call']['args'] = [bytes.fromhex(i[2:]) for i in j['call']['args']]
        # vector['call']['args'] = [
        #     abi.decode_many(v['call']['type_list'],
        #                     b''.join(v['call']['args']))
        #     ]
        return vector

    @classmethod
    def setUpClass(cls):
        cls.vectors = [TestTxns.prep_json(t) for t in helpers.txn_json['txns']]

    def test_deser(self):
        for v in self.vectors:
            print(
                transactions.SignedEthTx.deserialize_hex(v['raw']),
                v['tx_obj']
            )
            self.assertEqual(
                transactions.SignedEthTx.deserialize_hex(v['raw']),
                v['tx_obj']
            )

    def test_ser(self):
        for v in self.vectors:
            self.assertEqual(
                v['tx_obj'].serialize_hex(),
                v['raw']
            )
