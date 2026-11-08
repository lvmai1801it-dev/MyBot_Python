# ==== ocr_reader.py ====
try:
    import torch
except Exception:
    pass
import os

_reader = None

def _get_reader():
    global _reader
    if _reader is None:
        os.environ.setdefault('CUDA_VISIBLE_DEVICES', '')
        os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')
        os.environ.setdefault('OMP_NUM_THREADS', '1')
        os.environ.setdefault('MKL_NUM_THREADS', '1')

        import easyocr
        _reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _reader


class _LazyReader:
    def __getattr__(self, name):
        return getattr(_get_reader(), name)


reader = _LazyReader()


def read_text(img, **kwargs):
    return _get_reader().readtext(img, detail=0, **kwargs)
