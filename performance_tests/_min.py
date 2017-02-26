import os
import sys
import math
import numpy
import time
import random

import _src
sys.path.extend(['..', '../..'])
from dagpype import *


_f_name = 'perf.tsv'


def _chunking_pipe(num_cols):
    print np.chunk_stream_vals(_f_name, delimit = b'\t', cols = range(num_cols)) | filt(lambda a: numpy.min(a)) | min_()


def _pipe():
    print stream_vals(_f_name, delimit = '\t') | filt(lambda tup: min(tup)) | min_()


def _numpy():
    x = numpy.genfromtxt(_f_name, delimiter = b'\t')
    print numpy.min(x)


def _perl():
    os.system("perl -MList::Util=min -alne '@M = (@M, @F); END { print min @M }' %s" % _f_name)


def _run_test(fn, num_lines, num_cols, num_its):
    _src.make_tsv_file(_f_name, num_lines, num_cols)
    start = time.time()
    for i in range(num_its):
        fn()
    end = time.time()
    diff = (end - start) / num_its
    os.remove(_f_name)
    return diff


def run_tests(names, num_lines, num_cols, num_its):
    fns = dict([
        ('chunking dagpype', lambda : _chunking_pipe(num_cols)),
        ('dagpype', lambda: _pipe()),
        ('perl', lambda : _perl()),
        ('numpy', lambda: _numpy())])
    t = dict([])        
    for name in names:        
        t[name] = _run_test(fns[name], num_lines, num_cols, num_its)
    return t


