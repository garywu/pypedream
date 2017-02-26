#include <Python.h>
#include <structmember.h>
#include <numpy/arrayobject.h>

#include <iostream>

#include "defs.hpp"
#include "correlator.hpp"

using namespace std;

struct Correlator
{
    PyObject_HEAD
    
    double sx, sy, sxx, sxy, syy;
    unsigned long n;
};

extern PyTypeObject CorrelatorType;

extern "C" void
correlator_dealloc(Correlator * self)
{
    Py_TYPE(self)->tp_free((PyObject*)self);
}

extern "C" PyObject *
correlator_new(PyTypeObject * type, PyObject * args, PyObject * keyword_args)
{
    Correlator * const self = (Correlator *)type->tp_alloc(type, 0);
    if (self == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    self->sx = self->sy = self->sxx = self->sxy = self->syy = self->n = 0;
    
    return (PyObject *)self;
}

extern "C" PyObject *
correlator_push(Correlator * self, PyObject *args, PyObject *keyword_args)
{    
    double x, y;
    if (!PyArg_ParseTuple(
            args, 
            "dd",
            &x, &y)) {
        PyErr_SetString(PyExc_TypeError, "Failed to parse stuff");
        return NULL;
    }
    
    self->sx += x;
    self->sy += y;
    self->sxx += x * x;
    self->sxy += x * y;
    self->syy += y * y;
    ++self->n;
    
    Py_RETURN_NONE;
}

extern "C" PyObject *
correlator_corr(Correlator * self)
{
    const double corr = (self->n * self->sxy - self->sx * self->sy) / 
        sqrt(self->n * self->sxx - self->sx * self->sx) / 
        sqrt(self->n * self->syy - self->sy * self->sy);
        
    return PyFloat_FromDouble(corr);    
}

static PyMethodDef correlator_methods[] = {
    { "push", (PyCFunction)correlator_push, METH_VARARGS, "" },
    { "corr", (PyCFunction)correlator_corr, METH_NOARGS, "" },
    { NULL}
};

static PyMemberDef correlator_memberlist[] = {
    { NULL }
};

PyDoc_STRVAR(CorrelatorType_doc, "");

PyTypeObject CorrelatorType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "dagpype_c.Correlator",               /*tp_name*/
    sizeof(Correlator),                   /*tp_basicsize*/
    0,                                      /*tp_itemsize*/
    /* methods */
    (destructor)correlator_dealloc,          /*tp_dealloc*/
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
    CorrelatorType_doc,                     /*tp_doc*/
    0,       /*tp_traverse*/
    0,               /*tp_clear*/
    0,                                      /*tp_richcompare*/
    0,                                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                              /*tp_iternext*/
    correlator_methods,                      /*tp_methods*/
    correlator_memberlist,                   /*tp_members*/
    0,                       /* tp_getset */
    0,                       /* tp_base */
    0,                       /* tp_dict */
    0,                       /* tp_descr_get */
    0,                       /* tp_descr_set */
    0,                       /* tp_dictoffset */
    0,      /* tp_init */
    0,                         /* tp_alloc */
    correlator_new,                 /* tp_new */
};
