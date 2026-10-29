GMOS-LIA
========

Lab automation (``ate_lia/``), LIA readout board (``schematics/LIA-Readout/``),
simulations (``simulations/``) and thesis (``thesis/``) for the GMOS gas sensor.

Installation (Python lab automation)
------------------------------------

Create the virtual environment in the repository root, then install the package
and its dependencies from ``pyproject.toml``::

    python -m venv .venv
    .venv/bin/pip install -e ".[lint,typecheck]"   # extras add ruff and pyright

See ``ate_lia/CLAUDE.md`` and ``ate_lia/FSD.md`` for usage.
