from invoke import task

@task
def test(c):
    """ Run the test suit """
    c.run("pytest", pty = True)
@task
def format(c):
    """ Format code with black """
    c.run("black .")

@task
def lint(c):
    """ Lint code with ruff and mypy """
    c.run("ruff check .")
    c.run("mypy src")
    
@task
def all(c):
    """ Run all suit of checks """
    format(c)
    lint(c)
    test(c)