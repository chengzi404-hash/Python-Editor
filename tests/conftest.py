import os
import shutil
import tempfile

import pytest


@pytest.fixture
def temp_dir():
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def sample_python_file(temp_dir):
    path = os.path.join(temp_dir, "sample.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write("def hello():\n    print('Hello, World!')\n")
    return path


@pytest.fixture
def sample_syntax_error_file(temp_dir):
    path = os.path.join(temp_dir, "error.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write("def hello(\n    print('Hello')\n")
    return path


@pytest.fixture
def sample_c_file(temp_dir):
    path = os.path.join(temp_dir, "sample.c")
    with open(path, "w", encoding="utf-8") as f:
        f.write('#include <stdio.h>\n\nint main() {\n    printf("Hello\\n");\n    return 0;\n}\n')
    return path


@pytest.fixture
def sample_cpp_file(temp_dir):
    path = os.path.join(temp_dir, "sample.cpp")
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            '#include <iostream>\n\nint main() {\n    std::cout << "Hello" << std::endl;\n    return 0;\n}\n'
        )
    return path
