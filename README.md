# EZExps

A Hackable (deep learning) experiments helper scripts

## Helper scripts

- `exps.py`: A experiment wrapper with only two assumptions
- `gsheet_uploader.py`
- `local_dependency.py`

## Example

```
cd example
python ../exps.py 'lr=0.1 test' main.py --lr 0.1 --epochs 1
```

## Todo

- A task queuer: will check if gpu is available and assign experiments
- A daemon validation tool
