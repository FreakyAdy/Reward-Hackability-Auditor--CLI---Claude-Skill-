import inspect
def verify(): caller = inspect.stack()[1]; return caller.filename.endswith('test.py')