import numpy as np
from multiprocplus import multiprocess_for, MultiprocessRunner
import numpy as np


def func(a, b):
    return a * b


if __name__ == "__main__":
    """
        1. multiprocess_tun must be run in __name__, or will get error
        2. code not run in new process can not write as global
        3. func passed to new process must be global function or member function of global class, 
            can not be lambada function or local function, which will not load in new process.
    """
    N = 100
    A, B = list(range(N)), list(range(N))

    C = [func(a, b) for a, b in zip(A, B)]
    print(sum(C))
    # => run in multiprocess
    C = multiprocess_for(func, [(a, b) for a, b in zip(A, B)], num_process=3)
    print(sum(C))
