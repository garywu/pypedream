#define MODULE_VERSION "1.0"

#include "Python.h"
#include "structmember.h"
#define PY_ARRAY_UNIQUE_SYMBOL dagpype_c
#include <numpy/arrayobject.h>

#include <cstdio>
#include <cstdlib>

#include "defs.hpp"
#include "col_reader.hpp"
#include "line_writer.hpp"
#include "array_col_reader.hpp"
#include "_line_to_array.hpp"
#include "line_to_tuple.hpp"
#include "exp_averager.hpp"
#include "enumerator.hpp"
#include "correlator.hpp"

using namespace std;

struct module_state 
{
    PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))
#else
#define GETSTATE(m) (&_state)
static struct module_state _state;
#endif

static PyObject *
error_out(PyObject *m) {
    struct module_state *st = GETSTATE(m);
    PyErr_SetString(st->error, "something bad happened");
    return NULL;
}

static PyMethodDef dagpype_c_methods[] =
{
    { "line_to_tuple", (PyCFunction)line_to_tuple, METH_VARARGS, NULL},
    { "parser_max_field_len", (PyCFunction)parser_max_field_len, METH_VARARGS, NULL},
#ifdef DAGPYPE_USE_AIO
    { "line_writer", (PyCFunction)line_writer, METH_VARARGS, NULL},
    { "line_writer_write", (PyCFunction)line_writer_write, METH_VARARGS, NULL},
    { "line_writer_close", (PyCFunction)line_writer_close, METH_VARARGS, NULL},
#endif // #ifdef DAGPYPE_USE_AIO
    { NULL, NULL }
};

#if PY_MAJOR_VERSION >= 3

static int dagpype_c_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int dagpype_c_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "dagpype_c",
    NULL,
    sizeof(struct module_state),
    dagpype_c_methods,
    NULL,
    dagpype_c_traverse,
    dagpype_c_clear,
    NULL
};

#define INITERROR return NULL

extern "C" PyObject *
PyInit_dagpype_c(void)

#else
#define INITERROR return

extern "C" void
initdagpype_c(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("dagpype_c", dagpype_c_methods);
#endif

    if (module == NULL)
        INITERROR;
    struct module_state *st = GETSTATE(module);

    st->error = PyErr_NewException("dagpype_c.Error", NULL, NULL);
    if (st->error == NULL) {
        Py_DECREF(module);
        INITERROR;
    }
    
    import_array();
    
    if (PyType_Ready(&EnumeratorType) < 0) {
        Py_DECREF(module);
        INITERROR;
    }
    Py_INCREF(&EnumeratorType);
    PyModule_AddObject(module, "Enumerator", (PyObject *)&EnumeratorType);

    if (PyType_Ready(&CorrelatorType) < 0) {
        Py_DECREF(module);
        INITERROR;
    }
    Py_INCREF(&CorrelatorType);
    PyModule_AddObject(module, "Correlator", (PyObject *)&CorrelatorType);

    if (PyType_Ready(&ExpAveragerType) < 0) {
        Py_DECREF(module);
        INITERROR;
    }
    Py_INCREF(&CorrelatorType);
    PyModule_AddObject(module, "ExpAverager", (PyObject *)&ExpAveragerType);

    if (PyType_Ready(&ColReaderType) < 0) {
        Py_DECREF(module);
        INITERROR;
    }
    Py_INCREF(&ColReaderType);
    PyModule_AddObject(module, "ColReader", (PyObject *)&ColReaderType);

    if (PyType_Ready(&ArrayColReaderType) < 0) {
        Py_DECREF(module);
        INITERROR;
    }
    Py_INCREF(&ArrayColReaderType);
    PyModule_AddObject(module, "ArrayColReader", (PyObject *)&ArrayColReaderType);

#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
