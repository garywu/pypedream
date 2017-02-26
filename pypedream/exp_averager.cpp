#include <Python.h>
#include <structmember.h>
#include <numpy/arrayobject.h>

#include <iostream>

#include "defs.hpp"
#include "exp_averager.hpp"

using namespace std;

struct ExpAverager
{
    PyObject_HEAD

    double alpha;

    double y;

    bool first;

    int type_num;
};

extern PyTypeObject ExpAveragerType;

extern "C" void
exp_averager_dealloc(ExpAverager * self)
{
    Py_TYPE(self)->tp_free((PyObject*)self);
}

extern "C" PyObject *
exp_averager_new(PyTypeObject * type, PyObject * args, PyObject * keyword_args)
{
    ExpAverager * const self = (ExpAverager *)type->tp_alloc(type, 0);
    if (self == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    if (!PyArg_ParseTuple(
            args, 
            "d",
            &self->alpha)) {
        PyErr_SetString(PyExc_TypeError, "Failed to parse stuff");
        return NULL;
    }

    self->first = true;

    return (PyObject *)self;
}

template<typename T>
void
calc_update(double alpha, const char * const v, size_t n, bool & first, double & y, char * const o)
{
    const double alpha_tag = 1 - alpha;

    const T * const vals = reinterpret_cast<const T *>(v);
    T * const out = reinterpret_cast<T *>(o);

    if (!first) 
        out[0] = static_cast<T>(alpha * vals[0] + alpha_tag * y);
    first = false;

    for (size_t i = 1; i < n; ++i) 
        out[i] = static_cast<T>(alpha * vals[i] + alpha_tag * out[i - 1]);
    
    y = static_cast<T>(out[n - 1]);
}

extern "C" PyObject *
exp_averager_ave(ExpAverager * self, PyObject *args, PyObject *keyword_args)
{
    PyArrayObject * vs;
    PyArrayObject * outs;
    if (!PyArg_ParseTuple(
            args, 
            "OO",
            reinterpret_cast<PyArrayObject **>(&vs),
            reinterpret_cast<PyArrayObject **>(&outs)) || self == NULL || vs == NULL || outs == NULL) {
        PyErr_SetString(PyExc_TypeError, "Failed to parse stuff");
        return NULL;
    }

    DBG_VERIFY(vs->nd == 1 && outs->nd == 1);
    DBG_VERIFY(vs->dimensions[0] == outs->dimensions[0]);
    const size_t n = vs->dimensions[0];
    if (n == 0)
        Py_RETURN_NONE;

    if (!is_delightful_array(vs) || !is_delightful_array(outs)) {
        PyErr_SetString(PyExc_NotImplementedError, "Must be well behaved");
        return NULL;
    }

    if (self->first)
        self->type_num = vs->descr->type_num;
    if (self->type_num != vs->descr->type_num) { 
        PyErr_SetString(PyExc_TypeError, "Inconsistent types");
        return NULL;
    }
    switch (vs->descr->type_num) {
        case PyArray_CHAR:
	        calc_update<char>(self->alpha, vs->data, n, self->first, self->y, outs->data);
            break;
        case PyArray_UBYTE:
	        calc_update<unsigned char>(self->alpha, vs->data, n, self->first, self->y, outs->data);
            break;
        /*case PyArray_SBYTE:
	        calc_update<signed char>(self->alpha, vs->data, n, self->first, self->y, outs->data);
            break;*/
        case PyArray_SHORT:
	        calc_update<short>(self->alpha, vs->data, n, self->first, self->y, outs->data);
            break;
        case PyArray_INT:
	        calc_update<int>(self->alpha, vs->data, n, self->first, self->y, outs->data);
            break;
        case PyArray_LONG:
	        calc_update<long>(self->alpha, vs->data, n, self->first, self->y, outs->data);
            break;
        case PyArray_FLOAT:
	        calc_update<float>(self->alpha, vs->data, n, self->first, self->y, outs->data);
            break;
        case PyArray_DOUBLE:
	        calc_update<double>(self->alpha, vs->data, n, self->first, self->y, outs->data);
            break;
        default:
        PyErr_SetString(PyExc_TypeError, "Unknown type");
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyMethodDef exp_averager_methods[] = {
    { "ave", (PyCFunction)exp_averager_ave, METH_VARARGS, "" },
    { NULL}
};

static PyMemberDef exp_averager_memberlist[] = {
    { NULL }
};

PyDoc_STRVAR(ExpAveragerType_doc, "");

PyTypeObject ExpAveragerType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "dagpype_c.ExpAverager",               /*tp_name*/
    sizeof(ExpAverager),                   /*tp_basicsize*/
    0,                                      /*tp_itemsize*/
    /* methods */
    (destructor)exp_averager_dealloc,          /*tp_dealloc*/
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
    ExpAveragerType_doc,                     /*tp_doc*/
    0,       /*tp_traverse*/
    0,               /*tp_clear*/
    0,                                      /*tp_richcompare*/
    0,                                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                              /*tp_iternext*/
    exp_averager_methods,                      /*tp_methods*/
    exp_averager_memberlist,                   /*tp_members*/
    0,                       /* tp_getset */
    0,                       /* tp_base */
    0,                       /* tp_dict */
    0,                       /* tp_descr_get */
    0,                       /* tp_descr_set */
    0,                       /* tp_dictoffset */
    0,      /* tp_init */
    0,                         /* tp_alloc */
    exp_averager_new,                 /* tp_new */
};
