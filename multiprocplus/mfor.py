import multiprocessing
import time
import traceback
import sys


class MapFunctionWrapper(object):
    def __init__(self, func):
        self.func = func

    def __call__(self, args):
        try:
            i = args[0]
            return i, self.func(*args[1:])
        except BaseException as b:
            print(f"[MultiprocessRunner:({b})", file=sys.stderr)
            traceback.print_exc()
            return None


class MultiProcessMap(object):
    def __init__(self, num_process=multiprocessing.cpu_count()):
        self.num_process = self.get_num_process(num_process)
        self.pool = multiprocessing.Pool(self.num_process)

    def get_num_process(self, num_process):
        if isinstance(num_process, int):
            if num_process < 0:
                num_process = multiprocessing.cpu_count()
        elif isinstance(num_process, float):
            assert 0.0 <= num_process <= 1.0, f"num_process must be float in [0.0, 1.0] or int," \
                                              f" but got <{type(num_process)} {num_process}>"
            num_process = int(round(num_process * multiprocessing.cpu_count()))
        else:
            raise ValueError(f"num_process must be float in [0.0, 1.0] or int, but got <{type(num_process)} {num_process}>")
        return min(num_process, multiprocessing.cpu_count())

    def __call__(self, func, args_list, with_tqdm=False):
        func = MapFunctionWrapper(func)
        args_list = [tuple([i] + list(args)) for i, args in enumerate(args_list)]
        map_iter = self.pool.imap_unordered(func, args_list)
        if with_tqdm:
            from tqdm import tqdm
            map_iter = tqdm(map_iter, total=len(args_list))

        results = [None] * len(args_list)
        for i, result in map_iter:
            results[i] = result
        return results


def mfor(func, args_list, num_process, with_tqdm=False):
    mapper = MultiProcessMap(num_process)
    return mapper(func, args_list, with_tqdm)
