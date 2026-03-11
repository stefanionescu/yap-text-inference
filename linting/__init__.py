"""Repository-local linting packages and helper modules.

Package layout
--------------
repo.py             Repository/config/path helpers shared across linting code.
config/repo/policy.toml
                    Centralised thresholds and path configuration.

python/common.py
                    AST and file helpers used by custom Python lint rules.

python/structure/
                    Code-shape and file-organization rules
    file_length.py              Source files must not exceed the configured line limit.
    function_length.py          Functions must not exceed the configured line limit.
    function_order.py           Private functions must precede public ones.
    one_class_per_file.py       One non-dataclass class per source file.
    all_at_bottom.py            __all__ must be the last top-level statement.
    single_file_folders.py      Packages with one module should be flattened.
    prefix_collisions.py        No filename prefix collisions in the same directory.

python/imports/
                    Import graph and dependency rules
    import_cycles.py            No import cycles between internal modules.
    single_line_imports_first.py Top-level imports: future first, then
                                 contiguous single-line imports, then multiline.
    no_lazy_module_loading.py   No lazy/dynamic import patterns at runtime.

python/runtime/
                    Runtime module hygiene rules
    no_runtime_singletons.py    No singleton patterns in runtime modules.
    no_legacy_markers.py        No legacy/compatibility markers in runtime code.
    no_inline_python.py         Shell scripts must not embed inline Python.

python/modules/
                    Config-module purity rules
    no_config_functions.py      Config modules must be purely declarative.
    no_config_cross_imports.py  Config modules must not import siblings.

python/testing/
                    Test file placement and naming rules
    function_placement.py       Test functions only in unit/ and integration/.
    unit_test_domain_folders.py Unit tests must live in domain subfolders.
    file_prefix.py              Test filenames must use the test_ prefix.
    no_conftest_in_subfolders.py Only one conftest.py allowed (tests root).

python/infra/
                    Build and repository policy rules
    dockerignore_policy.py      Docker ignore files must match linting/config/repo/policy.toml.

licenses/           License policy audit
    audit.py                    Checks repo dependency licenses against local policy.
"""
