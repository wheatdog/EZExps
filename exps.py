from sacred import Experiment
from sacred.observers import MongoObserver
from main import main, get_args

NAME='mnist-train'

ex = Experiment(NAME, base_dir='.')
ex.observers.append(MongoObserver.create())

@ex.config
def config():
    args = get_args()

@ex.main
def main_wrapper(args):
    main(args)

if __name__ == '__main__':
    ex.run()
