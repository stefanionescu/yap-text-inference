"""Custom structural lint checks for the Orpheus TTS API.

Package layout
--------------
shared.py           Shared helpers (path constants, file iteration, parsing,
                    violation reporting) used by every linter.
policy.toml         Centralised thresholds and path configuration.

structure/          Code-shape and file-organization rules
    file_length.py              Source files must not exceed the configured line limit.
    function_length.py          Functions must not exceed the configured line limit.
    function_order.py           Private functions must precede public ones.
    one_class_per_file.py       One non-dataclass class per source file.
    all_at_bottom.py            __all__ must be the last top-level statement.
    single_file_folders.py      Packages with one module should be flattened.
    prefix_collisions.py        No filename prefix collisions in the same directory.

imports/            Import graph and dependency rules
    import_cycles.py            No import cycles between internal modules.
    no_lazy_module_loading.py   No lazy/dynamic import patterns at runtime.

runtime/            Runtime module hygiene rules
    no_runtime_singletons.py    No singleton patterns in runtime modules.
    no_legacy_markers.py        No legacy/compatibility markers in runtime code.
    no_inline_python.py         Shell scripts must not embed inline Python.

modules/            Config-module purity rules
    no_config_functions.py      Config modules must be purely declarative.
    no_config_cross_imports.py  Config modules must not import siblings.

testing/            Test file placement and naming rules
    test_function_placement.py  Test functions only in unit/ and integration/.
    unit_test_domain_folders.py Unit tests must live in domain subfolders.
    no_test_file_prefix.py      Test filenames must not use the test_ prefix.
    no_conftest_in_subfolders.py Only one conftest.py allowed (tests root).

infra/              Build and deploy policy rules
    dockerignore_policy.py      Docker ignore files must match linting/policy.toml.
"""
