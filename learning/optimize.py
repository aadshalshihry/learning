"""Optimizers for optimizing model parameters."""

import functools
import operator

import numpy

############################
# Problem
############################
class Problem(object):
    """Problem instance for optimizer.

    Functions are prioritized as follows:
        value(s): first priority, second_priority, (first_value_using_best_func, second_func)

        obj: obj_func, obj_jac_func, obj_hess_func, obj_jac_hess_func
        jac: jac_func, obj_jac_func, jac_hess_func, obj_jac_hess_func
        hess: hess_func, obj_hess_func, jac_hess_func, obj_jac_hess_func

        obj_jac: obj_jac_func, obj_jac_hess_func, (obj, jac)
        obj_hess: obj_hess_func, obj_jac_hess_func, (obj, hess)
        jac_hess: jac_hess_func, obj_jac_hess_func, (jac, hess)

        obj_jac_hess: obj_jac_hess_func, (obj_jac_func, hess), (obj_hess_func, jac),
            (obj, jac_hess_func), (obj, jac, hess)
    """
    def __init__(self, obj_func=None, jac_func=None, hess_func=None,
                 obj_jac_func=None, obj_hess_func=None, jac_hess_func=None,
                 obj_jac_hess_func=None):
        # Get objective function
        if obj_func is not None:
            self.get_obj = obj_func
        elif obj_jac_func is not None:
            self.get_obj = functools.partial(_call_return_index, obj_jac_func, 0)
        elif obj_hess_func is not None:
            self.get_obj = functools.partial(_call_return_index, obj_hess_func, 0)
        elif obj_jac_hess_func is not None:
            self.get_obj = functools.partial(_call_return_index, obj_jac_hess_func, 0)
        else:
            self.get_obj = _return_none

        # Get jacobian function
        if jac_func is not None:
            self.get_jac = jac_func
        elif obj_jac_func is not None:
            self.get_jac = functools.partial(_call_return_index, obj_jac_func, 1)
        elif jac_hess_func is not None:
            self.get_jac = functools.partial(_call_return_index, jac_hess_func, 0)
        elif obj_jac_hess_func is not None:
            self.get_jac = functools.partial(_call_return_index, obj_jac_hess_func, 1)
        else:
            self.get_jac = _return_none

        # Get hessian function
        if hess_func is not None:
            self.get_hess = hess_func
        elif obj_hess_func is not None:
            self.get_hess = functools.partial(_call_return_index, obj_hess_func, 1)
        elif jac_hess_func is not None:
            self.get_hess = functools.partial(_call_return_index, jac_hess_func, 1)
        elif obj_jac_hess_func is not None:
            self.get_hess = functools.partial(_call_return_index, obj_jac_hess_func, 2)
        else:
            self.get_hess = _return_none

        # Get objective and jacobian function
        if obj_jac_func is not None:
            self.get_obj_jac = obj_jac_func
        elif obj_jac_hess_func is not None:
            self.get_obj_jac = functools.partial(_call_return_indices, obj_jac_hess_func, (0, 1))
        else:
            self.get_obj_jac = functools.partial(_bundle, (self.get_obj, self.get_jac))

        # Get objective and hessian function
        if obj_hess_func is not None:
            self.get_obj_hess = obj_hess_func
        elif obj_jac_hess_func is not None:
            self.get_obj_hess = functools.partial(_call_return_indices, obj_jac_hess_func, (0, 2))
        else:
            self.get_obj_hess = functools.partial(_bundle, (self.get_obj, self.get_hess))

        # Get jacobian and hessian function
        if jac_hess_func is not None:
            self.get_jac_hess = jac_hess_func
        elif obj_jac_hess_func is not None:
            self.get_jac_hess = functools.partial(_call_return_indices, obj_jac_hess_func, (1, 2))
        else:
            self.get_jac_hess = functools.partial(_bundle, (self.get_jac, self.get_hess))

        # Get objective, jacobian, hessian function
        if obj_jac_hess_func is not None:
            self.get_obj_jac_hess = obj_jac_hess_func
        elif obj_jac_func is not None:
            self.get_obj_jac_hess = functools.partial(
                _bundle_add,
                (obj_jac_func, functools.partial(_tuple_result, self.get_hess))
            )
        elif obj_hess_func is not None:
            self.get_obj_jac_hess = functools.partial(
                _bundle_add_split, obj_hess_func, self.get_jac)
        elif jac_hess_func is not None:
            self.get_obj_jac_hess = functools.partial(
                _bundle_add,
                (functools.partial(_tuple_result, self.get_obj), jac_hess_func)
            )
        else:
            self.get_obj_jac_hess = functools.partial(
                _bundle, (self.get_obj, self.get_jac, self.get_hess))

def _call_return_indices(func, indices, *args, **kwargs):
    """Return indices of func called with *args and **kwargs.

    Use with functools.partial to wrap func.
    """
    values = func(*args, **kwargs)
    return [values[i] for i in indices]

def _call_return_index(func, index, *args, **kwargs):
    """Return index of func called with *args and **kwargs.

    Use with functools.partial to wrap func.
    """
    return func(*args, **kwargs)[index]

def _bundle_add(functions, *args, **kwargs):
    """Return results of functions, concatenated together, called with *args and **kwargs."""
    return reduce(operator.add, _bundle(functions, *args, **kwargs))

def _bundle(functions, *args, **kwargs):
    """Return result of each function, called with *args and **kwargs."""
    return [func(*args, **kwargs) for func in functions]

def _bundle_add_split(f_1, f_2, *args, **kwargs):
    """Return f_1[0], f_2, f_1[1], called with *args, **kwargs."""
    f_1_values = f_1(*args, **kwargs)
    return f_1_values[0], f_2(*args, **kwargs), f_1_values[1]

def _tuple_result(func, *args, **kwargs):
    return func(*args, **kwargs), # , makes tuple

def _return_none(*args, **kwargs):
    """Return None."""
    return None

################################
# Optimizer
################################
class Optimizer(object):
    """Optimizer for optimizing model parameters."""

    def reset(self):
        """Reset optimizer parameters."""
        raise NotImplementedError()

    def next(self, problem, parameters):
        """Return next iteration of this optimizer."""
        raise NotImplementedError()

################################
# Implementations
################################
class SteepestDescent(Optimizer):
    """Simple steepest descent with constant step size."""
    def __init__(self, step_size=1.0):
        super(SteepestDescent, self).__init__()
        self._step_size = step_size

    def reset(self):
        """Reset optimizer parameters."""
        pass

    def next(self, problem, parameters):
        """Return next iteration of this optimizer."""
        obj_value, jacobian = problem.get_obj_jac(parameters)

        # Take a step down the first derivative direction
        return obj_value, parameters - self._step_size*jacobian

class SteepestDescentMomentum(Optimizer):
    """Simple gradient descent with constant step size, and momentum."""
    def __init__(self, step_size=1.0, momentum_rate=0.2):
        super(SteepestDescentMomentum, self).__init__()
        self._step_size = step_size
        self._momentum_rate = momentum_rate

        # Store previous jacobian for momentum
        self._prev_jacobian = None

    def reset(self):
        """Reset optimizer parameters."""
        self._prev_jacobian = None

    def next(self, problem, parameters):
        """Return next iteration of this optimizer."""
        obj_value, jacobian = problem.get_obj_jac(parameters)

        next_parameters = parameters - self._step_size*jacobian
        if self._prev_jacobian is not None:
            next_parameters -= (self._step_size*self._momentum_rate) * self._prev_jacobian

        # Take a step down the first derivative direction
        return obj_value, next_parameters

def _wolfe_conditions(step_size, parameters, obj_xk, jac_xk, step_dir, obj_jac_func, c_1, c_2):
    """Return True if Wolfe conditions (Armijo rule and curvature condition) are met.

    step_size: a; Proposed step size.
    parameters: x_k; Parameter values at current step.
    obj_xk: f(x_k); Objective value at x_k.
    jac_xk: grad_f(x_k); First derivative (jacobian) at x_k.
    step_dir: p_k; Step direction (ex. jacobian in steepest descent) at x_k.
    obj_jac_func: Function taking parameters and returning obj and jac at given parameters.
    c_1: Strictness parameter for Armijo rule.
    c_2: Strictness parameter for curvature.
    """
    if not (0 < c_1 < c_2 < 1):
        raise ValueError('0 < c_1 < c_2 < 1')

    # NOTE: Note that we add step_dir, not subtract, ex. -jacobian is a step direction
    obj_xk_plus_ap, jac_xk_plus_ap = obj_jac_func(parameters + step_size*step_dir)

    wolfe = (_armijo_rule(step_size, obj_xk, jac_xk, step_dir, obj_xk_plus_ap, c_1)
             and _curvature_condition(jac_xk, step_dir, jac_xk_plus_ap, c_2))
    assert isinstance(wolfe, (numpy.bool_, bool)), '_wolfe_conditions should return bool, check parameters shape'
    return wolfe

def _armijo_rule(step_size, obj_xk, jac_xk, step_dir, obj_xk_plus_ap, c_1):
    """Return True if Armijo rule is met.

    Armijo rule:
    f(x_k + a_k p_k) <= f(x_k) + c_1 a_k p_k^T grad_f(x_k)

    args:
        step_size: a; Proposed step size.
        obj_xk: f(x_k); Objective value at x_k.
        jac_xk: grad_f(x_k); First derivative (jacobian) at x_k.
        step_dir: p_k; Step direction (ex. jacobian in steepest descent) at x_k.
        obj_xk_plus_ap: f(x_k + a_k p_k); Objective value at x_k + a_k p_k
        c_1: Strictness parameter for Armijo rule.
    """
    return obj_xk_plus_ap <= obj_xk + ((c_1*step_size)*jac_xk.T).dot(step_dir)

def _curvature_condition(jac_xk, step_dir, jac_xk_plus_ap, c_2):
    """Return True if curvature condition is met.

    Curvature condition:
    -p_k^T grad_f(x_k = a_k p_k) <= -c_2 p_k^T grad_f(x_k)

    args:
        jac_xk: grad_f(x_k); First derivative (jacobian) at x_k.
        step_dir: p_k; Step direction (ex. jacobian in steepest descent) at x_k.
        jac_xk_plus_ap: grad_f(x_k = a_k p_k); jacobian value at x_k + a_k p_k
        c_2: Strictness parameter for curvature.
    """
    return (jac_xk_plus_ap.T).dot(step_dir) >= (c_2*jac_xk.T).dot(step_dir)