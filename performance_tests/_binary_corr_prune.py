import os
import sys
import math
import numpy
import time

import _src
import c_corr
sys.path.extend(['..', '../..'])
from dagpype import *


_f_name = 'perf.dat'


def _chunking_pipe():
    c = np.chunk_stream_bytes(_f_name, num_cols = 2) | \
        filt(lambda a : a[numpy.logical_and(a[:, 0] < 0.25, a[:, 1] < 0.25), :]) | \
        np.corr()


def _c():
    c_corr.c_corr_prune(_f_name)


def _numpy():
    s = open(_f_name, 'rb').read()
    a = numpy.fromstring(s)
    xy = a.reshape(a.shape[0] / 2, 2)    
    xy = xy[numpy.logical_and(xy[:, 0] < 0.25, xy[:, 1] < 0.25), :]

    s = numpy.sum(xy, axis = 0)
    sx = s[0]
    sy = s[1]

    c = numpy.dot(xy.T, xy)

    sxx = c[0, 0]
    sxy = c[0, 1]
    syy = c[1, 1]

    n = xy.shape[0]
    res = (n * sxy - sx * sy) / math.sqrt(n * sxx - sx * sx) / math.sqrt(n * syy - sy * sy)


def _run_test(fn, num_elems, num_its):
    _src.make_binary_file(_f_name, 2 * num_elems)
    start = time.time()
    for i in range(num_its):
        fn()
    end = time.time()
    diff = (end - start) / num_its
    os.remove(_f_name)
    return diff


def run_tests(names, num_elems, num_its):
    fns = dict([
        ('chunking dagpype', lambda : _chunking_pipe()),
        ('c', lambda : _c()),
        ('numpy', lambda : _numpy())])    
    t = dict([])        
    for name in names:        
        t[name] = _run_test(fns[name], num_elems, num_its)
    return t

