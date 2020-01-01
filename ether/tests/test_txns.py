import unittest

from ether import abi, transactions

from ether.tests import helpers


class TestTxns(unittest.TestCase):

    @staticmethod
    def prep_json(j):
        v = j.copy()
        v['tx']['data'] = bytes.fromhex(j['tx']['data'][2:])
        v['tx']['r'] = int(j['tx']['r'], 16)
        v['tx']['s'] = int(j['tx']['s'], 16)
        v['call']['args'] = [bytes.fromhex(i[2:]) for i in j['call']['args']]
        v['call']['args'] = [
            abi.decode_many(v['call']['type_list'],
                            b''.join(v['call']['args']))
            ]
        return v

    @classmethod
    def setUpClass(cls):
        cls.vectors = [TestTxns.prep_json(t) for t in helpers.txn_json['txns']]

    def test_deser(self):
        for v in self.vectors:
            print(
                transactions.deserialize_hex(v['raw']),
                v['tx']
            )
            self.assertEqual(
                transactions.deserialize_hex(v['raw']),
                v['tx']
            )

    def test_ser(self):
        for v in self.vectors:
            self.assertEqual(
                transactions.serialize_hex(v['tx']),
                v['raw']
            )
