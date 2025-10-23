import re

from pathlib import Path
from setuptools import setup, find_packages

HERE = Path(__file__).parent

README = (HERE / "README.md").read_text(encoding="utf-8") if (HERE / "README.md").exists() else ""

def read_version(package: str = "hapiserver") -> str:
  init_py = HERE / package / "__init__.py"
  if not init_py.exists():
    return "0.0.0"
  content = init_py.read_text(encoding="utf-8")
  m = re.search(r"^__version__\s*=\s*['\"]([^'\"]+)['\"]", content, re.M)
  return m.group(1) if m else "0.0.0"

setup(
  name="hapiserver",
  version=read_version("hapiserver"),
  description="Generic HAPI server implementation in Python",
  long_description=README,
  long_description_content_type="text/markdown" if README else None,
  author="",
  url="https://github.com/hapi-server/server-python-generic",
  license="MIT",
  packages=find_packages(exclude=("tests", "docs")),
  include_package_data=True,
  python_requires=">=3.8",
  install_requires=["fastapi>=0.97", "uvicorn>=0.22"],
  extras_require={
    "dev": ["pytest", "check-manifest"],
  },
  classifiers=[
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
  ]
)
