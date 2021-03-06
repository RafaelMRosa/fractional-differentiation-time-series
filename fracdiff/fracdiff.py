import numpy as np
from numpy.fft import fft, ifft

# from: http://www.mirzatrokic.ca/FILES/codes/fracdiff.py
# small modification: wrapped 2**np.ceil(...) around int()
# https://github.com/SimonOuellette35/FractionalDiff/blob/master/question2.py

_default_thresh = 1e-4

def get_weights(d, size):
    """Expanding window fraction difference weights."""
    w = [1.0]
    for k in range(1, size):
        w_ = -w[-1] / k * (d - k + 1)
        w.append(w_)
    w = np.array(w[::-1]).reshape(-1, 1)
    return w

import numba

@numba.njit
def get_weights_ffd(d, thres, lim=99999):
    """Fixed width window fraction difference weights.
    Set lim to be large if you want to only stop at thres.
    Set thres to be zero if you want to ignore it.
    """
    w = [1.0]
    k = 1
    for i in range(1, lim):
        w_ = -w[-1] / k * (d - k + 1)
        if abs(w_) < thres:
            break
        w.append(w_)
        k += 1
    w = np.array(w[::-1]).reshape(-1, 1)
    return w

def frac_diff_ffd(x, d, thres=_default_thresh, lim=None):
    assert isinstance(x, np.ndarray)
    assert x.ndim == 1
    if lim is None:
        lim = len(x)
    w, out = _frac_diff_ffd(x, d, lim, thres=thres)
    # print(f'weights is shape {w.shape}')
    return out

# this method was not faster
# def frac_diff_ffd_stride_tricks(x, d, thres=_default_thresh):
#     """d is any positive real"""
#     assert isinstance(x, np.ndarray)
#     w = get_weights_ffd(d, thres, len(x))
#     width = len(w) - 1
#     output = np.empty(len(x))
#     output[:width] = np.nan
#     output[width:] = np.dot(np.lib.stride_tricks.as_strided(x, (len(x) - width, len(w)), (x.itemsize, x.itemsize)), w[:,0])
#     return output

@numba.njit
def _frac_diff_ffd(x, d, lim, thres=_default_thresh):
    """d is any positive real"""
    w = get_weights_ffd(d, thres, lim)
    width = len(w) - 1
    output = []
    output.extend([np.nan] * width) # the first few entries *were* zero, should be nan?
    for i in range(width, len(x)):
        output.append(np.dot(w.T, x[i - width: i + 1])[0])
    return w, np.array(output)


def fast_frac_diff(x, d):
    """expanding window version using fft form"""
    assert isinstance(x, np.ndarray)
    T = len(x)
    np2 = int(2 ** np.ceil(np.log2(2 * T - 1)))
    k = np.arange(1, T)
    b = (1,) + tuple(np.cumprod((k - d - 1) / k))
    z = (0,) * (np2 - T)
    z1 = b + z
    z2 = tuple(x) + z
    dx = ifft(fft(z1) * fft(z2))
    return np.real(dx[0:T])


# TESTS


def test_all():
    for d in [0.3, 1, 1.5, 2, 2.5]:
        test_fast_frac_diff_equals_fracDiff_original_impl(d=d)
        test_frac_diff_ffd_equals_original_impl(d=d)
        # test_frac_diff_ffd_equals_prado_original(d=d) # his implementation is busted for fractional d


# def test_frac_diff_ffd_equals_prado_original(d=3):
#     # ignore this one for now as Prado's version does not work
#     from .prado_orig import fracDiff_FFD_prado_original
#     import pandas as pd
# 
#     x = np.random.randn(100)
#     a = frac_diff_ffd(x, d, thres=_default_thresh)
#     b = fracDiff_FFD_prado_original(pd.DataFrame(x), d, thres=_default_thresh)
#     b = np.squeeze(b.values)
#     a = a[d:]  # something wrong with the frac_diff_ffd gives extra entries of zero
#     assert np.allclose(a, b)
#     # return locals()


def test_frac_diff_ffd_equals_original_impl(d=3):
    from .prado_orig import fracDiff_FFD_original_impl
    import pandas as pd

    x = np.random.randn(100)
    a = frac_diff_ffd(x, d, thres=_default_thresh)
    b = fracDiff_FFD_original_impl(pd.DataFrame(x), d, thres=_default_thresh)
    assert np.allclose(a, b)
    # return locals()


def test_fast_frac_diff_equals_fracDiff_original_impl(d=3):
    from .prado_orig import fracDiff_original_impl
    import pandas as pd

    x = np.random.randn(100)
    a = fast_frac_diff(x, d)
    b = fracDiff_original_impl(pd.DataFrame(x), d, thres=None)
    b = b.values
    assert a.shape == b.shape
    assert np.allclose(a, b)
    # return locals()


if __name__ == "__main__":
    test_all()
