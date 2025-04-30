Notes about pytest commands for testing


python -m pytest --html=report.html tests/
This will create a report.html file with detailed test results.

To see more verbose output, use the -v or -vv flag:
python -m pytest -v tests/
This will show each test function name and its result.

For even more detail, including print statements and full test names, use:
python -m pytest -vv tests/

To see print statements even for passing tests, use the -s flag:
python -m pytest -vv -s tests/

To see the test data that was compared in assertions, add the -l flag:
python -m pytest -vv -l tests/

You can also add print statements in your tests to see the actual data. Here's how you could modify your test files:
python -m pytest -vv -s tests/


For a full report of all test details, you can generate an HTML report using pytest-html:
First install it:

pip install pytest-html

Then run:
python -m pytest --html=report.html tests/

