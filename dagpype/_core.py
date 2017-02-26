import types
import itertools
import collections
import warnings


__all__ = []
    

class Error(Exception):
    """
    Base class for data-pipe errors.
    """

    def __init__(self, msg):
        Exception.__init__(self, msg)
__all__ += ['Error']


class NoResultError(Error):
    """
    Indicates a pipeline terminated with no result.
    """

    def __init__(self):
        Error.__init__(self, 'no result')
__all__ += ['NoResultError']


class InvalidParamError(Error, ValueError):
    """
    Invalid parameter passed.
    """

    def __init__(self, param, value, msg):
        Error.__init__(self, msg)
        self._param, self._value = param, value

    def param(self):
        """
        Returns offending parameter name.
        """

        return self._param    

    def value(self):
        """
        Returns offending parameter value.
        """

        return self._value
__all__ += ['InvalidParamError']


class _Piped(object):
    @staticmethod
    def assert_valid_fn_list(fns):
        assert isinstance(fns, list)
        for fn_ in fns:
            if isinstance(fn_, tuple):
                _Piped.assert_valid_fn_tuple(fn_)
                continue
            assert isinstance(fn_, types.FunctionType)

    @staticmethod
    def assert_valid_fn_tuple(fns):
        assert isinstance(fns, tuple)
        for fn_ in fns:
            if isinstance(fn_, list):
                _Piped.assert_valid_fn_list(fn_)
                continue
            assert isinstance(fn_, types.FunctionType)


class _SimplePiped(_Piped):
    def __init__(self, fns):
        self._fns = fns
        _Piped.assert_valid_fn_list(self._fns)
        _Piped.__init__(self)                
        
    def simple(self):
        return self._fns

    def fanned(self):
        return (self._fns,)


class _SrcPiped(_SimplePiped):
    def __init__(self, fns):
        _SimplePiped.__init__(self, fns)    

    def __or__(self, other):
        return other.connect_src(self)

    def __add__(self, other):
        return _SrcFannedPiped(self.fanned() + other.fanned())


__all__ += ['source']
def source(iterable):
    """
    Creates a source from any iterable sequence.

    Arguments:
        iterable -- Iterable sequence whose values will be sent on.
        
    See Also:
        :func:`dagpype.np.chunk_source`

    Examples:

    >>> source([1, 2, 3, 4]) | count()
    4

    >>> source(()) | count()
    0
    """
    def act(target):
        try:
            for e in iterable:
                (yield)
                target.send(e) 
        except GeneratorExit:
            target.close()    

    return _SrcPiped([act])


__all__ += ['sources']
def sources(fn):
    """
    Decorator signifying a (generator) function is a source function.

    Arguments:
        fn -- Decorated function.

    Example:

    >>> # Function returning 10 '1's (there are simpler ways of doing this):
    >>> def ten_ones():
    ...     @sources
    ...     def _act():
    ...         for i in range(10):
    ...             yield '1'
    ...     return _act
    """
    return source(fn())


class _MidPiped(_SimplePiped):
    def __init__(self, fns):
        _SimplePiped.__init__(self, fns)
        
    def __or__(self, other):
        return other.connect_mid(self)

    def connect_src(self, prev):
        return _SrcPiped(prev._fns + self._fns)

    def connect_mid(self, prev):
        return _MidPiped(prev._fns + self._fns)

    def __add__(self, other):
        return _MidFannedPiped(self.fanned() + other.fanned())


__all__ += ['filters']
def filters(fn):
    """
    Decorator signifying a (generator) function is a filter function.

    Arguments:
        fn -- Decorated function.

    Example:

    >>> # Function adding 1 to anything (there are simpler ways of doing this):
    >>> def add_1():
    ...     @filters
    ...     def _act(target):
    ...         try:
    ...             while True:
    ...                 target.send((yield) + 1)
    ...         except GeneratorExit:
    ...             target.close()
    ...     return _act    
    """
    return _MidPiped([fn])


class _Chainer(object):
    def __init__(self, fns, gen):
        self.gen = self._connect_all(fns, gen)
            
    def _connect_all(self, fns, gen):
        for what in reversed(fns):
            assert isinstance(gen, types.GeneratorType)
            if isinstance(what, types.FunctionType):
                gen = what(gen)
                if gen is None:
                    break
                try:
                    next(gen)
                except StopIteration:
                    pass
                continue
            assert isinstance(what, tuple)
            gens = self._connect_join(gen, len(what))
            gens = [_Chainer(fn, gen).gen for fn, gen in zip(what, gens)]
            gen = self._connect_split(gens)
            if gen is None:
                break
        return gen

    def _connect_join(self, g, size):    
        def join(target):
            payloads = [collections.deque() for i in range(size)]
            closed = [False] * size
            try:
                while True:
                    e = (yield)
                    i, active = e[0], e[1]
                    if not active:
                        closed[i] = True
                        if True not in closed:
                            target.close()
                            return
                        continue
                    payload_data = e[2]     
                    payloads[i].append(payload_data)
                    if not all(len(payloads[j]) > 0 for j in range(size)):    
                        continue
                    ps = tuple(p.popleft() for p in payloads)
                    target.send(ps)
            except GeneratorExit:
                target.close()

        g = join(g)
        next(g)
        
        def numbered_relay(i):
            def act(target):
                try:
                    while True:
                        e = (yield)
                        target.send((i, True, e))
                except GeneratorExit:
                    target.send((i, False,))
            return act

        relays = [numbered_relay(i) for i in range(size)]
        gens = [r(g) for r in relays]
        for g in gens:
            next(g)
            
        return gens    

    def _connect_split(self, gens):
        assert len(gens) > 0
        if gens[0] is None:
            assert all(g is None for g in gens)
            return None
        assert None not in gens

        def split(targets):
            assert len(targets) > 1
            try:
                while True:
                    e = (yield)
                    for i, t in enumerate(targets):
                        try:
                            if t is not None:
                                t.send(e)
                        except StopIteration:
                            targets[i] = None
                            if all(t is None for t in targets):
                                raise
            except GeneratorExit:
                for t in targets:
                    t.close()

        g = split(gens)
        assert g is not None
        next(g)
        
        return g


class _FinalActor(object):
    def __init__(self):
        self._l = []
        def final_dagpype_internal_fn_act():
            has = False
            try:
                while True:
                    last = (yield)
                    has = True
            except GeneratorExit:
                if not has:
                    raise NoResultError()
                self._l.append(last)
        self.gen = final_dagpype_internal_fn_act()
        next(self.gen)

    def pump(self, gen):
        with warnings.catch_warnings() as w:
            while len(self._l) == 0:
                try:
                    gen.send(True)
                except StopIteration:
                    self.gen.close()
                    if len(self._l) == 0:
                        raise NoResultError()

    def res(self):
        with warnings.catch_warnings() as w:
            if len(self._l) == 0:
                raise NoResultError()
            return self._l[0]


class _SnkPiped(_SimplePiped):        
    def __init__(self, fns):
        _SimplePiped.__init__(self, fns)
        
    def __or__(self, other):
        return other.connect_snk(self)

    def connect_src(self, prev):
        f = _FinalActor()
        gen = _Chainer(prev._fns + self._fns, f.gen).gen
        f.pump(gen)
        return f.res()
        
    def connect_mid(self, prev):
        return _SnkPiped(prev._fns + self._fns)

    def connect_snk(self, prev):
        return _SnkPiped(prev._fns + self._fns)

    def __add__(self, other):
        return _SnkFannedPiped(self.fanned() + other.fanned())
        
    def freeze(self):
        final_dagpype_internal_fn_actor = _FinalActor()
        return _FrozenSnkPiped(
            final_dagpype_internal_fn_actor,
            _Chainer(self._fns, final_dagpype_internal_fn_actor.gen).gen,
            [])


class _FrozenSnkPiped(_Piped):        
    def __init__(self, final_dagpype_internal_fn_actor, connect_gen, fns):
        self._final_dagpype_internal_fn_actor = final_dagpype_internal_fn_actor
        self._connect_gen = connect_gen
        self._fns = fns
       
    def connect_src(self, prev):
        gen = _Chainer(prev._fns + self._fns + [_no_close_relay()], self._connect_gen).gen
        try:    
            while True:
                gen.send(True)
        except StopIteration:
            pass

    def connect_mid(self, prev):
        return _FrozenSnkPiped(
            self._final_dagpype_internal_fn_actor,
            self._connect_gen,
            prev._fns + self._fns)

    def thaw(self):
        self._connect_gen.close()
        return self._final_dagpype_internal_fn_actor.res()


__all__ += ['sinks']
def sinks(fn):
    """
    Decorator signifying a (generator) function is a sink function.

    Arguments:
        fn -- Decorated function.

    Example:

    >>> # Function returning the sum of the first two values sent to it:
    ... def add_1():
    ...     @filters
    ...     def _act(target):
    ...         i, sum = 0, 0
    ...         try:
    ...             while True:
    ...                 if i < 2:       
    ...                     sum += (yield)
    ...                 i += 1
    ...         except GeneratorExit:
    ...             if i >= 2:
    ...                 target.send(sum)
    ...             target.close()
    ...     return _act    
    """
    return _SnkPiped([fn])


class _FannedPiped(_Piped):
    def __init__(self, fan):
        self._fan = fan
        _Piped.assert_valid_fn_tuple(self._fan)    

    def simple(self):
        return [self._fan]

    def fanned(self):
        return self._fan


class _SrcFannedPiped(_FannedPiped):
    def __init__(self, fan):
        _FannedPiped.__init__(self, fan)
        
    def __or__(self, other):
        return _SrcPiped([self._fan]) | other

    def __add__(self, other):
        return _SrcFannedPiped(self.fanned() + other.fanned())
        

class _MidFannedPiped(_FannedPiped):
    def __init__(self, fan):
        _FannedPiped.__init__(self, fan)
        
    def __or__(self, other):
        return _MidPiped([self._fan]) | other

    def __add__(self, other):
        return _MidFannedPiped(self.fanned() + other.fanned())

    def connect_src(self, prev):
        return prev | _MidPiped([self._fan])

    def connect_mid(self, prev):
        return prev | _MidPiped([self._fan])


class _SnkFannedPiped(_FannedPiped):
    def __init__(self, fan):
        _FannedPiped.__init__(self, fan)
        
    def __or__(self, other):
        return other.connect_src(_SnkPiped([self._fan]))

    def __add__(self, other):
        return _SnkFannedPiped(self.fanned() + other.fanned())

    def freeze(self):
        return _SnkPiped([self._fan]).freeze()

    def connect_src(self, prev):
        return prev | _SnkPiped([self._fan])

    def connect_mid(self, prev):
        return _SnkPiped(prev._fns + [self._fan])            
    
    def connect_snk(self, prev):
        return _SnkPiped(prev._fns + [self._fan])


def _no_close_relay():
    def _dagpype_internal_fn_act(target):
        try:
            while True:
                target.send((yield))
        except GeneratorExit:
            pass
    return _dagpype_internal_fn_act


__all__ += ['sub_pipe_target']
def sub_pipe_target(pipe, target):
    """    
    Call, from within an implementation of a filter,
        to dynamically create a sub-target formed by concatenating a pipe
        to the current target.

    Arguments:
        pipe -- Typically a pipe created within the implementation.
        target -- The target provided to the implementation.

    Returns:
        If the pipe is a source pipe - None. Otherwise a subtarget to which
            elements can be passed through send(), closed via close(), etc.

    Example:

    >>> def some_implementation(target):
    ...     pipe = filt(lambda x : 2 * x)
    ...     sub_target = sub_pipe_target(pipe, target)
    ...     try:
    ...         while True:
    ...             sub_target.send((yield))
    ...     except GeneratorExit:
    ...         sub_target.close()
    ...         target.close()                
    """
    g = _no_close_relay()(target)
    next(g)
    g = _Chainer(pipe.simple(), g).gen
    if not isinstance(pipe, _SrcPiped):
        return g
    try:
        while True:
            g.send(True)
    except StopIteration:
        pass        
    return None
    

__all__ += ['freeze']
def freeze(target):
    """
    freeze and thaw are used together to create a "frozen" target, which
        can be connected to pipelines multiple times. Feeding values
        to a frozen target does not result in anything. Only when the target is "thawed",
        a result is returned.

    Examples:

    >>> # Print the smallest value in three files
    >>> a = freeze(min_())
    >>> for f_name in ['data1.txt', 'data2.txt', 'data3.txt']:
    ...     stream_vals(f_name) | cast(float) | a
    >>> print(thaw(a))
    2.0

    >>> lists = [range(100), range(10), range(500)]
    >>> # Calculate the mean and standard deviation of the elements in lists
    >>> #   which are longer than 100.
    >>> a = freeze(mean() + stddev())
    >>> for l in lists:
    ...     if len(l) > 100:
    ...         source(l) | a
    >>> # Get the mean and standard deviation
    >>> m, s = thaw(a)
    """
    return target.freeze()


__all__ += ['thaw']
def thaw(target):
    return target.thaw()
thaw.__doc__ = freeze.__doc__
       

