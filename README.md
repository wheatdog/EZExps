# EZExps

A set of hackable (deep learning) experiments helpers for python scripts

## Features

- Track local dependencies of your experiment script. For reproducibility, it won't run your experiment until those changes are committed via git.
- Store experiment information into MongoDB after finishing.
- Upload experiment information to Google Sheets if you have OAuth2 credentials for Google API.

## Tracked experiment information

- Arguments
- Artifacts
- Purpose
- Source files
- Start/End/Elapsed Time
- Stdout

## Prerequisites

You will need

- Git
- MongoDB ([you can install without root](https://groups.google.com/forum/#!topic/mongodb-user/DUpcIkoAv88))
- Python 3
- (Optional) OAuth Credentials ([tutorial](http://gspread.readthedocs.io/en/latest/oauth2.html))

There are some assumptions for the `.py` we can track.

- Must have a function named `get_args`, which returns an object like `ArgumentParser.parse_args()` returns.
- Must have a function named `main`, which return the experiment artifacts.


## Installation

```
pip install -r requirements.txt
```

Setup `ezexps.ini` for your project, check out [ezexps.ini](example/ezexps.ini).

## Helper scripts

- `exps.py` 
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
