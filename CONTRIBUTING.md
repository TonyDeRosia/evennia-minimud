# Contributing

Thank you for your interest in contributing!

## Running the Test Suite

Tests are executed with [`pytest`](https://docs.pytest.org/). They depend on
[Django](https://www.djangoproject.com/) and the [Evennia](https://www.evennia.com/) framework.
A helper requirements file is provided to install compatible versions of these
packages.

```bash
python -m pip install --upgrade pip
pip install -r requirements-test.txt
pip install -e .
```
Running `pytest` before installing these packages will lead to test
collection errors because Django and Evennia cannot be imported.

You can run `scripts/setup_test_env.sh` to perform these commands
automatically. Once everything is installed, run the tests with:

```bash
pytest -q
```

