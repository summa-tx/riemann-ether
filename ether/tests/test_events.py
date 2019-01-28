import unittest

from ether import events

from ether.tests import helpers


class TestABI(unittest.TestCase):

    def test_decode_event(self):
        for i in range(len(helpers.weth_transfers)):
            decoded = events.decode_event(
                helpers.weth_transfers[i],
                helpers.weth_json)
            # print(decoded)
            self.assertEqual(decoded, helpers.weth_parsed[i])

    def test_match_topic0_to_event(self):
        with self.assertRaises(ValueError) as context:
            events.match_topic0_to_event(
                'nope',
                [e for e in helpers.weth_json if e['type'] == 'event'])
        self.assertIn('Topic not found', str(context.exception))

    def test_process_value(self):
        test_vectors = (
            (('address', '0x' + '20' * 32), '0x' + '20' * 20),
            (('bytes', '00' * 32), b'\x00' * 32),
            (('uint', '80' + '00' * 31), 2 ** 255),  # test the sign bit
            (('int', '80' + '00' * 31), -1 * 2 ** 255),  # test the sign bit
            (('bool', '00' * 32), False))
        for v in test_vectors:
            self.assertEqual(
                events.process_value(*v[0]),
                v[1])
