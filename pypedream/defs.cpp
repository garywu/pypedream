#include <Python.h>
#include "numpy/arrayobject.h"

#include <memory>

#include "defs.hpp"

bool is_delightful_array(const PyArrayObject * a)
{
    return PyArray_ISCONTIGUOUS(a) && 
        PyArray_ISALIGNED(a) && 
        PyArray_ISBEHAVED(a) && 
        PyArray_ISCARRAY(a);
}

PyObject *
pyint_from_long(long l)
{
#if PY_MAJOR_VERSION >= 3
    return PyLong_FromLong(l);
#else // #if PY_MAJOR_VERSION >= 3
    return PyInt_FromLong(l);
#endif // #if PY_MAJOR_VERSION >= 3
}

