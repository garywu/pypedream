import itertools
import numpy
import sys
if sys.version_info >= (3, 0):
    _zip = zip
    _zip_longest = itertools.zip_longest
else:
    _zip = itertools.izip
    _zip_longest = itertools.izip_longest

try:
    from ._core import Error, InvalidParamError
except ValueError:
    from _core import Error, InvalidParamError
import dagpype_c


__all__ = []


class UnknownNamedCSVColError(Error, ValueError):
    """    Indicates a name was not found in a CSV header.
    """
    def __init__(self, name):
        """
        Constructor.

        Arguments:
        name -- Name of column that could not be found.
        """
        Error.__init__(self, b'Could not find ' + name)
        self._name = name

    def name(self):
        """
        Returns problematic name.
        """
        return self._name
__all__ += ['UnknownNamedCSVColError']


def cols_are_type(cols, type_):
    if isinstance(cols, bytes):
        return bytes == type_

    try:
        if cols is None:
            return False
        if isinstance(cols, type_):
            return True
        if isinstance(cols[0], bytes):
            for c in cols[1: ]:
                if not isinstance(c, bytes):
                    raise InvalidParamError('cols', cols, 'Must be homogeneous')
            return type_ == bytes                    
        if isinstance(cols[0], type_):
            for c in cols[1: ]:
                if not isinstance(c, type_):
                    raise InvalidParamError('cols', cols, 'Must be homogeneous')
            return True
        return False
    except:
        return False


def _process_inds(inds):
    uniques = sorted(list(set(inds)))
    unique_inds = dict((ind, i) for i, ind in enumerate(uniques))
    copies = [unique_inds[i] for i in inds]
    return uniques, copies, max(inds) if len(inds) > 0 else -1


_int = 0
_float = 1
_str = 2

_inds_cols = 0
_names_cols = 1
_all_cols = 2


def _inds_from_cols(stream, cols, types_, delimit, comment, skip_init_space):
    if cols_are_type(cols, bytes):
        single = isinstance(cols, bytes)
        firsts = dagpype_c.line_to_tuple(
            stream, 
            delimit, comment, 1 if skip_init_space else 0)
        firsts = dict((firsts, i) for i, firsts in enumerate(firsts))
        if isinstance(cols, bytes):
            cols = (cols,)
        inds = []
        for col in cols:
            if col not in firsts:
                raise UnknownNamedCSVColError(col)
            inds.append(firsts[col])
        uniques, copies, max_ind = _process_inds(inds)         
    elif cols_are_type(cols, int):
        single = isinstance(cols, int)
        if isinstance(cols, int):
            cols = (cols,)
        inds = cols
        uniques, copies, max_ind = _process_inds(inds) 
    elif types_ is not None and cols is None:
        single = not isinstance(types_, tuple)
        if not isinstance(types_, tuple):
            types_ = (types_,)
        inds = list(range(len(types_)))
        uniques, copies, max_ind = _process_inds(inds) 
    elif types_ is None:
        single = False
        inds = ()
        uniques, copies, max_ind = _process_inds(inds) 
    else:
        raise InvalidParamError(b'cols', cols, b'Unknown')

    return cols, single, inds, uniques, copies, max_ind


def _csv_attribs(stream, cols, types_, delimit, comment, skip_init_space):
    if not isinstance(delimit, type(b'')) or len(delimit) != 1:
        raise InvalidParamError('delimit', delimit, 'Must be a length-1 string')
    if comment is not None and (not isinstance(comment, type(b'')) or len(comment) != 1):
        raise InvalidParamError('comment', comment, 'Must be a length-1 string')

    cols, single, inds, uniques, copies, max_ind = _inds_from_cols(
        stream, cols, types_, delimit, comment, skip_init_space)

    c_types, cast_back = (), False
    if types_ is not None:
        for t in types_ if isinstance(types_, tuple) else (types_,):
            if t == int:
                c_types = c_types + (_int,)
            elif t == float:
                c_types = c_types + (_float,)
            elif t == bytes:
                c_types = c_types + (_str,)
            else:
                c_types = c_types + (_str,)
                cast_back = True
    if cast_back:
        types_ = types_ if isinstance(types_, tuple) else (types_,)
        c_types = (_str,) * len(types_) 

    return (cols, single, inds, uniques, copies, max_ind, types_, c_types, cast_back)


def _make_bufs(c_types, max_field_len, max_elems):
    bufs = []
    for t in c_types:
        if t == _int:
            bufs.append( numpy.array(range(max_elems), dtype = int) )
        elif t == _float:
            bufs.append( numpy.array(range(max_elems), dtype = float) )
        elif t == _str:
            bufs.append( numpy.array(range(max_field_len * max_elems), dtype = bytes) )
    return bufs


def _copy_array(buf, type_, len_, max_field_len, max_elems):
    if type_ == bytes:
        strs = []
        for i in range(len_):
            len_ = 100 * int(buf[max_field_len * i]) + 10 * int(buf[max_field_len * i + 1]) + int(buf[max_field_len * i + 2])
            str_ = type_().join(type_(buf[j]) for j in range(max_field_len * i + 3, max_field_len * i + 3 + len_))
            strs.append(str_)
        return numpy.array(strs, dtype = type_)

    if len_ < max_elems:
        return numpy.array(buf[: len_], copy = True, dtype = type_)
    return numpy.array(buf, copy = True, dtype = type_)


def array_read(stream, cols, types_, missing_vals, delimit, comment, skip_init_space, max_elems):
    (cols, single, inds, uniques, copies, max_ind, types_, c_types, cast_back) = \
        _csv_attribs(stream, cols, types_, delimit, comment, skip_init_space)

    assert max_elems > 0
    
    def _encode(e):
        return e if isinstance(e, bytes) else str(e).encode()                    

    c_missing_vals = (_encode(missing_vals), ) if single else tuple(_encode(m) for m in missing_vals)
    assert len(cols) == len(c_types) == len(c_missing_vals)

    max_field_len = dagpype_c.parser_max_field_len()
    assert max_field_len > 0

    bufs = _make_bufs(c_types, max_field_len, max_elems)

    r = dagpype_c.ArrayColReader(
        stream, 
        delimit, comment, 1 if skip_init_space else 0, 
        1 if single else 0,
        inds, uniques, copies, max_ind,
        c_types, 
        c_missing_vals,
        max_elems,
        bufs)

    for len_ in r:
        if len_ == 0:
            break
        if single:
            payload = _copy_array(bufs[0], types_, len_, max_field_len, max_elems)
        else:
            payload = \
                tuple(_copy_array(buf, type_, len_, max_field_len, max_elems) for buf, type_ in _zip(bufs, types_))
        yield payload
        if len_ < max_elems:
            break


def _cast(a, b):
    return b(a) if a is not None and b is not None else a


def read(stream, cols, types_, delimit, comment, skip_init_space):
    (cols, single, inds, uniques, copies, max_ind, types_, c_types, cast_back) = \
        _csv_attribs(stream, cols, types_, delimit, comment, skip_init_space)

    r = dagpype_c.ColReader(
        stream, 
        delimit, comment, 1 if skip_init_space else 0, 
        1 if single else 0,
        inds, uniques, copies, max_ind,
        c_types)
        
    if not cast_back:
        for t in r:
            yield t
        return

    if single:
        for t in r:
            yield _cast(t, types_[0])
        return

    for t in r:
        yield tuple(_cast(a, b) for a, b in _zip_longest(t, types_))

