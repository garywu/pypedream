import numpy
import itertools

from dagpype._core import sources
from dagpype._csv_utils import array_read as _csv_utils_array_read


__all__ = []


def _stream_chunk(reader, dtype_, max_elems, num_cols):
    s = reader.read(dtype_().itemsize * max_elems * num_cols)
    if not s:
        return None
    a = numpy.fromstring(s, dtype = dtype_) 
    if num_cols > 1:
        a = a.reshape(len(a) / num_cols, num_cols)
    return a


__all__ += ['chunk_stream_bytes']
def chunk_stream_bytes(stream, max_elems = 8192, dtype = numpy.float64, num_cols = 1):
    """
    Reads a binary file containing a numpy.array, and emits a series of chunks. Each chunk
        is a numpy array with num_cols columns.
    
    Arguments:
        stream -- Either the name of a file or a *binary* stream. 
    
    Keyword Arguments:
        max_elems -- Number of rows per chunk (last might have less) (default 8192).
        dtype -- Underlying element type (default numpy.float64)
        num_cols -- Number of columns in the chunks' arrays (default 1).

    See Also:
        :func:`dagpype.np.chunk_stream_vals`
        :func:`dagpype.np.chunks_to_stream_bytes`

    Example:

    >>> # Reads from a binary file, and writes the cumulative average to a different one.
    >>> np.chunk_stream_bytes('meteo.dat') | np.cum_ave() | np.chunks_to_stream_bytes('wind_ave.dat')
    5
    """
    
    @sources
    def _dagpype_internal_fn_act():
        assert num_cols >= 1
        assert max_elems > 0

        reader = open(stream, 'rb') if isinstance(stream, str) else stream
        
        while True:
            a = _stream_chunk(reader, dtype, max_elems, num_cols)
            if a is None:
                break
            yield a

        if isinstance(stream, str):
            reader.close()
    
    return _dagpype_internal_fn_act


__all__ += ['chunk_stream_vals']
def chunk_stream_vals(stream, 
    cols, 
    types_ = None, 
    missing_vals = None,
    delimit = b',', 
    comment = None, 
    skip_init_space = True,
    max_elems = 8192):

    """
    Streams delimited (e.g., by commas for CSV files, or by tabs for TAB files) values as tuples of
        numpy.arrays.

    Arguments:
        stream -- Either the name of a file or a *binary* stream. 
        cols -- Indication of which columns to read. If either an integer or a tuple of integers,
            the corresponding columns will be read. If either a string or a tuple of strings, the 
            columns whose first rows have these string names (excluding the first row) will be 
            read. 

    Keyword Arguments:
        types_ -- Either None, a type, or a tuple of types (must correspond to cols). The read values will
            be cast to these types. If None, this is a tuple of floats.
        missing_vals -- Either None, a value, or a tuple of values (must correspond to cols). Missing values will be filled from 
            this parameter. If None, this is a tuple of 0s cast to types_.
        delimit -- Delimiting binary character (default b',').
        comment -- Comment-starting binary character or ``None`` (default). 
            Any character starting from this one until the line end will be ignored.
        skip_init_space -- Whether spaces starting a field will be ignored (default True).
        max_elems -- Number of rows per chunk (last might have less) (default 8192).

    See Also:
        :func:`dagpype.stream_vals`
        :func:`dagpype.np.chunk_stream_bytes`

    Examples:

    >>> # Find the correlation between two named columns.
    >>> np.chunk_stream_vals('meteo.csv', (b'day', b'wind'), (float, float), (0, 0)) | np.corr()    
    0.019720323758326334
    >>> #Equivalent to:    
    >>> np.chunk_stream_vals('meteo.csv', (b'day', b'wind')) | np.corr()    
    0.019720323758326334

    >>> # Find the correlation between two indexed columns.
    >>> np.chunk_stream_vals('neat_data.csv', (3, 0)) | np.corr()    
    -0.084075296393769511
    """

    def _is_it_t(type_):
        return isinstance(type_, list) or isinstance(type_, tuple)

    if types_ is None:
        types_ = tuple(float for _ in cols) if _is_it_t(cols) else float
    if missing_vals is None:
        missing_vals = tuple(type_(0) for type_ in types_) if _is_it_t(types_) else types_(0)
    @sources
    def _dagpype_internal_fn_act():
        assert max_elems > 0
    
        stream_ = open(stream, 'rb') if isinstance(stream, str) else stream

        for t in _csv_utils_array_read(stream_, cols, types_, missing_vals, delimit, comment, skip_init_space, max_elems):
            yield t

        if isinstance(stream, str):
            stream_.close()

    return _dagpype_internal_fn_act


__all__ += ['chunk_source']
def chunk_source(seq, max_elems = 1024):
    """
    Streams stream elements as lists.

    Arguments:
        seq -- Some sequence.

    Keyword Arguments:
        max_elems -- Number of rows per chunk (last might have less) (default 1024).

    See Also:
        :func:`dagpype.source`
    """

    @sources
    def _dagpype_internal_fn_act():
        def _next_batch(it):
            return [l for l in itertools.islice(it, max_elems)]
    
        it = iter(seq)
        items = _next_batch(it)
        while items:
            yield items
            items = _next_batch(it)

    return _dagpype_internal_fn_act

