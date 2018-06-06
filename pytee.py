import os
import sys

class Pytee(object):
    def __init__(self, filename):
        self.filename = filename

    def start(self):
        self.old_stdout = os.dup(sys.stdout.fileno())
        self.old_stderr = os.dup(sys.stderr.fileno())

        self.pipe_read, self.pipe_write = os.pipe()
        self.pid = os.fork()
        if self.pid == 0:
            # Child
            os.close(self.pipe_write)

            file_read = os.fdopen(self.pipe_read)

            with open(self.filename, 'w') as file_log:
                for content in file_read:
                    print(content, end='')
                    print(content, end='', file=file_log)

                file_log.flush()
                os.fsync(file_log.fileno())

            os._exit(255)
        else:
            # Parent
            os.close(self.pipe_read)
            os.dup2(self.pipe_write, sys.stdout.fileno())
            os.dup2(self.pipe_write, sys.stderr.fileno())

    def end(self):

        try:
            os.close(self.pipe_write)
        except OSError:
            pass

        os.dup2(self.old_stdout, sys.stdout.fileno())
        os.dup2(self.old_stderr, sys.stderr.fileno())
        os.waitpid(self.pid, 0)
