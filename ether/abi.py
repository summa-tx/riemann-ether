from functools import wraps
from itertools import starmap, zip_longest

from ether.ether_types import EthABI
from typing import Any, cast, Callable, Dict, Iterable, List, Tuple, Union


class ABIEncodingError(ValueError):
    ...


def single_item_decoder(
        f: Callable[..., Any]) -> Callable[..., Any]:
    '''Decorator for decoders that use a single item.'''
    @wraps(f)
    def wrapper(b: bytes, *args: int) -> Any:
        if len(b) != 32:
            raise ABIEncodingError(
                f'Expected 32 byte input to decoder {f.__name__}.'
                f'Got {len(b)} bytes')
        return f(b, *args)
    return wrapper


def _inner_type(type_str: str) -> str:
    '''Throws if not an array type'''
    return type_str[:type_str.rindex('[')]


def _array_length(type_str: str) -> int:
    '''Returns the length of a fixed array, or 0'''
    if '[' not in type_str:
        return 0

    num = type_str[type_str.rindex('[') + 1: type_str.rindex(']')]
    if num == '':
        return 0
    length = int(num)
    if length == 1:
        raise NotImplementedError('1-length arrays? Really?')
    return length


def _join_lists(*a: Iterable[int]) -> Iterable[int]:
    '''column addition without carry for lists of integers'''
    return map(sum, zip_longest(*a, fillvalue=0))


def _slots_to_encode(type_str: str, arg: Any) -> Tuple[int, int]:
    '''
    Output represents slots used at each nested headtail layer
    e.g. (3 slots in the head, 15 in the tail)
    '''
    t = type_str

    if type_str == 'string':
        # 1 for the pointer to the body,
        return (1, len(_encode_str(arg)) // 32)

    if type_str == 'bytes':
        # 1 for the pointer to the body,
        return (1, len(_encode_dynamic_bytes(arg)) // 32)

    # dynamic array
    if t[-2:] == '[]':
        inner = _inner_type(type_str)
        tail = _join_lists(*[_slots_to_encode(inner, a) for a in arg])
        return (1, sum(tail) + 1)  # 1 in head, 1 for length in tail

    # fixed array
    if t[-1] == ']':
        inner = _inner_type(type_str)
        arr_len = _array_length(type_str)
        if len(arg) != arr_len:
            raise ABIEncodingError(
                'Declared fixed arr length does not match type. '
                f'Expected {arr_len}, got {len(arg)}')
        usage = list(_join_lists(*[_slots_to_encode(inner, a) for a in arg]))
        return (usage[0], sum(usage[1:]))

    return (1, 0)


def _encode_uint(number: int) -> bytes:
    '''Encode any unsigned integer, throws if >32 bytes'''
    if not isinstance(number, int) or number < 0:
        raise ABIEncodingError(f'Expected uint. Got {type(number)}')
    return number.to_bytes(32, 'big', signed=False)


@single_item_decoder
def _decode_uint(b: bytes) -> int:
    '''Decode an unsigned integer'''
    return int.from_bytes(b, 'big', signed=False)


def _encode_int(number: int) -> bytes:
    '''Encode any signed integer. Throws if 2s complement is >32 bytes'''
    if not isinstance(number, int):
        raise ABIEncodingError(f'Expected int. Got {type(number)}')
    return number.to_bytes(32, 'big', signed=True)


@single_item_decoder
def _decode_int(b: bytes) -> int:
    '''Decode a signed integer'''
    return int.from_bytes(b, 'big', signed=True)


def _encode_fixed_bytes(b: bytes) -> bytes:
    if not isinstance(b, bytes):
        raise ABIEncodingError(f'Expected bytes. Got {type(b)}')
    padding = bytes(32 - (len(b) % 32))
    return b''.join([b, padding])


@single_item_decoder
def _decode_fixed_bytes(b: bytes, type_str: str) -> bytes:
    length = int(type_str[5:])
    return b[:length]


def _encode_dynamic_bytes(b: bytes) -> bytes:
    '''Returns JUST the tail portion'''
    payload = _encode_fixed_bytes(b)
    return b''.join([_encode_uint(len(b)), payload])


def _decode_dynamic_bytes(b: bytes) -> bytes:
    # first 32 bytes are the length of the string
    length = _decode_uint(b[:32])
    return b[32: 32 + length]


def _encode_str(arg: str) -> bytes:
    if not isinstance(arg, str):
        raise ABIEncodingError(f'Expected str. Got {type(arg)}')
    payload = arg.encode('utf8')
    return _encode_dynamic_bytes(payload)


def _decode_str(b: bytes) -> str:
    return _decode_dynamic_bytes(b).decode('utf8')


def _encode_address(arg: str) -> bytes:
    # addresses are encoded as uint160s, not bytes20s
    return _encode_uint(int(arg, 16))


@single_item_decoder
def _decode_address(b: bytes) -> str:
    return f'0x{b[-20:].hex()}'


def _encode_dynamic_array(type_str: str, arg: List) -> bytes:
    inner = _inner_type(type_str)
    type_list = [inner for _ in arg]
    return _encode_uint(len(arg)) + encode_many(type_list, arg)


def _decode_dynamic_array(type_str: str, b: bytes) -> List:
    '''Decodes the body (tail portion) of a complex type'''
    inner = _inner_type(type_str)
    length = _decode_uint(b[:32])
    type_list = [inner] * length
    return decode_many(type_list, b[32:])


def _is_dynamic(type_str: str) -> bool:
    return ('[]' in type_str         # dynamic array
            or 'string' in type_str  # strings
            or 'bytes[' in type_str  # bytes
            or type_str == 'bytes')  # bytes


def _is_complex(type_str: str) -> bool:
    if '[][]' in type_str:
        return True  # dynamic array
    # static array of dyanmic types
    return 'string[]' in type_str or 'bytes[]' in type_str


def _encode_fixed_array(type_str: str, arg: List) -> bytes:
    '''Head-only lists, no strings, or dynamic entries'''

    return b''.join([encode(_inner_type(type_str), a)[0] for a in arg])


def _decode_fixed_array(type_str: str, b: bytes) -> List:
    '''Head-only lists, no strings, or dynamic entries'''
    if _is_complex(type_str):
        raise ABIEncodingError('Complex type in fixed array decoder')
    length = _array_length(type_str)
    inner = _inner_type(type_str)
    item_len = 32 * _slots_to_encode(inner, range(length))[0]

    items = [b[i:i + item_len] for i in range(0, len(b), item_len)]

    decoded = [decode(inner, item) for item in items]

    return decoded


def encode(
        type_str: str,
        arg: Union[int, bool, str, bytes, List]) -> Tuple[bytes, bytes]:
    '''
    Encode a single item as a bytestring
    Raises an ABIEncodingError if the type does not match the argument
    If the type is dynamic, returns just the tail portion.
    '''
    if type_str == 'address':
        return _encode_address(cast(str, arg)), b''

    elif type_str == 'string':
        return b'', _encode_str(cast(str, arg))

    elif type_str == 'bytes':
        return b'', _encode_dynamic_bytes(cast(bytes, arg))

    elif type_str[-2:] == '[]':
        return b'', _encode_dynamic_array(type_str, cast(List, arg))

    elif '[' in type_str:
        return _encode_fixed_array(type_str, cast(list, arg)), b''

    elif 'bytes' in type_str and int(type_str[5:]) < 32:
        a = cast(bytes, arg)
        if len(a) > 32:
            raise ABIEncodingError(f'Too long for fixed encoding: {len(a)}B')
        return _encode_fixed_bytes(a), b''

    elif type_str[:4] == 'uint':
        return _encode_uint(cast(int, arg)), b''

    elif type_str[:3] == 'int':
        return _encode_int(cast(int, arg)), b''

    elif type_str == 'bool':
        if not isinstance(arg, bool):
            raise ABIEncodingError(f'Expected bool. Got {type(arg)}')
        b = 1 if arg else 0
        return _encode_uint(b), b''

    elif 'fixed' in type_str:
        raise NotImplementedError('No fixed point numbers. Who even are you?')

    raise ValueError(f'Unknown type: {type_str}')


def _encode_offset(head_size: int, tail_pos: int) -> bytes:
    '''Encode the offset'''
    return _encode_uint((tail_pos + head_size) * 32)


def encode_many(type_list: List[str], arg_list: List[Any]) -> bytes:
    '''Encode many arguments into a single blob.'''
    head: List[bytes] = []
    tail: List[bytes] = []

    slot_usage = list(starmap(_slots_to_encode, zip(type_list, arg_list)))

    # will need to be redone for dynamic types
    head_size = sum([s[0] for s in slot_usage])
    head_pos = 0
    for (i, t, a) in zip(range(len(type_list)), type_list, arg_list):
        encoded_head, encoded_tail = encode(t, a)

        if encoded_head == b'':
            tail_pos = sum(s[1] for s in slot_usage[:i])
            offset = _encode_offset(head_size, tail_pos)
            encoded_head = offset

        head_pos += 1
        head.append(encoded_head)

        if encoded_tail != b'':
            tail.append(encoded_tail)

    return b''.join([*head, *tail])


def encode_tuple(type_tuple: str, args: List) -> bytes:
    '''Encode using an abi-format type-tuple e.g. "(bytes,int,address[])"'''
    # strip () and pass through
    type_tuple = type_tuple[1:-1]
    return encode_many(type_tuple.split(','), args)


def decode(type_str: str, b: bytes) -> Any:
    '''Decode an item from a bytestring'''
    if type_str[-2:] == '[]':
        return _decode_dynamic_array(type_str, b)
    elif '[' in type_str:
        return _decode_fixed_array(type_str, b)
    elif type_str == 'address':
        return _decode_address(b[:32])
    elif 'string' in type_str:
        return _decode_str(b)
    elif 'bytes' in type_str:
        if type_str == 'bytes':
            return _decode_dynamic_bytes(b)
        return _decode_fixed_bytes(b[:32], type_str)
    elif 'uint' in type_str:
        return _decode_uint(b[:32])
    elif 'int' in type_str:
        return _decode_int(b[:32])
    elif type_str == 'bool':
        return b[31:32] == b'\x01'
    elif 'fixed' in type_str:
        raise NotImplementedError('No fixed point numbers. Who even are you?')
    raise ValueError(f'Could not deserialize {type_str} with value {b.hex()}')


def decode_many(type_list: List[str], b: bytes) -> List[Any]:
    if len(b) % 32 != 0:
        raise ValueError('Invalid ABI blob. Expected multiple of 32 bytes')
    # arrays use extra slots depending on their length
    array_head_slots = sum([max(0, _array_length(t) - 1) for t in type_list])
    head_size = len(type_list) + array_head_slots

    # break up the whole thing into its 32-byte slots
    slots = [b[i:i + 32] for i in range(0, len(b), 32)]

    decoded = []
    head_pos = 0
    type_pos = 0
    while head_pos < head_size:
        outer = type_list[type_pos]

        # how many head items are in this?
        array_length = _array_length(outer)
        head_items = max(1, array_length)

        dec = []
        for i in range(head_items):
            h = slots[head_pos]
            t = outer if array_length == 0 else _inner_type(outer)
            if not _is_dynamic(t):
                value = decode(t, h)
            else:
                tail_loc = _decode_uint(h) // 32
                value = decode(t, b''.join(slots[tail_loc:]))
            dec.append(value)
            head_pos += 1
        type_pos += 1

        if array_length != 0:
            decoded.append(dec)
        else:
            decoded.extend(dec)
    return decoded


def decode_tuple(type_tuple: str, b: bytes) -> List:
    '''Decode an abi-format type-tuple e.g. "(bytes,int,address[])"'''
    # strip () and pass through
    type_tuple = type_tuple[1:-1]
    return decode_many(type_tuple.split(','), b)


def find(name: str, interface: EthABI) -> List[Dict[str, Any]]:
    return [e for e in interface if 'name' in e and e['name'] == name]


def _make_type_tuple(f: Dict[str, Any]) -> str:
    '''
    makes a comma-delimted type tuple
    for use in the signature and encoding
    e.g. '(bytes,bytes,bytes)'
    '''
    inputs: List[Dict[str, Any]] = f['inputs']
    types = ','.join(t['type'] for t in inputs)
    return f'({types})'


def make_signature(f: Dict[str, Any]) -> str:
    '''
    Parses a function or event ABI into a signture

    Args:
        f (dict): the function or event ABI
    Returns:
        (str): the signature
    '''
    type_tuple = _make_type_tuple(f)
    return f'{f["name"]}{type_tuple}'
