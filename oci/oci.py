from ctypes import *

lib = cdll.LoadLibrary("./cnabtooci.dylib")


class GoString(Structure):
    _fields_ = [
        ("pointer", c_char_p),
        ("length", c_int)
    ]


def Pull(ref, out_file, out_rel):
    r = GoString(c_char_p(ref.encode('utf-8')), len(ref))
    f = GoString(c_char_p(out_file.encode('utf-8')), len(out_file))
    m = GoString(c_char_p(out_rel.encode('utf-8')), len(out_rel))

    lib.Pull(r, f, m)


Pull("radumatei/pysigny-bundle:v1", "bundle.json", "rel.json")
