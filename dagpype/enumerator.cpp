#include <Python.h>
#include <structmember.h>
#include <numpy/arrayobject.h>

#include <iostream>

#include "defs.hpp"
#include "enumerator.hpp"

using namespace std;

struct Enumerator
{
    PyObject_HEAD
    
    long count;
};

extern PyTypeObject EnumeratorType;

extern "C" void
enumerator_dealloc(Enumerator * self)
{
    Py_TYPE(self)->tp_free((PyObject*)self);
}

extern "C" PyObject *
enumerator_new(PyTypeObject * type, PyObject * args, PyObject * keyword_args)
{
    Enumerator * const self = (Enumerator *)type->tp_alloc(type, 0);
    if (self == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    if (!PyArg_ParseTuple(
            args, 
            "l",
            &self->count)) {
        PyErr_SetString(PyExc_TypeError, "Failed to parse stuff");
        return NULL;
    }

    return (PyObject *)self;
}

extern "C" PyObject *
enumerator_next(Enumerator * self, PyObject * args, PyObject * keyword_args)
{
    PyObject * o;
    if (!PyArg_ParseTuple(
            args, 
            "O",
            &o) || o == NULL) {
        PyErr_SetString(PyExc_TypeError, "Failed to parse stuff");
        return NULL;
    }
    
    Py_INCREF(o);
    
    PyObject * const fields = PyTuple_New(2);
    if (fields == NULL) {
        PyErr_NoMemory();
        Py_XDECREF(o);
        return NULL;
    }
        
    PyObject * const n = pyint_from_long(self->count++);
    if (n == NULL) {
        PyErr_NoMemory();
        Py_XDECREF(fields);
        Py_XDECREF(o);
        return NULL;
    }    
        
    PyTuple_SET_ITEM(fields, 0, n);        
    PyTuple_SET_ITEM(fields, 1, o);   
    
    return fields;     
}

static PyMethodDef enumerator_methods[] = {
    { "next", (PyCFunction)enumerator_next, METH_VARARGS, "" },
    { NULL}
};

static PyMemberDef enumerator_memberlist[] = {
    { NULL }
};

PyDoc_STRVAR(EnumeratorType_doc, "");

PyTypeObject EnumeratorType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "dagpype_c.Enumerator",               /*tp_name*/
    sizeof(Enumerator),                   /*tp_basicsize*/
    0,                                      /*tp_itemsize*/
    /* methods */
    (destructor)enumerator_dealloc,          /*tp_dealloc*/
    0,                                         /*tp_print*/
    0,                                         /*tp_getattr*/
    0,                                         /*tp_setattr*/
    0,                                          /*tp_compare*/
    0,                                        /*tp_repr*/
    0,                                      /*tp_as_number*/
    0,                                      /*tp_as_sequence*/
    0,                                      /*tp_as_mapping*/
    0,                            /*tp_hash*/
    0,                         /*tp_call*/
    0,                            /*tp_str*/
    0,                                      /*tp_getattro*/
    0,                                      /*tp_setattro*/
    0,                                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT ,                     /*tp_flags*/
    EnumeratorType_doc,                     /*tp_doc*/
    0,       /*tp_traverse*/
    0,               /*tp_clear*/
    0,                                      /*tp_richcompare*/
    0,                                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                              /*tp_iternext*/
    enumerator_methods,                      /*tp_methods*/
    enumerator_memberlist,                   /*tp_members*/
    0,                       /* tp_getset */
    0,                       /* tp_base */
    0,                       /* tp_dict */
    0,                       /* tp_descr_get */
    0,                       /* tp_descr_set */
    0,                       /* tp_dictoffset */
    0,      /* tp_init */
    0,                         /* tp_alloc */
    enumerator_new,                 /* tp_new */
};
