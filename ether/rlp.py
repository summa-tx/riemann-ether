from typing import List, Tuple, Union

LIST = False
BYTES = True

# defined by RLP standard
BYTES_OFFSET = 0x80
LONG_BYTES_OFFSET = BYTES_OFFSET + 55  # 0xb7
ARRAY_OFFSET = 0xc0
LONG_ARRAY_OFFSET = ARRAY_OFFSET + 55  # 0xf7


class RLPError(ValueError):
    ...


def i2be_rlp_padded(
        number: int,
        length: int = 0,
        signed: bool = False) -> bytes:
    '''
    Convert int to big endian (b.e.) bytes

    Args:
        number: int value to convert to bytes in BE format
    Returns:
        bytes in BE format
    '''
    if length == 0:
        sign_bit = 1 if signed else 0
        length = (number.bit_length() + 7 + sign_bit) // 8
    if number == 0 and length == 0:
        return b''
    return number.to_bytes(length, 'big', signed=signed)


def be2i_rlp(b: bytes, signed: bool = False) -> int:
    if b == b'':
        return 0
    return int.from_bytes(b, 'big', signed=signed)


def encode(item: Union[List, bytes]) -> bytes:
    if isinstance(item, bytes):
        if len(item) == 1 and item[0] < BYTES_OFFSET:
            return item
        else:
            return _encode_length(len(item), BYTES_OFFSET) + item
    elif isinstance(item, list):
        output = b''.join(encode(i) for i in item)
        return _encode_length(len(output), ARRAY_OFFSET) + output


def _encode_length(length: int, offset: int) -> bytes:
    '''Encode a length '''
    if length <= 55:
        return bytes([offset + length])

    if length >= 256 ** 8:
        raise RLPError('Bytestring is too long to encode')

    enc_len = i2be_rlp_padded(number=length)
    tag = bytes([offset + 55 + len(enc_len)])
    return b''.join([tag, enc_len])


def decode_list(raw: bytes) -> List:
    output = []
    remaining = raw[:]
    while len(remaining) > 0:
        (offset, data_len, type) = _decode_length(remaining)
        try:
            next_item = remaining[:offset + data_len]
            output.append(decode(next_item))
        except IndexError as e:
            raise RLPError('Malformatted bytestring. Overran input.') from e
        remaining = remaining[offset + data_len:]
    return output


def decode(raw: bytes) -> Union[List, bytes]:
    if len(raw) == 0:
        return b''

    (offset, data_len, type) = _decode_length(raw)

    try:
        next_item = raw[offset: offset + data_len]
    except IndexError as e:
        raise RLPError('Malformatted bytestring. Overran input') from e

    if type == BYTES:
        return next_item

    return decode_list(next_item)


def _decode_length(raw: bytes) -> Tuple[int, int, bool]:
    try:
        tag = raw[0]
    except IndexError as e:
        raise RLPError('Malformatted bytestring. Null.') from e

    # single byte
    if tag < BYTES_OFFSET:
        return (0, 1, BYTES)

    # short bytestring
    if tag <= LONG_BYTES_OFFSET:
        bytes_len = tag - BYTES_OFFSET
        return (1, bytes_len, BYTES)

    # long bytestring
    if tag <= LONG_BYTES_OFFSET + 7:
        enc_len_bytes = tag - LONG_BYTES_OFFSET
        enc_len = raw[1: 1 + enc_len_bytes]
        bytes_len = int.from_bytes(enc_len, 'big')
        return (1 + enc_len_bytes, bytes_len, BYTES)

    # short list
    if tag <= LONG_ARRAY_OFFSET:
        list_len = tag - ARRAY_OFFSET
        return (1, list_len, LIST)

    # long list
    enc_len_bytes = tag - LONG_ARRAY_OFFSET
    enc_len = raw[1: 1 + enc_len_bytes]
    list_len = int.from_bytes(enc_len, 'big')
    return (1 + enc_len_bytes, list_len, LIST)
