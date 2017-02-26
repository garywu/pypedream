import numpy
import math
import types

from dagpype._core import sinks


__all__ = []


__all__ += ['chunks_to_stream']
def chunks_to_stream(stream, names = None, fmt = '%.18e', delimit = b',', line_terminator = b'\n'):    
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
        fmt -- See corresponding parameter in numpy.savetxt
        delimit -- Delimiting binary character between elements (default b',').
        line_terminator -- Between-element binary character element (default b'\n')

    See Also:
        :func:`dagpype.to_stream`
    
    Examples:

    >>> # Reads from a CSV file, and writes the cumulative average to a different one.
    >>> np.chunk_stream_vals('meteo.csv', b'wind') | np.cum_ave() | np.chunks_to_stream('wind_ave.csv', b'wind')
    1
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        stream_ = open(stream, 'wb') if isinstance(stream, str) else stream
        
        str(delimit), str(line_terminator)

        if names is not None:
            stream_.write((delimit.join(names) if isinstance(names, tuple) else names) + line_terminator)
            
        delimit_ = delimit.decode('utf-8')
        line_terminator_ = line_terminator.decode('utf-8')                    
            
        n = 0
        try:
            while True:
                e = (yield)
                numpy.savetxt(stream_, e, fmt, delimit_, line_terminator_)
                n += 1
        except GeneratorExit:
            target.send(n)    
            target.close()

        if isinstance(stream, str):
            stream_.close()

    return _dagpype_internal_fn_act


__all__ += ['chunks_to_stream_bytes']
def chunks_to_stream_bytes(stream):
    """
    Writes chunks to a binary stream.

    See Also:
        :func:`dagpype.np.chunk_stream_bytes`
        :func:`dagpype.np.chunks_to_stream`
        :func:`dagpype.to_stream`

    Example:

    >>> # Reads from a binary file, and writes the cumulative average to a different one.
    >>> np.chunk_stream_bytes('meteo.dat') | np.cum_ave() | np.chunks_to_stream_bytes('wind_ave.dat')
    5
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        with open(stream, 'wb') if isinstance(stream, str) else stream as writer:
            dtype = None        
            n = 0
            try:           
                while True:
                    a = (yield)
                    if dtype is None:   
                        dtype = a.dtype
                    assert dtype == a.dtype
                    n += len(a)
                    writer.write(a.tostring())    
            except GeneratorExit:
                target.send(n)
                target.close()

    return _dagpype_internal_fn_act


__all__ += ['corr']
def corr():
    """
    Finds the correlation between streams of chunk-pairs, or between streams of 2-column chunks.

    See Also:
        :func:`dagpype.corr`

    Examples:

    >>> # Find the correlation between two indexed columns.
    >>> np.chunk_stream_vals('neat_data.csv', cols = (3, 0)) | np.corr()    
    -0.084075296393769511
    """

    @sinks
    def act_(target):
        sx, sxx, sy, syy, sxy, n = 0, 0, 0, 0, 0, 0
        try:
            while True:
                xy = (yield)
                if isinstance(xy, tuple):                
                    x, y = xy
                    sx += numpy.sum(x)
                    sxx += numpy.dot(x, x)
                    sy += numpy.sum(y)
                    sxy += numpy.dot(x, y)
                    syy += numpy.dot(y, y)
                    n += len(x)
                else:
                    if len(xy) == 0:
                        continue
                    assert xy.shape[1] == 2

                    s = numpy.sum(xy, axis = 0)
                    sx += s[0]
                    sy += s[1]

                    c = numpy.dot(xy.T, xy)

                    sxx += c[0, 0]
                    sxy += c[0, 1]
                    syy += c[1, 1]

                    n += xy.shape[0]
        except GeneratorExit:
            if n > 0:
                res = (n * sxy - sx * sy) / math.sqrt(n * sxx - sx * sx) / math.sqrt(n * syy - sy * sy)
                target.send(res)
            target.close()
    return act_
    

__all__ += ['to_array']
def to_array(dtype = None):
    """
    Converts all elements to a numpy.array.

    Keyword Arguments:
    dtype -- Same as in the ctor of numpy.array (default None).

    Examples:

    >>> source(((1, 2), (3, 4))) | np.to_array()
    array([[1, 2],
           [3, 4]])

    >>> a = source([1, 2, 3, 4]) | np.to_array(dtype = numpy.float64)
    """
    @sinks
    def _dagpype_internal_fn_act(target): 
        l = []
        try:
            while True:
                l.append((yield))
        except GeneratorExit:
            d = dtype
            target.send(numpy.array(l, dtype = d))
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['sum_']
def sum_(axis = None):
    """
    Computes the sum of piped chunks' elements. 

    Keyword Arguments:
        axis -- Axis over which the sum is taken (default None, all elements summed)

    See Also:
        :func:`dagpype.sum_`
        :func:`dagpype.np.chunks_sum`

    Examples:

    >>> np.chunk_stream_bytes('meteo.dat') | np.sum_()
    5.9399999999999995

    >>> source([1, 2, 3, 4]) | np.chunk() | np.sum_()
    10.0
    
    >>> source([(1, 2), (3, 4)]) | np.chunk() | np.sum_()
    10.0

    >>> source([(1, 2), (3, 4)]) | np.chunk() | np.sum_(axis = 0)
    array([ 4.,  6.])
    """
    @sinks
    def _dagpype_internal_fn_act(target):
        s = 0
        try:
            while True:
                s += numpy.sum((yield), axis)
        except GeneratorExit:
            target.send(s)
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['mean']
def mean(axis = None):
    """
    Computes the mean of piped chunks' elements. 

    Keyword Arguments:
        axis -- Axis over which the mean is taken (default None, all elements summed)

    See Also:
        :func:`dagpype.mean`

    Examples:

    >>> np.chunk_stream_bytes('meteo.dat') | np.mean()
    1.1879999999999999

    >>> source([1, 2, 3, 4]) | np.chunk() | np.mean()
    2.5
    
    >>> source([(1, 2), (3, 4)]) | np.chunk() | np.mean()
    2.5

    >>> source([(1, 2), (3, 4)]) | np.chunk() | np.mean(axis = 0)
    array([ 2.,  3.])
    """
    @sinks
    def _dagpype_internal_fn_act(target):
        s, n = 0, 0
        try:
            while True:
                a = (yield)
                s += numpy.sum(a, axis)
                n += a.shape[0] if axis is not None else a.size
        except GeneratorExit:
            target.send(s / n)
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['min_']
def min_(axis = None):
    """
    Computes the minimum of piped chunks' elements. 

    Keyword Arguments:
        axis -- Axis over which the minimum is taken (default None)

    See Also:
        :func:`dagpype.np.max_`
        :func:`dagpype.min_`

    Examples:

    >>> np.chunk_stream_bytes('meteo.dat') | np.min_()
    -1.0

    >>> source([1, 2, 3, 4]) | np.chunk() | np.min_()
    1.0
    
    >>> source([(1, 2), (3, 4)]) | np.chunk() | np.min_()
    1.0

    >>> source([(1, 2), (3, 4)]) | np.chunk() | np.min_(axis = 0)
    array([ 1.,  2.])
    """
    @sinks
    def _dagpype_internal_fn_act(target):
        has = False
        try:
            while True:
                cm = (yield).min(axis)
                if not has:
                    m = cm
                else:
                    m = min(cm, m) if axis is None else numpy.minium(cm, m)
                has = True
        except GeneratorExit:
            if has:
                target.send(m)
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['max_']
def max_(axis = None):
    """
    Computes the maximum of piped chunks' elements. 

    Keyword Arguments:
        axis -- Axis over which the maximum is taken (default None)

    See Also:
        :func:`dagpype.np.min_`
        :func:`dagpype.max_`

    Examples:

    >>> np.chunk_stream_bytes('meteo.dat') | np.max_()
    3.1400000000000001

    >>> source([1, 2, 3, 4]) | np.chunk() | np.max_()
    4.0
    
    >>> source([(1, 2), (3, 4)]) | np.chunk() | np.max_()
    4.0

    >>> source([(1, 2), (3, 4)]) | np.chunk() | np.max_(axis = 0)
    array([ 3.,  4.])
    """
    @sinks
    def _dagpype_internal_fn_act(target):
        has = False
        try:
            while True:
                cm = (yield).max(axis)
                if not has:
                    m = cm
                else:
                    m = min(cm, m) if axis is None else numpy.maximum(cm, m)
                has = True
        except GeneratorExit:
            if has:
                target.send(m)
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['count']
def count():
    """
    Computes the number of piped chunks' elements. 

    See Also:   
        :func:`dagpype.count`

    Examples:

    >>> np.chunk_stream_bytes('meteo.dat') | np.count()
    5

    >>> source([1, 2, 3, 4]) | np.chunk() | np.count()
    4
    
    >>> source([(1, 2), (3, 4)]) | np.chunk() | np.count()
    2
    """
    @sinks
    def _dagpype_internal_fn_act(target):
        s = 0
        try:
            while True:
                s += (yield).shape[0]
        except GeneratorExit:
            target.send(s)
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['vstack_chunks']
def vstack_chunks():
    """
    Stacks chunks vertically. They must have the same size.
    
    See Also:
        :func:`dagpype.np.concatenate_chunks`

    Example:

    >>> source([numpy.array([1, 2, 3, 4]), numpy.array([5, 6, 7, 8])]) | np.vstack_chunks()
    array([[1, 2, 3, 4],
           [5, 6, 7, 8]])
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        e = None
        try:
            while True:   
                e = (yield) if e is None else numpy.vstack((e, (yield))) 
        except GeneratorExit:
            if e is not None:
                target.send(e)
            target.close()
    return _dagpype_internal_fn_act


__all__ += ['concatenate_chunks']
def concatenate_chunks():
    """
    Concatenates chunks.

    See Also:
        :func:`dagpype.np.vstack_chunks`
    
    Example:

    >>> assert numpy.allclose(source(range(30000)) | np.chunk() | np.concatenate_chunks(), numpy.array(range(30000)))
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        e = None
        try:
            while True:   
                e = (yield) if e is None else numpy.concatenate((e, (yield))) 
        except GeneratorExit:
            if e is not None:
                target.send(e)
            target.close()
    return _dagpype_internal_fn_act


__all__ += ['chunks_sum']
def chunks_sum():
    """
    Sums chunks. They must have the same size.
    
    Example:

    >>> source([numpy.array([1, 2, 3, 4]), numpy.array([5, 6, 7, 8])]) | np.chunks_sum()
    array([ 6,  8, 10, 12])
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        e = None
        try:
            while True:
                if e is None:
                    e = numpy.array((yield))
                else:
                    e += numpy.array((yield))
        except GeneratorExit:
            if e is not None:
                target.send(e)
            target.close()
    return _dagpype_internal_fn_act


__all__ += ['chunks_mean']
def chunks_mean():
    """
    Finds means chunks. They must have the same size.
    
    See Also:
        :func:`dagpype.chunks_stddev`

    Example:

    >>> source([numpy.array([1, 2, 3, 4], dtype = float), numpy.array([5, 6, 7, 8])]) | np.chunks_mean()
    array([ 3.,  4.,  5.,  6.])
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        n = 0
        try:
            while True:
                if n > 0:
                    e += numpy.array((yield))
                else:
                    e = numpy.array((yield))
                n += 1
        except GeneratorExit:
            if n > 0:
                target.send(e / n)
            target.close()
    return _dagpype_internal_fn_act


__all__ += ['chunks_stddev']
def chunks_stddev(ddof = 1):
    """
    Calculates the sample standard deviation of chunks. They must have the same size.
    See the documentation of stddev in the parent module.

    See Also:
        :func:`dagpype.chunks_mean`
    
    Example:

    >>> source([numpy.array([1, 2, 3, 4]), numpy.array([5, 6, 7, 8])]) | np.chunks_stddev()
    array([ 2.82842712,  2.82842712,  2.82842712,  2.82842712])
    """

    @sinks
    def _dagpype_internal_fn_act(target):
        n = 0
        try:
            while True:
                e = numpy.array((yield))                
                if n > 0:   
                    s += e
                    ss += e * e
                else:
                    s = e
                    ss = e * e
                n += 1
        except GeneratorExit:
            if n > ddof:
                res = numpy.sqrt((ss - s * s / n) / (n - ddof))
                target.send(res)
            target.close()
    return _dagpype_internal_fn_act

