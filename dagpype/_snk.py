import math
import csv
import collections
import random
import types
import itertools

from dagpype._core import sinks
import dagpype_c
_has_c_line_writer = 'line_writer' in dir(dagpype_c)


__all__ = []
    

__all__ += ['to_stream']
def to_stream(stream, names = None, delimit = b',', line_terminator = b'\n', buf_size = 256):    
    """
    Writes elements to an output stream; computes the number of lines written (excluding names). If an element
        is a tuple, its sub-elements will be separated by the delimit byte. Elements will be separated by   
        the line-terminator byte. 
    
    Arguments:
        stream -- Either a binary stream, e.g., as returned by open(..., 'wb'), or a name of a file.

    Keyword Arguments:
        names -- Either a byte array, a tuple of byte arrays, or None (default None). If not None, the names
            will be written (separated by the delimit byte if more than one), followed by the 
            line_terminator byte.
        delimit -- Delimiting binary character between elements (default b',').
        line_terminator -- Between-element binary character element (default b'\n')
        buf_size -- Number of elements buffered before writing (default 1024)

    See Also:
        :func:`dagpype.np.chunks_to_stream`
    
    Examples:

    >>> # Writes a CSV file of 3 lines, each containing 2 sub-elements
    >>> source([(1, 2), (3, 4), (5, 6)]) | to_stream('data.csv')
    3
    
    >>> # Same but with headings
    >>> source([(1, 2), (3, 4), (5, 6)]) | to_stream('data.csv', names = ('wind', 'rain'))
    3

    >>> # Same but with tab separators.
    >>> source([(1, 2), (3, 4), (5, 6)]) | to_stream('data.csv', names = ('wind', 'rain'), delimit = b'\t')
    3
    """
    
    @sinks
    def _dagpype_internal_fn_act(target):
        class _LineWriter(object):
            def __init__(self, stream_, line_terminator, w):
                self._stream_ = stream_
                self._line_terminator = line_terminator
                self._w = w
                self._n = 0
                self._first = True
                
            def write(self, stored):
                if self._w is not None:
                    dagpype_c.line_writer_write(self._w, stored)
                    return
                self._n += len(stored)
                self._stream_.write(
                    line_terminator + line_terminator.join(stored) if not self._first else \
                        line_terminator.join(stored))
                self._first = False
            
            def close(self):
                if self._w is not None:
                    return dagpype_c.line_writer_close(self._w)
                return self._n
                
        def _encode(e):
            return e if isinstance(e, bytes) else str(e).encode()                    
                    
        def _stringify_tup(tup):
            return delimit.join(_encode(e) for e in tup)
            
        stream_ = open(stream, 'wb') if isinstance(stream, str) else stream
        
        if names is not None:        
            stream_.write((_stringify_tup(names) if isinstance(names, tuple) else names) + line_terminator)
            stream_.flush()
            
        writer = _LineWriter(
            stream_, 
            line_terminator, 
            dagpype_c.line_writer(stream_.fileno(), line_terminator) if _has_c_line_writer else None)     
        
        stored = []
        try:
            e = (yield)
            if isinstance(e, tuple):                
                while True:      
                    stored.append(_stringify_tup(e))
                    if len(stored) > buf_size:
                        writer.write(stored)
                        stored = []
                    e = (yield)
            elif isinstance(e, bytes):
                while True:
                    stored.append(e)
                    if len(stored) > buf_size:
                        writer.write(stored)
                        stored = []
                    e = (yield)
            else:
                while True:
                    stored.append(_encode(e))
                    if len(stored) > buf_size:
                        writer.write(stored)
                        stored = []
                    e = (yield)
        except GeneratorExit:
            if len(stored) > 0:
                writer.write(stored)
            target.send( writer.close() )    
            target.close()

        if isinstance(stream, bytes):
            stream_.close()

    return _dagpype_internal_fn_act


__all__ += ['sum_']
def sum_():
    """
    Computes the sum of piped elements. 

    See Also:
        :func:`dagpype.np.sum_`

    Example:

    >>> source([1, 2, 3, 4]) | sum_()
    10

    >>> source(['1', '2', '3', '4']) | sum_()
    '1234'
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        try:
            s = (yield)
            while True:
                s += (yield)
        except GeneratorExit:
            target.send(s)
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['count']
def count():
    """
    Computes the number of piped elements. 

    See Also:
        :func:`dagpype.np.count`

    Example:

    >>> source([1, 2, 3, 4]) | count()
    4
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        n = 0
        try:
            while True:
                (yield)
                n += 1
        except GeneratorExit:
            target.send(n)
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['nth']
def nth(n):
    """
    Returns the n-th piped element.

    Arguments:
        n - If a positive integer, returns nth element from start, else
            return nth element from n.

    See Also:
        :func:`dagpype.skip`

    Example:

    >>> source([1, 2, 3, 4]) | nth(0) 
    1

    >>> source([1, 2, 3, 4]) | nth(-1)
    4
    """

    if n >= 0:
        @sinks
        def _dagpype_internal_fn_act_p(target):
            i = 0
            try:
                while True:
                    e = (yield)
                    if i == n:
                        target.send(e)
                        target.close()
                        return
                    i += 1
            except GeneratorExit:
                target.close()

        return _dagpype_internal_fn_act_p

    @sinks
    def _dagpype_internal_fn_act_n(target):
        q = collections.deque([], -n)
        try:
            while True:
                q.append((yield))
        except GeneratorExit:
            if len(q) >= -n:
                target.send(q.popleft())
            target.close()

    return _dagpype_internal_fn_act_n


__all__ += ['to_list']
def to_list():
    """
    Converts all elements to a list.

    See Also:
        :func:`dagpype.to_dict`
        :func:`dagpype.np.to_array`

    Example:

    >>> source((1, 2, 3, 4)) | to_list()
    [1, 2, 3, 4]
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        l = []
        try:
            while True:
                l.append((yield))
        except GeneratorExit:
            target.send(l)    
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['to_dict']
def to_dict():
    """
    Converts all elements to a dictionary. Given tuples, the first entry of each is the key, and
    the second is the data.

    See Also:
        :func:`dagpype.to_list`
        :func:`dagpype.np.to_array`

    Example:

    >>> source(((1, 'a'), (2, 'b'), (3, 'b'), (4, 'j'))) | to_dict()
    {1: 'a', 2: 'b', 3: 'b', 4: 'j'}
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        d = dict([])
        try:
            while True:
                e = (yield)
                d[e[0]] = e[1]
        except GeneratorExit:
            target.send(d)
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['mean']
def mean():
    """
    Calculates the mean of all elements.

    See Also:
        :func:`dagpype.stddev`
        :func:`dagpype.np.mean`

    Example:

    >>> int(source([2, 4, 4, 4, 5, 5, 7, 9]) | mean())
    5
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        s, n = 0, 0
        try:
            while True:
                s += (yield)
                n += 1
        except GeneratorExit:
            if n > 0:
                target.send(s / n)
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['stddev']
def stddev(ddof = 1):
    """
    Calculates the sample standard deviation.

    Keyword Arguments:
        ddof -- Degrees of freedom (default 1)

    if:
        s is the sum of xs,
        ss is the sum of squared xs
        n is the number of xs,
    then:
        stddev = math.sqrt((ss - s * s / n) / (n - ddof))

    See Also:
        :func:`dagpype.mean`

    Example:

    >>> source([2, 4, 4, 4, 5, 5, 7, 9]) | stddev(0)
    2.0
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        s, ss, n = 0, 0, 0
        try:
            while True:
                e = (yield)
                s += e
                ss += e * e
                n += 1
        except GeneratorExit:
            if n > ddof:
                res = math.sqrt((ss - s * s / float(n)) / (n - ddof))
                target.send(res)
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['corr']
def corr():
    """
    Calculates the Pearson correlation coefficient between tuples.

    if:
    
        n is the number of elements
        
        sx is the sum of xs
        
        sy is the sum of ys
        
        sxx is the sum of squared xs 
        
        syy is the sum of squared ys
        
        sxy is the sum of xys
        
    then:
    
        corr = (n * sxy - sx * sy) / math.sqrt(n * sxx - sx * sx) / math.sqrt(n * syy - sy * sy)

    See Also:
        :func:`dagpype.np.corr`

    Examples:
    
    >>> source([1, 2, 3, 4]) + source([1, 2, 3, 4]) | corr() 
    1.0
    
    1.0

    >>> source([(60, 3.1), (61, 3.6), (62, 3.8), (63, 4), (65, 4.1)]) | corr()
    0.9118724953377315
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        c = dagpype_c.Correlator()
        try:
            while True:
                x, y = (yield)
                c.push(float(x), float(y))
        except GeneratorExit:
            target.send(c.corr())
            target.close()
    return _dagpype_internal_fn_act


__all__ += ['sink']
def sink(res):
    """
    General purpose sink.

    Arguments:
        res -- Result. If this is a function, the result is the function applied
            to the last argument. Otherwise, the result is this parameter independent 
            from the sequence

    See Also:
        :func:`dagpype.filt`

    Examples:

    >>> source([1, 2, 3]) | sink(lambda x : x ** 2)
    9

    >>> source([1, 2]) | sink('hello')
    'hello'

    >>> source([1, 2, 3]) | sink('hello')
    'hello'
    """

    if isinstance(res, types.FunctionType):
        @sinks
        def _dagpype_internal_fn_act(target):
            try:
                has = False
                while True:
                    last = (yield)
                    has = True
            except GeneratorExit:   
                if has:
                    target.send(res(last))
    else:
        @sinks
        def _dagpype_internal_fn_act(target):
            try:
                while True:
                    (yield)
            except GeneratorExit:
                target.send(res)

    return _dagpype_internal_fn_act


__all__ += ['min_']
def min_():
    """
    Computes the smallest element.

    See Also:
        :func:`dagpype.max_`
        :func:`dagpype.np.min_`

    Example:
    >>> source([1, 2, 3, 4]) | min_()
    1
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        has = False
        try:
            m = (yield)
            has = True
            while True:
                m = min((yield), m)
        except GeneratorExit:
            if has:
                target.send(m)
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['max_']
def max_():
    """
    Computes the largest element.

    See Also:
        :func:`dagpype.min_`

    Example:

    >>> source([1, 2, 3, 4]) | max_()
    4
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        has = False
        try:
            m = (yield)
            has = True
            while True:
                m = max((yield), m)
        except GeneratorExit:
            if has:
                target.send(m)
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['size_rand_sample']
def size_rand_sample(size):
    """
    Randomly samples (with replacement) a random sample with a given size. Returns
        a list of the sampled elements.
    
    Arguments:
        size -- Sample size.

    See Also:
        :func:`dagpype.prob_rand_sample`

    Example:

    >>> # Create a sample of size 2 from 0 : 100.
    >>> sample = source(range(100)) | size_rand_sample(2) 
    """

    assert size > 0
    @sinks
    def _dagpype_internal_fn_act(target):
        i = 0
        sample = None
        try:
            while True:
                e = (yield)
                sample = [e] * size if i == 0 else [e if random.randint(0, i) == 0 else ee for ee in sample]
                i += 1
        except GeneratorExit:
            if sample is not None:
                target.send(sample)
            target.close()

    return _dagpype_internal_fn_act

