#ifndef DEFS_HPP
#define DEFS_HPP

#include <Python.h>
#include <numpy/arrayobject.h>

#include <memory>

#include "dbg.hpp"

bool 
is_delightful_array(const PyArrayObject * a);

PyObject *
pyint_from_long(long l);

#endif // #ifndef DEFS_HPP
