import collections
import itertools
import numpy

from dagpype._core import filters
import dagpype_c


__all__ = []


__all__ += ['chunk']
def chunk(max_elems = 8192, dtype = numpy.float64):
    """
    Transforms a sequence of elements into chunks.
    
    Keyword Arguments:
        max_elems -- Number of elements per chunk (last might have less) (default 8192).
        dtype -- Underlying element type (default numpy.float64)

    See Also:
        :func:`dagpype.np.unchunk`

    Example:

    >>> source([0.000000133, 2.3, 9.2, 4.3, -5]) | np.chunk() | np.min_()
    -5.0
    """

    @filters
    def _dagpype_internal_fn_act(target):
        assert max_elems > 0
        dtype_ = dtype

        l = []
        try:
            while True:
                while len(l) < max_elems:
                    l.append((yield))
                target.send(numpy.array(l, dtype = dtype_))
                l = []
        except GeneratorExit:
            if len(l) > 0:
                target.send(numpy.array(l, dtype = dtype_))        
            
    return _dagpype_internal_fn_act
    

__all__ += ['unchunk']
def unchunk():
    """
    Complementary action to chunk. Transforms the rows of an array to tuples.

    See Also:
        :func:`dagpype.np.chunk`

    Example:

    >>> l = source([numpy.array([[1, 2], [3, 4]])]) | np.unchunk() | to_list()
    >>> assert l[0] == (1, 2)
    """

    @filters
    def _dagpype_internal_fn_act(target):
        try:
            while True:
                a = (yield)
                if len(a) == 0:
                    continue
                if a.ndim == 1:
                    for i in range(a.shape[0]):
                        target.send(a[i])                     
                else:
                    for i in range(a.shape[0]):
                        target.send(tuple(a[i]))
        except GeneratorExit:
            if len(l) > 0:
                target.send(numpy.array(l, dtype = dtype_))        
            
    return _dagpype_internal_fn_act
                

__all__ += ['skip']
def skip(n):
    """
    Skips the first n elements (not chunks) from a stream of chunks.

    See Also:
        :func:`dagpype.skip`

    Example:

    >>> # Calculate the mean of 'wind' column elements except the first three.
    >>> np.chunk_stream_vals('meteo.csv', b'wind') | np.skip(3) | np.mean()
    7.3508771929824563
    """

    if n >= 0:
        @filters
        def _dagpype_internal_fn_act_p(target):
            remaining = n
            try:
                while True:
                    e = (yield)
                    if remaining == 0:
                        target.send(e)
                        continue
                    t = e.shape[0]
                    if t > remaining:
                        target.send(e[remaining :])
                        remaining = 0
                    else:
                        remaining -= t
            except GeneratorExit:
                target.close()

        return _dagpype_internal_fn_act_p

    @filters
    def _dagpype_internal_fn_act_n(target):
        m = -n
        pending = collections.deque([])
        try:
            while True:
                pending.append((yield))
                while len(pending) > 0:
                    first = pending.popleft()
                    if sum((e.shape[0] for e in pending)) >= m:                                
                        target.send(first)
                    else:
                        pending.appendleft(first)
                        break
        except GeneratorExit:
            if sum((e.shape[0] for e in pending)) < m:
                target.close()
                return
            while m > 0:
                e = pending.pop()
                if e.shape[0] < m:
                    m -= e.shape[0]
                else:
                    e = e[: e.shape[0] - m]
                    if e.shape[0] > 0:
                        pending.append(e)
                    break
            while len(pending) > 0:
                e = pending.pop()
                target.send(e)
            target.close()

    return _dagpype_internal_fn_act_n


# Tmp Ami - do more See Also
#def window_simple_ave(wnd_len):
#    """
#    See Also:
#        window_simple_ave
#    """
#
#    def _dagpype_internal_fn_act(target):
#        try:
#            while True:
#                pass
#        except GeneratorExit:
#            target.close()
#
#    return _dagpype_internal_fn_act


__all__ += ['cum_ave']
def cum_ave():
    """
    See Also:
        :func:`dagpype.np.cum_sum`
        :func:`dagpype.np.exp_ave`
        :func:`dagpype.cum_ave`

    Example:

    >>> # Reads from a CSV file, and writes the cumulative average to a different one.
    >>> np.chunk_stream_vals('meteo.csv', b'wind') | np.cum_ave() | np.chunks_to_stream('wind_ave.csv', b'wind')
    1
    """

    @filters
    def _dagpype_internal_fn_act(target):
        sum_, len_ = 0.0, 0
        try:
            while True:
                a = sum_ + numpy.cumsum( (yield) )
                if len(a) == 0:
                    continue
                target.send( numpy.divide(a, numpy.arange(1 + len_, 1 + len_ + len(a)) ) )
                sum_ = a[-1]
                len_ += len(a)
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['cum_sum']
def cum_sum():
    """
    See Also:
        :func:`dagpype.np.cum_ave`
        :func:`dagpype.cum_sum`

    Example:

    >>> # Reads from a CSV file, and writes the cumulative sum to a different one.
    >>> np.chunk_stream_vals('meteo.csv', b'wind') | np.cum_sum() | np.chunks_to_stream('wind_ave.csv', b'wind')
    1
    """

    @filters
    def _dagpype_internal_fn_act(target):
        sum_, len_ = 0.0, 0
        try:
            while True:
                a = sum_ + numpy.cumsum( (yield) )
                if len(a) == 0:
                    continue
                target.send(a)
                sum_ = a[-1]
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['exp_ave']
def exp_ave(alpha):
    """
    See Also:
        :func:`dagpype.np.cum_ave`
        :func:`dagpype.exp_ave`

    Example:

    >>> # Reads from a CSV file, and writes the exponential average to a different one.
    >>> np.chunk_stream_vals('meteo.csv', b'wind') | np.cum_ave() | np.chunks_to_stream('wind_ave.csv', b'wind')
    1
    """

    @filters
    def _dagpype_internal_fn_act(target):
        assert 0 <= alpha <= 1

        av = dagpype_c.ExpAverager(alpha)

        proto = numpy.array([1])
        try:
            while True: 
                e = numpy.copy((yield))
                assert type(e) == type(proto)
                assert len(e.shape) == 1
                r = e.copy()
                av.ave(e, r)
                target.send(r)
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['enumerate_']
def enumerate_(start = 0):

    """    
    Enumerates the elements of the chunks of a stream. Transforms it into a stream of pairs, where the first of each
        is a numpy.array of a running index.

    Arguments:
        start -- Starting value of running index (default 0).
        
    See Also:
        :func:`dagpype.enumerate_`
        
    Example:

    >>> source(['a', 'b', 'c', 'd']) | np.chunk(dtype = str) | np.enumerate_() | nth(0)
    (array([0, 1, 2, 3]), array(['a', 'b', 'c', 'd'], 
          dtype='|S1'))
    """

    @filters
    def _dagpype_internal_fn_act(target):
        count = start   
        try:
            while True:
                e = (yield)
                target.send((numpy.arange(count, count + len(e)), e))
                count += len(e)
        except GeneratorExit:           
            target.close()               

    return _dagpype_internal_fn_act

