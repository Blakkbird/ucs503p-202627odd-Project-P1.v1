# Week 1 : Local Documentation Build Fails on a Fresh Clone

# Hard-coded Toolchain Paths in the Template Makefile


First week was introduction, so the only work
was setting up. After forking the template and cloning it


## Relevant Context

The template `Makefile` fixes its shell and Python environment at
the top:

``` makefile
SHELL           := /usr/bin/zsh
ENV             := emacs
CONDA_ROOT      := ~/miniconda3
```

That assumes `zsh` at a specific path, Anaconda at `~/miniconda3`,
and a conda environment named `emacs` holding `mkdocs`. None of
the three exists on a clean machine.

## Key Observation

Two build configurations live in this repository and only one is
a contract.

+  `.github/workflows/mkdocs.yml` installs its dependencies
   explicitly into a fresh runner, so it is reproducible by
   necessity.
+  The `Makefile` targets one developer's machine and is a
   convenience.

The real dependency list is therefore in the workflow file.

## Solution

Reproduce the CI environment locally and skip the `Makefile` for
this target:

``` shell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-docs.txt
mkdocs serve
```

`requirements-docs.txt` is transcribed from the workflow and
committed, so all three of us install the same set. `.venv/` is
gitignored. The `Makefile` is left untouched.

**Because**

Deriving the local environment from the CI specification keeps
the two from drifting. If docs build locally but fail in CI, that
difference is now a real signal rather than noise.

Leaving the `Makefile` alone matters separately: two report
templates are still to be published upstream and will arrive by
syncing the fork, so every file we edit unnecessarily is a file
that can conflict later.
