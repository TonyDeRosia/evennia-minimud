# Contributing

Thank you for your interest in contributing!

## Running the Test Suite

Tests are executed with [`pytest`](https://docs.pytest.org/). They rely on
[Django](https://www.djangoproject.com/) and the [Evennia](https://www.evennia.com/) framework.
If these packages are missing, `pytest` may report "found no collectors" or
similar import errors. Install the required dependencies using the helper
requirements file:

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

