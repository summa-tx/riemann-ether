import unittest

from ether import rlp

from ether.tests import helpers


def process_input(item) -> bytes:
    if isinstance(item, int):
        return rlp.i2be_rlp_padded(item)
    if isinstance(item, list):
        return [process_input(i) for i in item]
    if isinstance(item, str):
        if len(item) > 0 and item[0] == '#':
            return rlp.i2be_rlp_padded(int(item[1:]))
        return item.encode('utf8')


class TestRLP(unittest.TestCase):

    def prep_json(self, helpers_json):
        vectors = []
        for k, v in helpers_json.items():
            vectors.append(
                (process_input(v['in']),
                 bytes.fromhex(v['out'][2:]),
                 k)
            )
        return vectors

    def setUp(self):
        self.vectors = self.prep_json(helpers.rlp_json)

    def test_encode(self):
        for v in self.vectors:

            (a, b) = (rlp.encode(v[0]), v[1])
            self.assertEqual(a, b)

    def test_decode(self):
        for v in self.vectors:
            print('name', v[2])
            print('input', v[1])

            (a, b) = v[0], rlp.decode(v[1])
            print('theirs', a)
            print('ours', b)
            self.assertEqual(a, b)
            print('')

    def test_roundtrip(self):
        for v in self.vectors:
            decoded = rlp.decode(v[1])
            encoded = rlp.encode(decoded)
            self.assertEqual(encoded, v[1])
