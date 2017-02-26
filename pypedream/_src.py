import os
import sys
try:
    import xml.etree.cElementTree as _element_tree
except ImportError:
    import xml.etree.ElementTree as _element_tree
import types
import csv
import io
import itertools

import _csv_utils
try:
    from ._core import Error
    from ._core import sources, source
    from ._csv_utils import UnknownNamedCSVColError
except ValueError:
    from _core import Error
    from _core import sources, source
    from _csv_utils import UnknownNamedCSVColError
import dagpype_c


__all__ = []


__all__ += ['stream_lines']
def stream_lines(stream, rstrip = True):
    """
    Streams the lines from some stream.

    Arguments:
        stream -- Either a stream, e.g., as returned by open(), or a name of a file.

    Keyword Arguments:
        rstrip -- if True, right-strips lines (default True).

    See Also:
        :func:`dagpype.stream_vals`
        :func:`dagpype.np.chunk_stream_lines`

    Examples:

    >>> # Places a file's lines in a list.
    >>> stream_lines('data.csv') | to_list()
    ['wind rain', '1 2', '3 4', '5 6']
    """

    @sources
    def _dagpype_internal_fn_act():
        stream_ = open(stream, 'rb') if isinstance(stream, str) else stream
        
        if rstrip:
            for l in stream_:
                yield l.rstrip()
        else:
            for l in stream_:
                yield bytes(l);

        if isinstance(stream, str):
            stream_.close()

    return _dagpype_internal_fn_act


__all__ += ['stream_vals']
def stream_vals(stream, 
    cols = None, 
    types_ = None, 
    delimit = b',', 
    comment = None, 
    skip_init_space = True):
    """
    Streams delimited (e.g., by commas for CSV files, or by tabs for TAB files) values as tuples.

    Arguments:
        stream -- Either the name of a file or a *binary* stream. 

    Keyword Arguments:
        cols -- Indication of which columns to read. If either an integer or a tuple of integers,
            the corresponding columns will be read. If either a string or a tuple of strings, the 
            columns whose first rows have these string names (excluding the first row) will be 
            read. If None (which is the default), everything will be read. 
        types_ -- Either a type or a tuple of types. If this is given, the read values will
            be cast to these types. Otherwise, if this is None (which is the default) the read values
            will be cast into floats.
        delimit -- Delimiting binary character (default b',').
        comment -- Comment-starting binary character or ``None`` (default). 
            Any character starting from this one until the line end will be ignored.
        skip_init_space -- Whether spaces starting a field will be ignored (default True).

    See Also:
        :func:`dagpype.csv_split`
        :func:`dagpype.stream_lines`
        :func:`dagpype.np.chunk_stream_vals`

    Examples:

    >>> # Find the correlation between two named columns.
    >>> stream_vals('meteo.csv', (b'wind', b'rain')) | corr()
    -0.005981379045088809
    >>> # Find the correlation between two indexed columns.
    >>> stream_vals('neat_data.csv', (0, 3)) | corr()
    -0.0840752963937695
    """

    @sources
    def _dagpype_internal_fn_act():
        stream_ = open(stream, 'rb') if isinstance(stream, str) else stream

        for t in _csv_utils.read(stream_, cols, types_, delimit, comment, skip_init_space):
            yield t

        if isinstance(stream, str):
            stream_.close()

    return _dagpype_internal_fn_act


__all__ += ['parse_xml']
def parse_xml(stream, events = ('end',)):
    """
    Parses XML. Yields a sequence of (event, elem) pairs, where event
        is the event for yielding the element (e.g., 'end' for tag end),
        and elem is a xml.etree.ElementTree element whose tag and text can be
        obtained through elem.tag and elem.text, respectively.

    Arguments:
        stream -- Either a stream, e.g., as returned by open(), or a name of a file.    

    Keyword Arguments:
        events -- Tuple of xml.etree.ElementTree events (default ('end',))

    See the online documentation for an example.
    """

    @sources        
    def _dagpype_internal_fn_act():
        if isinstance(stream, str):
            reader = open(stream, 'rb')
        else: 
            reader = stream

        for event, elem in _element_tree.iterparse(reader, events):
            yield (event, elem)
            elem.clear()

        if isinstance(stream, str):
            reader.close()

    return _dagpype_internal_fn_act


__all__ += ['os_walk']
def os_walk(directory = '.'):
    """
    Recursively iterate through files.

    Keyword Arguments:
    directory -- Directory to perform the search (default '.')

    See Also:
        :func:`dagpype.filename_filt`

    Example:

    >>> # Creates a list of files in the current directory.
    >>> l = os_walk() | to_list()
    """

    @sources
    def os_walk():
        for root, dirs, files in os.walk(directory):
            for basename in files:
                f_name = os.path.join(root, basename)
                yield f_name
    return os_walk




