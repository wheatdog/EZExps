# Expsboost

A Hackable (deep learning) experiments helper scripts

## Helper scripts

- `ezexps/exps.py`
- `ezexps/gsheet_uploader.py`
- `ezexps/local_dependency.py`

## Example

```
(t5) ytliou@ubuntu:~/4tb/expsboost$ pwd
/home/ytliou/4tb/expsboost
(t5) ytliou@ubuntu:~/4tb/expsboost$ python ezexps/
exps.py              gsheet_uploader.py   local_dependency.py  __pycache__/
(t5) ytliou@ubuntu:~/4tb/expsboost$ python ezexps/exps.py --epochs 1
```

## Todo

- A task queuer: will check if gpu is available and assign experiments
- A daemon validation tool
