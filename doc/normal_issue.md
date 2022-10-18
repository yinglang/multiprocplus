# Error Usage

## Error code example

- multiprocess_run must be called in a function called under 'if __name__ == "__main__"'
     
```shell
from multiprocplus import multiprocess_for, MultiprocessRunner


def func(a, b):
    return a * b


N = 100
A, B = list(range(N)), list(range(N))

# => run in single process
C = [func(a, b) for a, b in zip(A, B)]
print(sum(C))
# => run in multiprocess
C = multiprocess_for(func, [(a, b) for a, b in zip(A, B)], num_process=3)
print(sum(C))
```


```shell
from multiprocplus import multiprocess_for, MultiprocessRunner


def func(a, b):
    return a * b


N = 100
A, B = list(range(N)), list(range(N))

# => run in single process
C = [func(a, b) for a, b in zip(A, B)]
print(sum(C))
# => run in multiprocess
C = multiprocess_for(func, [(a, b) for a, b in zip(A, B)], num_process=3)
print(sum(C))
```