"""
Filter operations employing subgroup targets (group, equi-join).
"""


import types

from dagpype._core import filters, sub_pipe_target
from dagpype._snk import to_list
from dagpype._filt import filt


# Tmp Ami - more examples


__all__ = []


__all__ += ['consec_group']
def consec_group(key, key_pipe):
    """
    Groups consecutive similar elements by sending all such elements
        through an ad-hoc create pipe.

    Arguments:
        key -- Function mapping each element to a key. This key will 
            be used to decide which elements are similar. 
        key_pipe -- Function mapping each key to a pipe.

    See Also:
        :func:`dagpype.group`

    Example:

    >>> # Count number of tuples with same first item.
    >>> source([(1, 1), (1, 455), (13, 0)]) | \\
    ... consec_group(
    ...     lambda p : p[0], 
    ...     lambda k : sink(k) + count()) | \\
    ... to_list()
    [(1, 2), (13, 1)]
    """    

    @filters
    def _dagpype_internal_fn_act(target):
        sub_target, cur_k = None, None
        try:
            while True:            
                e = (yield)
                k = key(e)
                if sub_target is None or cur_k != k:
                    cur_k = k
                    pipe = key_pipe(k)
                    sub_target = sub_pipe_target(pipe, target)
                try:
                    sub_target.send(e)
                except Exception as e:                
                    pass
        except GeneratorExit:
            if sub_target is not None:
                sub_target.close()
            target.close()        

    return _dagpype_internal_fn_act


__all__ += ['group']
def group(key, key_pipe):
    """
    Groups not-necessarily-consecutive similar elements by sending all such elements
        through an ad-hoc create pipe.

    Arguments:
        key -- Function mapping each element to a key. This key will 
            be used to decide which elements are similar. 
        key_pipe -- Function mapping each key to a pipe.

    See Also:
        :func:`dagpype.consec_group`

    Example:

    >>> # Count number of tuples with same first item.
    >>> source([(1, 1), (13, 0), (1, 455)]) | \\
    ...     group(
    ...         lambda p : p[0], 
    ...         lambda k : sink(k) + count()) | \\
    ...     to_list()
    [(1, 2), (13, 1)]
    """    

    @filters
    def _dagpype_internal_fn_act(target):
        pipes, targets = [], dict([])
        try:
            while True:
                e = (yield)
                k = key(e)
                if k not in targets:
                    targets[k] = sub_pipe_target(key_pipe(k), target)
                    pipes.append(targets[k])
                # Tmp - make sub_pipe_target have this.
                try:
                    targets[k].send(e)            
                except Exception as e:                
                    pass
        except GeneratorExit:
            for p in pipes:
                p.close()    
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['chain']
def chain(key_pipe):
    """
    Chains the result of applying an ad-hoc created pipe to each element.

    Arguments:
        key_pipe - Function mapping each element to a pipe.

    Example:

    >>> # Chain each element twice.
    >>> source([1, 2, 3]) | chain(lambda p : source([p] * 2)) | to_list()
    [1, 1, 2, 2, 3, 3]
    """

    @filters
    def _dagpype_internal_fn_act(target):            
        try:
            while True:
                k = (yield)
                pipe = key_pipe(k)
                sub_pipe_target(pipe, target)
        except GeneratorExit:
            target.close()

    return _dagpype_internal_fn_act


__all__ += ['dict_join']
def dict_join(
        joined, 
        key, 
        common_pipe,
        out_of_dict_pipe = None,
        dict_only_pipe = None):
    r"""
    Performs an SQL-style join with a dictionary.

    Arguments:
        joined -- Dictionary of items with which to join.
        key -- Function mapping each element to a key. This key will 
            be used to decide with which joined element (if any) to join.
        common_pipe -- Function taking a key and a value from the joined dictionary, and
            returning a pipe. This pipe will be used for all elements matching the key.

    Keyword Arguments:
        out_of_dict_pipe -- Pipe used for all elements not in the joined dictionary (default None).
        dict_only_pipe -- Pipe used for all elements only in the dictionary (default None).

    Examples:

    >>> # Assume employee.csv has the following content:
    >>> # Name,EmpId,DeptName
    >>> # Harry,3415,Finance
    >>> # Sally,2241,Sales
    >>> # George,3401,Finance
    >>> # Harriet,2202,Sales
    >>> # Nelson,2455,Entertainment
    >>> #
    >>> # Assume dept.csv has the following content:
    >>> # DeptName,Manager
    >>> # Finance,George
    >>> # Sales,Harriet
    >>> # Production,Charles

    >>> # Create a dictionary mapping employees to managers:
    >>> d = stream_vals('employee.csv', (b'Name', b'EmpId', b'DeptName'), (bytes, int, bytes)) | \
    ...     dict_join(
    ...         stream_vals('dept.csv', (b'DeptName', b'Manager'), (bytes, bytes)) | to_dict(),
    ...         lambda name_id_dept : name_id_dept[2],
    ...         lambda dept, manager : filt(lambda name_id_dept : (name_id_dept[0], manager)),
    ...         filt(lambda name_id_dept : (name_id_dept[0], None)), 
    ...         None) | \
    ...     to_dict()
    >>> assert d[b'Harriet'] == b'Harriet'
    >>> assert d[b'Nelson'] is None

    >>> # Annoying Py3k compatibility stuff:
    >>> # Create a dictionary mapping managers to the number of people they manage:
    >>> d = stream_vals('employee.csv', (b'Name', b'EmpId', b'DeptName'), (bytes, int, bytes)) | \
    ...     dict_join(
    ...         stream_vals('dept.csv', (b'DeptName', b'Manager'), (bytes, bytes)) | to_dict(),
    ...         lambda name_id_dept : name_id_dept[2],
    ...         lambda dept, manager : sink(manager) + count(),
    ...         None, 
    ...         filt(lambda dept_manager : (dept_manager[1], 0))) | \
    ...     to_dict()
    >>> assert d[b'Harriet'] == 2
    >>> assert d[b'Charles'] == 0
    """

    @filters
    def _dagpype_internal_fn_act(target):
        if out_of_dict_pipe is not None:
            out_of_dict_target = sub_pipe_target(out_of_dict_pipe, target)
        else:
            out_of_dict_target = None
            
        if dict_only_pipe is not None:
            dict_only_target = sub_pipe_target(dict_only_pipe, target)
        else:
            dict_only_target = None
    
        targets = dict([])
        try:
            while True:
                e = (yield)
                k = key(e)
                if k not in joined:
                    if out_of_dict_target is not None:
                        out_of_dict_target.send(e)
                    continue
                if k not in targets:
                    targets[k] = sub_pipe_target(
                        common_pipe(k, joined[k]), target)
                targets[k].send(e)            
        except GeneratorExit:
            for k in targets:
                targets[k].close()
    
            if out_of_dict_target is not None:
                out_of_dict_target.close()
            if dict_only_target is not None:
                for k in set(joined.keys()) - set(targets.keys()):
                    dict_only_target.send((k, joined[k]))
                dict_only_target.close()
            target.close()

    return _dagpype_internal_fn_act

