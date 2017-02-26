"""
Filter operations.
"""


import itertools
import random
import os
import os.path
import fnmatch
import collections
import sys
import types
import math

try:
    from ._core import filters
except ValueError:
    from _core import filters
import _rank_treap
import _csv_utils
import dagpype_c

# pylint: disable-msg=C0103


__all__ = []


__all__ += ['filt']
def filt(trans = None, pre = None, post = None):
    """
    Filter (transform elements and / or suppress them).

    Keyword Arguments:
    trans -- Transformation function for each element (default None).
    pre -- Suppression function checked against each element before
        transformation function, if any (default None).
    post -- Suppression function checked against each element after
        transformation function, if any (default None).

    See Also:
        :func:`dagpype.from_`
        :func:`dagpype.to`
        :func:`dagpype.from_to`
        :func:`dagpype.skip`
        :func:`dagpype.nth`
        :func:`dagpype.slice_`
        :func:`dagpype.tail`
        :func:`dagpype.sink`
        :func:`dagpype.grep`

    Example:

    >>> # square-root of non-negative elements
    >>> source([-1, 4, -3, 16]) | filt(trans = lambda x : math.sqrt(x), pre = lambda x : x >= 0) | to_list()
    [2.0, 4.0]
    """

    @filters
    def _dagpype_internal_fn_act(target):
        try:
            if pre is None and trans is None and post is None:
                while True:
                    target.send((yield))
            elif pre is None and trans is None and post is not None:
                while True:
                    e = (yield)
                    if post(e):
                        target.send(e)
            elif pre is None and trans is not None and post is None:
                while True:
                    target.send(trans((yield)))
            elif pre is None and trans is not None and post is not None:
                while True:
                    e = trans((yield))
                    if pos(e):
                        target.send(e)     
            elif pre is not None and trans is None and post is None:
                while True:
                    e = (yield)
                    if pre(e):
                        target.send(e)
            elif pre is not None and trans is None and post is not None:
                while True:
                    e = (yield)
                    if pre(e) and post(e):
                        target.send(e)
            elif pre is not None and trans is not None and post is None:
                while True:
                    e = (yield)
                    if pre(e):
                        target.send(trans(e))
            elif pre is None and trans is not None and post is not None:
                while True:
                    e = (yield)
                    if not pre(e):
                        continue
                    e = trans(e)
                    if pos(e):
                        target.send(e)     
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['grep']
def grep(what):
    """
    Filters strings based on the occurrence of a substring or a regular expression.

    Arguments:
        what -- Either a string or a compiled regular expression.

    See Also:
        :func:`dagpype.filt`

    Examples:

    >>> source([b'aa', b'aab', b'b']) | grep(b'b') | to_list()
    ['aab', 'b']

    >>> source(['aa', 'aab', 'b']) | grep(re.compile(r'(a+)b')) | to_list()
    ['aab']
    """

    return filt(pre = lambda s: s.find(what) != -1 if isinstance(what, bytes) else what.search(s))


__all__ += ['select_inds']
def select_inds(inds):
    """
    Returns a selection of the selected indices of indexable elements.

    Arguments:
    inds -- either an integer, or an iterable of integers.

    If inds is an integer, this filter will pass on a single element for    
        each element passed through it. Otherwise, it will pass a tuple.

    Examples:

    >>> source([(1, 2, 3), (4, 5, 6)]) | select_inds(2) | to_list()
    [3, 6]

    >>> source([(1, 2, 3), (4, 5, 6)]) | select_inds((0, 2)) | to_list()
    [(1, 3), (4, 6)]

    >>> source([(1, 2, 3), (4, 5, 6)]) | select_inds(()) | to_list()
    [(), ()]
    """

    if type(inds) == int:
        @filters
        def _dagpype_internal_fn_act_i(target):
            try:
                while True:
                    target.send((yield)[inds])                
            except GeneratorExit:
                target.close()

        return _dagpype_internal_fn_act_i

    inds = list(inds)

    if len(inds) == 2:
        @filters
        def _dagpype_internal_fn_act_2(target):
            i0, i1 = inds[0], inds[1]
            try:
                while True:
                    e = (yield)
                    target.send( (e[i0], e[i1]) )                
            except GeneratorExit:
                target.close()

        return _dagpype_internal_fn_act_2

    if len(inds) == 3:
        @filters
        def _dagpype_internal_fn_act_3(target):
            i0, i1, i2 = inds[0], inds[1], inds[2]
            try:
                while True:
                    e = (yield)
                    target.send( (e[i0], e[i1], e[i2]) )                
            except GeneratorExit:
                target.close()

        return _dagpype_internal_fn_act_3

    @filters
    def _dagpype_internal_fn_act(target):
            try:
                while True:
                    e = (yield)
                    target.send( tuple(e[i] for i in inds) )
            except GeneratorExit:
                target.close()

    return _dagpype_internal_fn_act


__all__ += ['relay']
def relay():
    """
    Sends on whatever is passed to it.

    Example:

    >>> # Find the rain auto-correlation relative to the signal 5 time units in the future.
    >>> stream_vals(open('meteo.csv'), 'rain') | relay() + skip(5) | corr()
    1.0
    """

    @filters
    def _dagpype_internal_fn_act(target):
        try:
            while True:
                target.send((yield))
        except GeneratorExit:
            target.close();

    return _dagpype_internal_fn_act


__all__ += ['window_simple_ave']
def window_simple_ave(wnd_len):
    """
    Transforms a sequence into a simple moving average of its values
        within some window.

    If the input sequence is x[0], x[1], ..., then the output sequence is        
        {{{
        y[i] = (x[max(0, i - len)] + ... + x[i]) / min(i + 1, wnd_len)
        }}}

    Arguments:
        wnd_len -- Averaging window length.

    See Also:
        :func:`dagpype.cum_ave`
        :func:`dagpype.exp_ave`        
        
    Examples:

    >>> source([1., 2., 3., 4.]) | window_simple_ave(2) | to_list()
    [1.0, 1.5, 2.5, 3.5]
    """

    @filters
    def _dagpype_internal_fn_act(target):
        assert wnd_len > 0
        vals, i, sum_ = [0] * wnd_len, 0, 0
        try:
            while i < wnd_len:
                vals[i] = (yield)
                sum_ += vals[i]
                target.send(sum_ / float(i + 1))
                i += 1
            w_ = float(wnd_len)
            while True:
                if i == wnd_len:
                    i = 0
                sum_ -= vals[i]
                vals[i] = (yield)
                sum_ += vals[i]
                target.send(sum_ / w_)
                i += 1
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['cum_ave']
def cum_ave():
    """
    Transforms a sequence into a cumulative average of it.

    If the input sequence is x[0], x[1], ..., then the output sequence is        
        {{{
        y[i] = (x[0] + ... + x[i]) / (i + 1)
        }}}

    See Also:
        :func:`dagpype.cum_sum`
        :func:`dagpype.window_simple_ave`
        :func:`dagpype.exp_ave`        
        :func:`dagpype.np.cum_ave`

    Examples:

    >>> source([1., 2., 3., 4.]) | cum_ave() | to_list()
    [1.0, 1.5, 2.0, 2.5]
    """

    @filters
    def _dagpype_internal_fn_act(target):
        y, i = (yield), 1
        target.send(y)
        try:
            while True:
                y += ((yield) - y) / float(i + 1)
                target.send(y)
                i += 1
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['exp_ave']
def exp_ave(alpha):
    """
    Transforms a sequence into an exponential moving average of it.

    If the input sequence is x[0], x[1], ..., then the output sequence is
        {{{
        y[0] = x[0]
        y[i] = alpha * x[i] + (1 - alpha) * y[i - 1]
        }}}
        
    All but an epsilon of relevant weight is stored at each point in the last
        log(epsilon) / log(1 - alpha) time units.

    Arguments:
    alpha -- Responsiveness factor, should be between 0 and 1.

    See Also:
        :func:`dagpype.window_simple_ave`
        :func:`dagpype.cum_ave`    
        :func:`dagpype.np.exp_ave`

    Example:

    >>> source([1., 2., 3., 4.]) | exp_ave(0.75) | to_list()
    [1.0, 1.75, 2.6875, 3.671875]
    """

    @filters
    def _dagpype_internal_fn_act(target):
        assert 0 <= alpha <= 1
        y = (yield)
        target.send(y)
        alpha_tag = 1 - alpha
        try:
            while True:
                y = alpha * (yield) + alpha_tag * y
                target.send(y)
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


def _window_min_max_imp(wnd_len, lt):
    @filters
    def _dagpype_internal_fn_act(target):
        _Pair = collections.namedtuple('_Pair', ['val', 'death'], verbose = False)
        ring, end, last, min_pair = [None] * wnd_len, wnd_len, 0, 0
        ring[0] = _Pair((yield), wnd_len)
        target.send(ring[0].val)
        i = 1
        try:
            while True:
                if ring[min_pair].death == i:
                    min_pair += 1
                    if min_pair >= end:
                        min_pair = 0
                e = (yield)
                if not lt(ring[min_pair].val, e):
                    ring[min_pair] = _Pair(e, i + wnd_len)
                    last = min_pair
                else:
                    while not lt(ring[last].val, e):
                        if last == 0:
                            last = end
                        last -= 1
                    last += 1
                    if last == end:
                        last = 0
                    ring[last] = _Pair(e, i + wnd_len)
                target.send(ring[min_pair].val)
                i += 1
        except GeneratorExit:
            target.close()
            
    return _dagpype_internal_fn_act        
    
    
__all__ += ['window_min']
def window_min(wnd_len, lt = lambda x, y: x < y):
    """
    Transforms a sequence into its minimum within some window.
    Uses an algorithm from http://home.tiac.net/~cri/2001/slidingmin.html

    If the input sequence is x[0], x[1], ..., then the output sequence is        
        {{{
        y[i] = min(x[i], x[i - 1], ..., x[max(0, i - wnd_len)])
        }}}

    Arguments:
    wnd_len -- Averaging window length.
    
    Keyword Arguments:
    lt -- Comparison function (default: lambda x, y: x  < y) used for deciding which is smaller than which.

    See Also:
        :func:`dagpype.window_max`
        
    Examples:

    >>> source([1, 2, 3, 4, 1, 0, 4, 4]) | window_min(2) | to_list()
    [1, 1, 2, 3, 1, 0, 0, 4]
    """    

    return _window_min_max_imp(wnd_len, lt)


__all__ += ['window_max']
def window_max(wnd_len, lt = lambda x, y: x < y):
    """
    See Also:
        :func:`dagpype.window_min`

    Examples:

    >>> source([1, 2, 3, 4, 1, 0, 4, 4]) | window_max(2) | to_list()
    [1, 2, 3, 4, 4, 1, 4, 4]
    """    

    return _window_min_max_imp(wnd_len, lambda x, y: not lt(x, y))


__all__ += ['window_quantile']
def window_quantile(wnd_len, quantile = 0.5, lt = lambda x, y: x < y):
    """
    Transforms a sequence into its quantiles within some window.

    If the input sequence is x[0], x[1], ..., then the output sequence is        
        {{{
        y[i] = q_{quantile}(x[i], x[i - 1], ..., x[max(0, i - wnd_len)])
        }}}
    where q_{p}(A) is the smallest element larger than a p-th of A's elements (e.g., 0.5 is the
        median).

    Arguments:
        wnd_len -- Window length.
    
    Keyword Arguments:
        quantile -- Quantile fraction; should be between 0 and 1 (default 0.5, which is the median).
        lt -- Comparison function (default: lambda x, y: x < y) used for deciding which is smaller than which.
        
    Examples:

    >>> source([1, 4, 2, 4, 6, 9, 2, 4, 5]) | window_quantile(2, 0.5) | to_list()
    [1, 4, 4, 4, 6, 9, 9, 4, 5]
    >>> source([1, 4, 2, 4, 6, 9, 2, 4, 5]) | window_quantile(3, 0.5) | to_list()
    [1, 4, 2, 4, 4, 6, 6, 4, 4]
    """    

    @filters
    def _dagpype_internal_fn_act(target):
        assert wnd_len > 0
        assert 0 <= quantile <= 1
        es, tr = [], _rank_treap.Treap(lt)
        try:
            while True:
                es.append(tr.insert((yield)))
                k = int(quantile * len(es))
                target.send(tr.kth(k))            
                if len(es) == wnd_len:
                    break
            i = 0
            while True:
                tr.erase(es[i])
                es[i] = tr.insert((yield))
                i = (i + 1) % wnd_len                
                target.send(tr.kth(k))            
        except GeneratorExit:
            target.close()
            
    return _dagpype_internal_fn_act        


__all__ += ['cast']
def cast(types_):
    """
    Returns a cast of elements.

    Arguments:
        types_ -- either an type, or a tuple of types. This corresponds to whether
            each element is a single item or a tuple of items.
            each element passed through it. Otherwise, it will pass a tuple.

    Examples:

    >>> source(['1']) | cast(float) | to_list()
    [1.0]

    >>> source([('1', '2')]) | cast((int, float)) | to_list()
    [(1, 2.0)]
    """

    if type(types_) == type:
        @filters
        def _dagpype_internal_fn_act_1(target):
            try:
                while True:
                    target.send(types_((yield)))
            except GeneratorExit:
                target.close()

        return _dagpype_internal_fn_act_1

    types_ = list(types_)

    if len(types_) == 2:
        @filters
        def _dagpype_internal_fn_act_2(target):
            t0, t1 = types_[0], types_[1]
            try:
                while True:
                    e = (yield)
                    target.send( (t0(e[0]), t1(e[1])) )                
            except GeneratorExit:
                target.close()

        return _dagpype_internal_fn_act_2

    if len(types_) == 3:
        @filters
        def _dagpype_internal_fn_act_3(target):
            t0, t1, t2 = types_[0], types_[1], types_[2]
            try:
                while True:
                    e = (yield)
                    target.send( (t0(e[0]), t1(e[1]), t2(e[2])) )                
            except GeneratorExit:
                target.close()

        return _dagpype_internal_fn_act_3

    @filters
    def _dagpype_internal_fn_act(target):
        try:
            while True:
                e = (yield)
                target.send( tuple(t(ee) for t, ee in zip(types_, e)) )
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['prepend']
def prepend(what):
    """
    Prepends to the start of all elements.

    Arguments:
        e -- What to prepend.

    See Also:
        :func:`dagpype.append`

    Example:

    >>> source([1, 2, 3, 4]) | prepend(0) | to_list()
    [0, 1, 2, 3, 4]
    """

    @filters
    def _dagpype_internal_fn_act(target):
        target.send(what)
        try:
            while True:
                target.send((yield))
        except GeneratorExit:
            target.close()
    return _dagpype_internal_fn_act

    
__all__ += ['append']
def append(e):
    """
    Appends to the end of all elements.

    Arguments:
        e -- What to append.

    See Also:
        :func:`dagpype.prepend`

    Example:

    >>> source([1, 2, 3, 4]) | append(5) | to_list()
    [1, 2, 3, 4, 5]
    """

    @filters
    def _dagpype_internal_fn_act(target):
        try:
            while True:
                target.send((yield))
        except GeneratorExit:
            target.send(e)
            target.close()
    return _dagpype_internal_fn_act


__all__ += ['filename_filt']
def filename_filt(pattern, skip_files = False, skip_dirs = True):
    """
    Filters filenames - checks if they pass some criteria.

    Arguments:
        pattern -- Glob type of pattern.

    Keyword Arguments:
        skip_files -- Whether to skip regular files (default False)
        skip_dirs -- Whether to skip directories.

    See Also:
        :func:`dagpype.os_walk`

    Example:

    >>> # Counts the number of files of the form 'data?.csv'
    >>> print(os_walk() | filename_filt('data?.csv') | count())
    0
    """

    def _matches(f_name):
        if skip_files and os.path.isfile(f_name):
            return False
        if skip_dirs and os.path.isdir(f_name):
            return False
        if pattern is not None and not fnmatch.fnmatch(f_name, pattern):
            return False
        return True
    return filt(pre = lambda f_name : _matches(f_name))


__all__ += ['prob_rand_sample']
def prob_rand_sample(prob):
    """
    Randomly passes some of the elements, with a given probability.

    Arguments:
        prob -- Probability an element will pass.

    See Also:
        :func:`dagpype.size_rand_sample`

    Example:

    >>> n = 99999
    >>> assert 0.5 <= (source(range(n)) | prob_rand_sample(0.7) | count()) / float(n) <= 1
    """

    assert 0 <= prob <= 1
    return filt(pre = lambda _ : random.random() < prob)


__all__ += ['skip']
def skip(n):
    """
    Skips n elements.

    Arguments:
    n - If a positive integer, skips n elements from start, else
        skips n element from the end

    See Also:
        :func:`dagpype.nth`
        :func:`dagpype.np.skip`

    Example:

    >>> source([1, 2, 3, 4]) | skip(2) | to_list()
    [3, 4]

    >>> source([1, 2, 3, 4]) | skip(-2) | to_list()
    [1, 2]
    """

    if n >= 0:
        @filters
        def _dagpype_internal_fn_act_p(target):
            i = 0
            try:
                while True:
                    e = (yield)
                    if i >= n:
                        target.send(e)
                    i += 1
            except GeneratorExit:
                target.close()

        return _dagpype_internal_fn_act_p

    @filters
    def _dagpype_internal_fn_act_n(target):
        m = -n + 1
        q = collections.deque([], m)
        try:
            while True:
                if len(q) == m:
                    target.send(q.popleft())
                q.append((yield))
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act_n


__all__ += ['trace']
def trace(stream = sys.stdout, enum = True, format_ = lambda e : str(e)):
    """
    Traces elements to a stream. Useful for debugging problematic streams.

    Keyword Arguments:
        stream -- Stream to which to trace (default sys.stdout)
        enum -- Whether to enumerate each element by its order (default True)
        format_ -- Format function for elements (default lambda e : str(e))

    Example:

    >>> source([1, 2, 3, 'd']) | trace() | sum_()
    0 : 1
    1 : 2
    2 : 3
    3 : d
    Traceback (most recent call last):
      ...
    TypeError: unsupported operand type(s) for +=: 'int' and 'str'
    """

    @filters
    def _dagpype_internal_fn_act(target):
        try:
            i = 0
            while True:
                e = (yield)
                s = (str(i) + ' : ') if enum else ''
                s += format_(e) + '\n'
                stream.write(s)
                stream.flush()
                i += 1
                target.send(e)
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act
    
    
__all__ += ['split']
def split(delimit = ','):
    """
    Splits a stream of strings to a stream of tuples resulting from the strings
        being split by a delimiter.
        
    Keyword Arguments:
        delimit -- Delimiting character (default ',')

    See Also:
        :func:`dagpype.csv_split`
        
    Example:

    >>> source(['a,b', 'c,d,e']) | split() | to_list()
    [('a', 'b'), ('c', 'd', 'e')]
    """
    
    return filt(lambda l : tuple(l.split(delimit)))
    # Tmp Ami - add to unit test, add optional types


__all__ += ['csv_split']
def csv_split(
    cols = None, 
    types_ = None, 
    delimit = b',', 
    comment = None,
    skip_init_space = True):

    """
    Splits the values in a delimited stream (e.g., by commas for CSV files, or by tabs for TAB files) as tuples.

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
        :func:`dagpype.split`
        :func:`dagpype.stream_vals`

    Examples:

    >>> # Assume the file 'junky.txt' contains lines, those containing the string
    >>> # 'moshe' are split by tabs, and we wish to find the correlation between the
    >>> #  3nd and 6th values in these lines.
    >>> stream_lines('junky.txt') | grep(b'moshe') | csv_split((2, 5), delimit = b';') | corr()
    0.4472135954999579
    """

    types__ = types_
    @filters
    def _dagpype_internal_fn_act(target):
        try:     
            e = (0,) if cols is None or _csv_utils.cols_are_type(cols, int) else (yield) 
            (cols_, single, inds, uniques, copies, max_ind, types_, c_types, cast_back) = \
                _csv_utils._csv_attribs((e, ), cols, types__, delimit, comment, skip_init_space)
            r = dagpype_c.ColReader(
                [], 
                delimit, comment, 1 if skip_init_space else 0, 
                1 if single else 0,
                inds, uniques, copies, max_ind,
                c_types)
            while True:
                e = r.parse_string((yield))
                if not cast_back:
                    target.send(e)
                elif single:
                    target.send( _csv_utils._cast(e, types_[0]) )
                else:
                    target.send( tuple(_csv_utils._cast(a, b) for a, b in itertools.izip_longest(e, types_)) )
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['cum_sum']
def cum_sum():
    """
    Transforms a sequence into a cumulative sum of it.

    If the input sequence is x[0], x[1], ..., then the output sequence is        
        {{{
        y[i] = x[0] + ... + x[i]
        }}}

    See Also:
        :func:`dagpype.cum_ave`
        :func:`dagpype.np.cum_sum`

    Examples:

    >>> source([1., 2., 3., 4.]) | cum_sum() | to_list()
    [1.0, 3.0, 6.0, 10.0]
    """

    @filters
    def _dagpype_internal_fn_act(target):
        y = (yield)
        target.send(y)
        try:
            while True:
                y += (yield)
                target.send(y)
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['from_']
def from_(cond, inclusive = True):
    """
    Stream elements starting from one that fits some condition.
   
    Arguments:
        cond -- Either a function or some other object. In the first case, the
            function will be applied to each element; in the second case, the object
            will be compared (using ==) with each element.
                       
    Keyword Arguments:
        inclusive -- Whether the element first matching the criteria is streamed
            (default True)

    See Also:
        :func:`dagpype.filt`
        :func:`dagpype.to`
        :func:`dagpype.from_to`
        :func:`dagpype.skip`
        :func:`dagpype.nth`
        :func:`dagpype.slice_`
        :func:`dagpype.tail`

    Examples:
   
    >>> source([1, 2, 3, 4, 3, 2, 1]) | from_(2) | to_list()
    [2, 3, 4, 3, 2, 1]
   
    >>> source([1, 2, 3, 4, 3, 2, 1]) | from_(2, False) | to_list()
    [3, 4, 3, 2, 1]

    >>> source([1, 2, 3, 4, 3, 2, 1]) | from_(lambda d: d % 3 == 0) | to_list()
    [3, 4, 3, 2, 1]
    """

    @filters
    def _dagpype_internal_fn_act(target):
        try:
            if isinstance(cond, types.FunctionType):       
                while True:
                    e = (yield)
                    if cond(e):
                        break
            else:
                while True:
                    e = (yield)
                    if e == cond:
                        break
            if inclusive:
                target.send(e)
            while True:
                target.send((yield))
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['to']
def to(cond, inclusive = True):
    """
    Stream elements until the one that fits some condition.
   
    Arguments:
        cond -- Either a function or some other object. In the first case, the
            function will be applied to each element; in the second case, the object
            will be compared (using ==) with each element.
                       
    Keyword Arguments:
        inclusive -- Whether the element first matching the criteria is streamed
            (default True)

    See Also:
        :func:`dagpype.filt`
        :func:`dagpype.from_`
        :func:`dagpype.from_to`
        :func:`dagpype.skip`
        :func:`dagpype.nth`
        :func:`dagpype.slice_`
        :func:`dagpype.tail`

    Examples:
   
    >>> source([1, 2, 3, 4, 3, 2, 1]) | to(2) | to_list()
    [1, 2]
   
    >>> source([1, 2, 3, 4, 3, 2, 1]) | to(2, False) | to_list()
    [1]

    >>> source([1, 2, 3, 4, 3, 2, 1]) | to(lambda d: d % 3 == 0) | to_list()
    [1, 2, 3]
    """

    @filters
    def _dagpype_internal_fn_act(target):
        try:
            if isinstance(cond, types.FunctionType):       
                while True:
                    e = (yield)
                    if cond(e):
                        break
                    target.send(e)
            else:
                while True:
                    e = (yield)
                    if e == cond:
                        break
                    target.send(e)
            if inclusive:
                target.send(e)
            target.close()
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


def _from_to_strict(from_cond, to_cond, from_inclusive, to_inclusive):
    @filters
    def _dagpype_internal_fn_act(target):
        try:
            while True:
                send = []
               
                if isinstance(from_cond, types.FunctionType):       
                    while True:
                        e = (yield)
                        if from_cond(e):
                            break
                else:
                    while True:
                        e = (yield)
                        if e == from_cond:
                            break
                if from_inclusive:
                    send.append(e)
                   
                if isinstance(to_cond, types.FunctionType):       
                    while True:
                        e = (yield)
                        if to_cond(e):
                            break
                        send.append(e)

                else:
                    while True:
                        e = (yield)
                        if e == to_cond:
                            break
                        send.append(e)
                if to_inclusive:
                    send.append(e)
                   
                for e in send:
                    target.send(e)

        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


def _from_to_nonstrict(from_cond, to_cond, from_inclusive, to_inclusive):
    @filters
    def _dagpype_internal_fn_act(target):
        try:
            while True:
                if isinstance(from_cond, types.FunctionType):       
                    while True:
                        e = (yield)
                        if from_cond(e):
                            break
                else:
                    while True:
                        e = (yield)
                        if e == from_cond:
                            break
                if from_inclusive:
                    target.send(e)
                   
                if isinstance(to_cond, types.FunctionType):       
                    while True:
                        e = (yield)
                        if to_cond(e):
                            break
                        target.send(e)
                else:
                    while True:
                        e = (yield)
                        if e == to_cond:
                            break
                        target.send(e)
                if to_inclusive:
                    target.send(e)

        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['from_to']
def from_to(from_cond, to_cond, from_inclusive = True, to_inclusive = True, strict = False):

    """
    Stream elements each time they are between one that fits a condition and up to some 
        other one that fits some condition.
   
    Arguments:
        from_cond -- Either a function or some other object. In the first case, the
            function will be applied to each element; in the second case, the object
            will be compared (using ==) with each element.                       
        to_cond -- Either a function or some other object. In the first case, the
            function will be applied to each element; in the second case, the object
            will be compared (using ==) with each element.                       

    Keyword Arguments:
        from_inclusive -- Whether the element first matching the criteria is streamed
            (default True)
        to_inclusive -- Whether the element first matching the criteria is streamed
            (default True)
        strict -- Whether 
        
        
    See Also:
        :func:`dagpype.filt`
        :func:`dagpype.from_`
        :func:`dagpype.to`
        :func:`dagpype.skip`
        :func:`dagpype.nth`
        :func:`dagpype.slice_`
        :func:`dagpype.tail`

    Examples:
   
    >>> source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(2, 3) | to_list()
    [2, 3, 2, 1, 3, 2]

    >>> source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(2, 3, from_inclusive = False) | to_list()
    [3, 1, 3]

    >>> source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(2, 3, to_inclusive = False) | to_list()
    [2, 2, 1, 2]

    >>> source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(2, 3, from_inclusive = False, to_inclusive = False) | to_list()
    [1]

    >>> source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(2, 3, strict = True) | to_list()
    [2, 3, 2, 1, 3]

    >>> source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(2, 3, from_inclusive = False, strict = True) | to_list()
    [3, 1, 3]

    >>> source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(2, 3, to_inclusive = False, strict = True) | to_list()
    [2, 2, 1]

    >>> source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(2, 3, from_inclusive = False, to_inclusive = False, strict = True) | to_list()
    [1]

    >>> source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(lambda d: d % 2 == 0, lambda d: d % 4 == 0) | to_list()
    [2, 3, 4, 2, 1, 3, 7, 2]

    >>> source([1, 2, 3, 4, 3, 2, 1, 3, 7, 2]) | from_to(lambda d: d % 2 == 0, lambda d: d % 4 == 0, strict = True) | to_list()
    [2, 3, 4]
    """

    return _from_to_strict(from_cond, to_cond, from_inclusive, to_inclusive) if strict else \
        _from_to_nonstrict(from_cond, to_cond, from_inclusive, to_inclusive)


__all__ += ['slice_']
def slice_(
    start = None, stop = None, step = None):

    """
    Similar to itertools.islice.

    See Also:
        :func:`dagpype.from_`
        :func:`dagpype.to`
        :func:`dagpype.from_to`
        :func:`dagpype.nth`
        :func:`dagpype.skip`  
        :func:`dagpype.tail`

    Examples:

    >>> source(range(100)) | slice_(10) | to_list()
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

    >>> source(range(100)) | slice_(0, 100, 10) | to_list()
    [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]

    >>> source(range(100)) | slice_(0, 10) | to_list()
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    """
    
    assert start is not None or stop is not None or step is not None

    if stop is None and step is None:
        start, stop = None, start

    @filters
    def _dagpype_internal_fn_act(target):
        if stop is not None:
            assert stop >= 0
        
        try:
            i = 0    

            if start is None and step is None:
                while True:
                    if i == stop:
                        break
                    target.send((yield))
                    i += 1
            elif start is not None and stop is not None and step is not None:
                assert start >= 0            
                assert step >= 0
            
                while True:
                    if i == stop:
                        break
                    e  = (yield)
                    if i >= start and (i - start) % step == 0:      
                        target.send(e)
                    i += 1
            elif stop is None and step is not None:
                start_ = start if start is not None else 0
                assert start_ >= 0            
                assert step >= 0
            
                while True:
                    e  = (yield)
                    if i >= start_ and (i - start_) % step == 0:      
                        target.send(e)
                    i += 1
            else:
                assert start is not None
                assert start >= 0
                
                while True:
                    if i == stop:
                        break
                    e  = (yield)
                    target.send(e)
                    i += 1
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act
	

__all__ += ['tail']
def tail(num):

    """
    Takes the tail of a stream.

    Arguments:
        num -- How many elements from the tail to take.

    See Also:
        :func:`dagpype.from_`
        :func:`dagpype.to`
        :func:`dagpype.from_to`
        :func:`dagpype.skip`
        :func:`dagpype.nth`
        :func:`dagpype.slice_`
        
    Examples:
   
    >>> source(range(10)) | tail(4) | to_list()
    [6, 7, 8, 9]

    >>> source(range(10)) | tail(0) | to_list()
    []

    >>> source(range(2)) | tail(4) | to_list()
    [0, 1]
    """
   
    assert num >= 0

    @filters
    def _dagpype_internal_fn_act(target):
        try:
            i, es = 0, []
           
            while len(es) < num:
                es.append((yield))
            if len(es) == 0:
                target.close()
                return
               
            while True:
                es[i] = (yield)
                i += 1
                if i == len(es):
                    i = 0
        except GeneratorExit:           
            for _ in es:
                target.send(es[i])
                i += 1
                if i == len(es):
                    i = 0
            target.close()               

    return _dagpype_internal_fn_act


__all__ += ['enumerate_']
def enumerate_(start = 0):

    """    
    Enumerates a stream. Transforms it into a stream of pairs, where the first of each
        is a running index.

    Arguments:
        start -- Starting value of running index (default 0).
        
    See Also:
        :func:`dagpype.np.enumerate_`
        
    Examples:
   
    >>> source(['a', 'b', 'c', 'd']) | enumerate_() | to_list()
    [(0, 'a'), (1, 'b'), (2, 'c'), (3, 'd')]
    """
   
    @filters
    def _dagpype_internal_fn_act(target):
        e = dagpype_c.Enumerator(start)
        try:
            while True:
                target.send(e.next((yield)))
        except GeneratorExit:           
            target.close()               

    return _dagpype_internal_fn_act

