import os
import sys
import math
import numpy
import time
import random

import _src
sys.path.extend(['..', '../..'])
from dagpype import *


_f_name = 'perf.csv'


def _chunking_pipe():
    c = np.chunk_stream_vals(_f_name, cols = '0') | np.mean()


def _pipe():
    c = stream_vals(_f_name, cols = '0') | mean()


def _numpy():
    x = numpy.genfromtxt(_f_name, usecols = (0), delimiter = ',')
    a = numpy.mean(x)


def _run_test(fn, num_rows, num_cols, num_its):
    _src.make_header_csv_file(_f_name, num_rows, num_cols)
    start = time.time()
    for i in range(num_its):
        fn()
    end = time.time()
    diff = (end - start) / num_its
    os.remove(_f_name)
    return diff


def run_tests(names, num_rows, num_cols, num_its):
    fns = dict([
        ('chunking dagpype', lambda: _chunking_pipe()),
        ('dagpype', lambda: _pipe()),
        ('numpy', lambda: _numpy())])
    t = dict([])        
    for name in names:        
        t[name] = _run_test(fns[name], num_rows, num_cols, num_its)
    return t

