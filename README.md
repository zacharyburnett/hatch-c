# `hatch-c`

[![build](https://github.com/zacharyburnett/hatch-c/actions/workflows/build.yaml/badge.svg?branch=main&event=push)](https://github.com/zacharyburnett/hatch-c/actions/workflows/build.yaml)
[![PyPI](https://img.shields.io/pypi/v/hatch-cpp.svg)](https://pypi.python.org/pypi/hatch-cpp)

Very simple C build plugin for [hatch](https://hatch.pypa.io/latest/), supporting CPython only.

```toml
[build-system]
requires = ["hatchling>=1.20", "hatch-c"]
build-backend = "hatchling.build"

[[tool.hatch.build.hooks.hatch-c.extension]]
name = "mypackage.mylib"
sources = ["src/module.c"]
include-dirs = ["src/"] # paths to add with `-I`
include-numpy = false # add Numpy include paths with `numpy.get_include()`; numpy must be in `build-system.requires`
library-dirs = [] # paths to add with `-L`
libraries = [] # libraries to link with `-l` 
extra-compile-args = []
extra-link-args = []
extra-objects = []
define-macros = [] # macros to define with `-D`
undef-macros = [] # macros to undefine with `-U`
py-limited-api = "cp39"  # optional limited API to use
```

`hatch-c` is driven by [pydantic](https://docs.pydantic.dev/latest/) models for configuration and execution of the build.
These models can themselves be overridden by setting `build-config-class` / `build-plan-class`.

## Other Python Build Backends for C Extensions

- [`hatch-cpp`](https://github.com/python-project-templates/hatch-cpp)
- [`scikit-build-core`](https://github.com/scikit-build/scikit-build-core)
- [`setuptools`](https://setuptools.pypa.io/en/latest/userguide/ext_modules.html)

## Acknowledgments 

This project was heavily modified and stripped down from https://github.com/python-project-templates/hatch-cpp
