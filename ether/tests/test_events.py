import unittest

from ether import events

from ether.tests import helpers


class TestABI(unittest.TestCase):

    def test_decode_event(self):
        for i in range(len(helpers.weth_transfers)):
            decoded = events.decode_event(
                helpers.weth_transfers[i],
                helpers.weth_json)
            self.assertEqual(decoded, helpers.weth_parsed[i])

    def test_match_topic0_to_event(self):
        with self.assertRaises(ValueError) as context:
            events._match_topic0_to_event(
                'nope',
                [e for e in helpers.weth_json if e['type'] == 'event'])
        self.assertIn('Topic not found', str(context.exception))
