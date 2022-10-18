
# API
### multiprocess_for
```python
def multiprocess_for(func, args_list, share_data_list=[], cost_list=None, num_process=multiprocessing.cpu_count(), debug_info=False):
```

the equal implementation of single process can be treated as:
```python
result = []
for args in args_list:
    args = args + share_data_list
    result.append(func(*args))
return result
```

#### 0. args_list

args_list is list of tuple, each tuple contains args passed to func
we only support arg

#### 1. [num_process](test/multiprocplus_test2_num_process.py)

```python
# => run in single process
print("run in single process")
C = multiprocess_for(func, [(a, b) for a, b in zip(A, B)], num_process=0.0, debug_info=True)  # 0.0 * cpu_count()
C = multiprocess_for(func, [(a, b) for a, b in zip(A, B)], num_process=0, debug_info=True)
C = multiprocess_for(func, [(a, b) for a, b in zip(A, B)], num_process=1, debug_info=True)

# => run in all processes
print("run in all processes")
C = multiprocess_for(func, [(a, b) for a, b in zip(A, B)], debug_info=True)
C = multiprocess_for(func, [(a, b) for a, b in zip(A, B)], num_process=1.0, debug_info=True)   # 1.0 * cpu_count()
C = multiprocess_for(func, [(a, b) for a, b in zip(A, B)], num_process=-1, debug_info=True)

# => run in half of all processes
print("run in half of all processes")
C = multiprocess_for(func, [(a, b) for a, b in zip(A, B)], num_process=0.5, debug_info=True)   # 0.5 * cpu_count()

# => run in 2 processes
print("run in 2 processes")
C = multiprocess_for(func, [(a, b) for a, b in zip(A, B)], num_process=2, debug_info=True)
```

#### 2. [share_data_list](test/multiprocplus_test2_share_data.py)
```python
def example_of_shared_data(A, B):
    # => run in single process
    C = [func(a, b) for a, b in zip(A, B)]
    print(sum(C))
    # => run in 3 processes
    C = multiprocess_for(func, [(a, b) for a, b in zip(A, B)], num_process=3)
    C = multiprocess_for(func1, [(idx, a) for idx, a in enumerate(A)], share_data_list=[B], num_process=3)
    print(sum(C))

def func1(idx, a, B):
    return a * B[idx]

def func(a, b):
    return a * b
```

#### 3. [cost_list](test/multiprocplus_test2_cost.py)
