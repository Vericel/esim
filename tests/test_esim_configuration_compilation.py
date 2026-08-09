from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from esim.configuration import CompileRequest, ConfigurationCompiler
from esim.errors import ConfigurationError
from esim.model import Flow, IgnoredField, RunRequest


def test_compile_merges_minimal_two_step_rules_tc_and_cli(tmp_path: Path) -> None:
    dv_home = tmp_path / "dv"
    dv_tmp = tmp_path / "runs"
    rules_directory = dv_home / "chip/core/rules"
    tests_directory = dv_home / "chip/core/tests/func"
    tb_directory = dv_home / "chip/core/tb"
    rules_directory.mkdir(parents=True)
    tests_directory.mkdir(parents=True)
    tb_directory.mkdir(parents=True)
    filelist = tb_directory / "top.f"
    filelist.write_text("dut.sv\n", encoding="utf-8")
    (rules_directory / "default.rules").write_text(
        f"""\
description: Default build
tags: [vcs, shared]
filelist: {filelist}
simulator: vcs
flow: two-step
ff:
  args:
    - -d BASE FEATURE
build:
  args:
    - -full64 -sverilog
run:
  args:
    - +BASE_RUN=1
""",
        encoding="utf-8",
    )
    (tests_directory / "smoke.tc").write_text(
        """\
description: Smoke testcase
owner: verification-team
tags: [smoke, shared]
build:
  args:
    - +define+SMOKE
run:
  args:
    - +CASE=smoke
""",
        encoding="utf-8",
    )
    compiler = ConfigurationCompiler(
        environment={"DV_HOME": str(dv_home), "DV_TMP": str(dv_tmp)}
    )
    run_request = RunRequest(
        tc_selector="chip.core:func.smoke",
        build_args=("-debug_access+all",),
        run_args=("+SEED=7",),
    )
    located = compiler.locate(run_request)

    compiled = compiler.compile(
        CompileRequest(located=located, run_request=run_request)
    )

    assert compiled.resolved_rules.name == "default"
    assert compiled.resolved_rules.description == "Default build"
    assert compiled.resolved_rules.tags == ("vcs", "shared")
    assert compiled.resolved_rules.filelist == filelist
    assert compiled.resolved_rules.simulator == "vcs"
    assert compiled.resolved_rules.flow is Flow.TWO_STEP
    assert compiled.resolved_rules.ff.predefined_macros == frozenset(
        {"BASE", "FEATURE"}
    )
    assert compiled.resolved_rules.build.argv == ("-full64", "-sverilog")
    assert compiled.resolved_rules.run.argv == ("+BASE_RUN=1",)
    assert compiled.resolved_rules.merge_order == (located.entry_rules,)

    assert compiled.effective_tc.name == "smoke"
    assert compiled.effective_tc.description == "Smoke testcase"
    assert compiled.effective_tc.owner == "verification-team"
    assert compiled.effective_tc.tags == ("vcs", "shared", "smoke")
    assert compiled.effective_tc.filelist == filelist
    assert compiled.effective_tc.build.argv == (
        "-full64",
        "-sverilog",
        "+define+SMOKE",
        "-debug_access+all",
    )
    assert compiled.effective_tc.run.argv == (
        "+BASE_RUN=1",
        "+CASE=smoke",
        "+SEED=7",
    )
    assert compiled.effective_tc.merge_order == (
        located.entry_rules,
        located.entry_tc,
    )
    assert compiled.ignored_fields == ()


def test_compile_expands_rules_and_tc_include_graphs_in_global_order(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    compiler = ConfigurationCompiler(
        environment={"DV_HOME": str(dv_home), "DV_TMP": str(tmp_path / "runs")}
    )
    run_request = RunRequest(
        tc_selector="xxx.yyy:func.smoke",
        run_args=("+CLI=1",),
    )
    located = compiler.locate(run_request)

    compiled = compiler.compile(
        CompileRequest(located=located, run_request=run_request)
    )

    common_rules = dv_home / "dtb_common/rules"
    local_rules = dv_home / "xxx/yyy/rules"
    tests_directory = dv_home / "xxx/yyy/tests"
    assert compiled.resolved_rules.merge_order == (
        common_rules / "vcs_base.rules",
        local_rules / "default.yaml",
    )
    assert compiled.effective_tc.merge_order == (
        common_rules / "vcs_base.rules",
        local_rules / "default.yaml",
        tests_directory / "base.yaml",
        tests_directory / "func/smoke.yaml",
    )
    assert compiled.resolved_rules.description == (
        "Default two-step VCS rules for the xxx.yyy demo"
    )
    assert compiled.effective_tc.description == (
        "Two-step YAML smoke testcase for xxx.yyy"
    )
    assert compiled.effective_tc.owner == "verification-team"
    assert compiled.effective_tc.tags == (
        "vcs",
        "two-step",
        "base",
        "smoke",
        "func",
        "yaml",
    )
    assert compiled.effective_tc.filelist == dv_home / "xxx/yyy/tb/top.f"
    assert compiled.effective_tc.ff.predefined_macros == frozenset(
        {"ESIM_DEMO", "ESIM_YYY"}
    )
    assert compiled.effective_tc.build.argv == (
        "-full64",
        "-sverilog",
        "-top",
        "top_tb",
    )
    assert compiled.effective_tc.run.argv == (
        "+UVM_VERBOSITY=UVM_LOW",
        "+ntb_random_seed=1",
        "+ESIM_DEMO_DTB=yyy",
        "+ESIM_DEMO_BASE=yyy",
        "+ESIM_DEMO_CASE=smoke",
        "+CLI=1",
    )
    assert compiled.effective_tc.ff.hooks.before is not None
    assert compiled.effective_tc.ff.hooks.before.commands == (
        "source $DV_HOME/dtb_common/env/common_setup.sh && "
        'echo "common ff setup complete"',
    )
    assert compiled.effective_tc.run.hooks.before is not None
    assert compiled.effective_tc.run.hooks.before.commands == (
        "source $DV_HOME/dtb_common/env/common_setup.sh && "
        'echo "xxx.yyy base testcase setup complete"',
        "source $DV_HOME/xxx/yyy/env/setup.sh && "
        'echo "xxx.yyy smoke testcase setup complete"',
    )


def test_compile_maps_three_step_build_and_elaborate_cli_arguments(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    compiler = ConfigurationCompiler(
        environment={"DV_HOME": str(dv_home), "DV_TMP": str(tmp_path / "runs")}
    )
    run_request = RunRequest(
        tc_selector="xxx.zzz:func.smoke",
        build_args=("-notice",),
        elaborate_args=("-debug_access+all",),
    )
    located = compiler.locate(run_request)

    compiled = compiler.compile(
        CompileRequest(located=located, run_request=run_request)
    )

    assert compiled.effective_tc.flow is Flow.THREE_STEP
    assert compiled.effective_tc.build.args == ()
    assert compiled.effective_tc.build.argv == ()
    assert compiled.effective_tc.build.analyze is not None
    assert compiled.effective_tc.build.analyze.argv == (
        "-full64",
        "-sverilog",
        "-notice",
    )
    assert compiled.effective_tc.build.elaborate is not None
    assert compiled.effective_tc.build.elaborate.argv == (
        "-full64",
        "top_tb",
        "-debug_access+all",
    )
    assert compiled.resolved_rules.build.analyze is not None
    assert compiled.resolved_rules.build.analyze.argv == ("-full64", "-sverilog")
    assert compiled.resolved_rules.build.elaborate is not None
    assert compiled.resolved_rules.build.elaborate.argv == ("-full64", "top_tb")


def test_complete_yaml_demo_composes_every_configuration_layer(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    yyy_home = dv_home / "xxx/yyy"
    environment = {
        "DV_HOME": str(dv_home),
        "DV_TMP": str(tmp_path / "runs"),
        "ESIM_DEMO_CONFIG_ROOT": str(yyy_home),
        "ESIM_DEMO_YYY_RULES": "$ESIM_DEMO_CONFIG_ROOT/rules",
        "ESIM_DEMO_YYY_TESTS": "${ESIM_DEMO_CONFIG_ROOT}/tests",
        "ESIM_DEMO_FILELIST": "$ESIM_DEMO_CONFIG_ROOT/tb/top.f",
        "ESIM_DEMO_LABEL": "alpha beta",
        "ESIM_DEMO_SEED": "23",
    }
    compiler = ConfigurationCompiler(environment=environment)
    request = RunRequest(
        tc_selector="xxx.yyy:features.complete",
        rules_selector="full",
        build_args=("-debug_access+all",),
        run_args=("+CLI=1",),
    )

    compiled = compiler.compile(
        CompileRequest(located=compiler.locate(request), run_request=request)
    )

    common_rules = dv_home / "dtb_common/rules/vcs_base.rules"
    rules = yyy_home / "rules"
    tests_directory = yyy_home / "tests"
    shared = tests_directory / "fragments/shared.yaml"
    assert compiled.resolved_rules.merge_order == (
        common_rules,
        shared,
        rules / "full-left.rules",
        rules / "full-right.yaml",
        rules / "full.yaml",
    )
    assert compiled.effective_tc.merge_order == (
        *compiled.resolved_rules.merge_order,
        tests_directory / "fragments/base.yaml",
        tests_directory / "fragments/extended.tc",
        tests_directory / "features/complete.yaml",
    )
    assert compiled.effective_tc.description == (
        "Complete YAML feature testcase for xxx.yyy"
    )
    assert compiled.effective_tc.owner == "verification-platform"
    assert compiled.effective_tc.tags == (
        "vcs",
        "shared-leaf",
        "duplicate",
        "left",
        "right",
        "complete-rules",
        "base",
        "extended",
        "complete-tc",
    )
    assert compiled.effective_tc.filelist == yyy_home / "tb/top.f"
    assert compiled.effective_tc.ff.predefined_macros == frozenset(
        {
            "COMPLETE_LEAF",
            "COMPLETE_LEFT",
            "COMPLETE_RIGHT",
            "COMPLETE_YYY",
        }
    )
    assert compiled.effective_tc.build.argv == (
        "-full64",
        "-sverilog",
        "-top",
        "top_tb",
        "+define+BASE_TC",
        "+define+EXTENDED_TC",
        "+define+COMPLETE_TC",
        "-debug_access+all",
    )
    assert compiled.effective_tc.run.argv == (
        "+UVM_VERBOSITY=UVM_LOW",
        "+SHARED_LEAF=1",
        "+RULES_LABEL=alpha beta",
        "+BASE_TC=1",
        "+FEATURE_LABEL=alpha beta",
        "+FEATURE_SCOPE=$unit",
        "+ntb_random_seed=23",
        "+ESIM_DEMO_CASE=complete",
        "+CLI=1",
    )
    build_before = compiled.effective_tc.build.hooks.before
    assert build_before is not None
    assert build_before.commands == (
        'echo "yyy rules-left build before"',
        'echo "yyy rules-entry build before"',
        'echo "yyy testcase-base build before"',
    )
    assert build_before.continue_on_error is False
    assert compiled.effective_tc.ff.hooks.before is not None
    assert compiled.effective_tc.ff.hooks.after is not None
    assert compiled.effective_tc.build.hooks.after is not None
    assert compiled.effective_tc.run.hooks.before is not None
    assert compiled.effective_tc.run.hooks.after is not None
    assert set(compiled.ignored_fields) == {
        IgnoredField(source=rules / "full.yaml", path="metadata"),
        IgnoredField(source=rules / "full.yaml", path="ff.timeout"),
        IgnoredField(
            source=tests_directory / "features/complete.yaml",
            path="metadata",
        ),
        IgnoredField(
            source=tests_directory / "features/complete.yaml",
            path="run.enabled",
        ),
    }
    assert [
        (diagnostic.source, diagnostic.include_chain)
        for diagnostic in compiled.diagnostics
    ] == [
        (
            shared,
            (rules / "full.yaml", rules / "full-right.yaml", shared),
        ),
        (
            shared,
            (
                tests_directory / "features/complete.yaml",
                tests_directory / "fragments/base.yaml",
                shared,
            ),
        ),
        (
            shared,
            (
                tests_directory / "features/complete.yaml",
                tests_directory / "fragments/extended.tc",
                shared,
            ),
        ),
    ]


def test_compile_ignores_unknown_fields_and_records_their_source_paths(
    tmp_path: Path,
) -> None:
    dv_home = tmp_path / "dv"
    rules_directory = dv_home / "chip/core/rules"
    tests_directory = dv_home / "chip/core/tests"
    tb_directory = dv_home / "chip/core/tb"
    rules_directory.mkdir(parents=True)
    tests_directory.mkdir(parents=True)
    tb_directory.mkdir(parents=True)
    filelist = tb_directory / "top.f"
    filelist.write_text("dut.sv\n", encoding="utf-8")
    entry_rules = rules_directory / "default.rules"
    entry_rules.write_text(
        f"""\
name: ignored-source-name
filelist: {filelist}
simulator: vcs
flow: two-step
ff:
  timeout: 10
  hooks:
    before:
      commands: []
      enabled: true
build:
  args: []
""",
        encoding="utf-8",
    )
    entry_tc = tests_directory / "smoke.tc"
    entry_tc.write_text(
        """\
metadata:
  arbitrary: value
run:
  args: []
  cwd: /ignored
""",
        encoding="utf-8",
    )
    compiler = ConfigurationCompiler(
        environment={"DV_HOME": str(dv_home), "DV_TMP": str(tmp_path / "runs")}
    )
    request = RunRequest(tc_selector="chip.core:smoke")

    compiled = compiler.compile(
        CompileRequest(located=compiler.locate(request), run_request=request)
    )

    assert compiled.ignored_fields == (
        IgnoredField(source=entry_rules, path="name"),
        IgnoredField(source=entry_rules, path="ff.timeout"),
        IgnoredField(source=entry_rules, path="ff.hooks.before.enabled"),
        IgnoredField(source=entry_tc, path="metadata"),
        IgnoredField(source=entry_tc, path="run.cwd"),
    )


def test_phase_args_split_before_recursive_environment_expansion_and_dollar_escape(
    tmp_path: Path,
) -> None:
    dv_home = tmp_path / "dv"
    rules_directory = dv_home / "chip/core/rules"
    tests_directory = dv_home / "chip/core/tests"
    tb_directory = dv_home / "chip/core/tb"
    rules_directory.mkdir(parents=True)
    tests_directory.mkdir(parents=True)
    tb_directory.mkdir(parents=True)
    filelist = tb_directory / "top.f"
    filelist.write_text("dut.sv\n", encoding="utf-8")
    (rules_directory / "default.rules").write_text(
        f"""\
filelist: {filelist}
simulator: vcs
flow: two-step
build:
  args:
    - '-P "$BUILD_VALUE" $$unit'
run:
  hooks:
    before:
      commands:
        - echo $BUILD_VALUE $$unit
""",
        encoding="utf-8",
    )
    (tests_directory / "smoke.tc").write_text("{}\n", encoding="utf-8")
    compiler = ConfigurationCompiler(
        environment={
            "DV_HOME": str(dv_home),
            "DV_TMP": str(tmp_path / "runs"),
            "BUILD_VALUE": "$INNER_VALUE",
            "INNER_VALUE": "alpha beta",
        }
    )
    request = RunRequest(tc_selector="chip.core:smoke")

    compiled = compiler.compile(
        CompileRequest(located=compiler.locate(request), run_request=request)
    )

    assert compiled.effective_tc.build.argv == (
        "-P",
        "alpha beta",
        "$unit",
    )
    assert compiled.effective_tc.run.hooks.before is not None
    assert compiled.effective_tc.run.hooks.before.commands == (
        "echo $BUILD_VALUE $$unit",
    )


def test_hook_continue_on_error_is_inherited_until_explicitly_overridden(
    tmp_path: Path,
) -> None:
    dv_home = tmp_path / "dv"
    rules_directory = dv_home / "chip/core/rules"
    tests_directory = dv_home / "chip/core/tests"
    tb_directory = dv_home / "chip/core/tb"
    rules_directory.mkdir(parents=True)
    tests_directory.mkdir(parents=True)
    tb_directory.mkdir(parents=True)
    filelist = tb_directory / "top.f"
    filelist.write_text("dut.sv\n", encoding="utf-8")
    (rules_directory / "base.rules").write_text(
        f"""\
filelist: {filelist}
simulator: vcs
flow: two-step
build:
  hooks:
    before:
      commands: [echo base]
      continue_on_error: true
""",
        encoding="utf-8",
    )
    (rules_directory / "default.rules").write_text(
        """\
include: [./base.rules]
build:
  hooks:
    before:
      commands: [echo entry]
""",
        encoding="utf-8",
    )
    (tests_directory / "smoke.tc").write_text("{}\n", encoding="utf-8")
    compiler = ConfigurationCompiler(
        environment={"DV_HOME": str(dv_home), "DV_TMP": str(tmp_path / "runs")}
    )
    request = RunRequest(tc_selector="chip.core:smoke")

    compiled = compiler.compile(
        CompileRequest(located=compiler.locate(request), run_request=request)
    )

    before = compiled.effective_tc.build.hooks.before
    assert before is not None
    assert before.commands == ("echo base", "echo entry")
    assert before.continue_on_error is True


@pytest.mark.parametrize("spelling", ["yes", "no", "True", "FALSE"])
def test_continue_on_error_rejects_noncanonical_yaml_boolean_spelling(
    tmp_path: Path,
    spelling: str,
) -> None:
    dv_home = tmp_path / "dv"
    rules_directory = dv_home / "chip/core/rules"
    tests_directory = dv_home / "chip/core/tests"
    tb_directory = dv_home / "chip/core/tb"
    rules_directory.mkdir(parents=True)
    tests_directory.mkdir(parents=True)
    tb_directory.mkdir(parents=True)
    filelist = tb_directory / "top.f"
    filelist.write_text("dut.sv\n", encoding="utf-8")
    (rules_directory / "default.rules").write_text(
        f"""\
filelist: {filelist}
simulator: vcs
flow: two-step
build:
  hooks:
    before:
      commands: [echo build]
      continue_on_error: {spelling}
""",
        encoding="utf-8",
    )
    (tests_directory / "smoke.tc").write_text("{}\n", encoding="utf-8")
    compiler = ConfigurationCompiler(
        environment={"DV_HOME": str(dv_home), "DV_TMP": str(tmp_path / "runs")}
    )
    request = RunRequest(tc_selector="chip.core:smoke")

    with pytest.raises(ConfigurationError, match="lowercase true or false"):
        compiler.compile(
            CompileRequest(located=compiler.locate(request), run_request=request)
        )


def test_compile_renders_resolved_rules_and_effective_tc_snapshots(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    compiler = ConfigurationCompiler(
        environment={"DV_HOME": str(dv_home), "DV_TMP": str(tmp_path / "runs")}
    )
    request = RunRequest(
        tc_selector="xxx.yyy:func.smoke",
        run_args=("+CLI=1",),
    )
    located = compiler.locate(request)

    compiled = compiler.compile(CompileRequest(located=located, run_request=request))
    rules_snapshot = yaml.safe_load(compiled.rules_yaml)
    tc_snapshot = yaml.safe_load(compiled.tc_yaml)

    assert rules_snapshot["name"] == "default"
    assert rules_snapshot["filelist"] == str(dv_home / "xxx/yyy/tb/top.f")
    assert rules_snapshot["source"] == {
        "entry": str(located.entry_rules),
        "merge_order": [str(path) for path in compiled.resolved_rules.merge_order],
    }
    assert "include" not in rules_snapshot
    assert tc_snapshot["name"] == "smoke"
    assert tc_snapshot["owner"] == "verification-team"
    assert tc_snapshot["run"]["args"] == [
        "+UVM_VERBOSITY=UVM_LOW",
        "+ntb_random_seed=1",
        "+ESIM_DEMO_DTB=yyy",
        "+ESIM_DEMO_BASE=yyy",
        "+ESIM_DEMO_CASE=smoke",
        "+CLI=1",
    ]
    assert tc_snapshot["source"] == {
        "entry_tc": str(located.entry_tc),
        "entry_rules": str(located.entry_rules),
        "merge_order": [str(path) for path in compiled.effective_tc.merge_order],
    }
    assert "include" not in tc_snapshot


@pytest.mark.parametrize(
    ("yaml_fragment", "field"),
    [
        ("run: null", "run"),
        ("run:\n  hooks: null", "run.hooks"),
        ("run:\n  hooks:\n    before: null", "run.hooks.before"),
    ],
)
def test_compile_rejects_explicit_null_structural_mapping(
    tmp_path: Path,
    yaml_fragment: str,
    field: str,
) -> None:
    dv_home = tmp_path / "dv"
    rules_directory = dv_home / "chip/core/rules"
    tests_directory = dv_home / "chip/core/tests"
    tb_directory = dv_home / "chip/core/tb"
    rules_directory.mkdir(parents=True)
    tests_directory.mkdir(parents=True)
    tb_directory.mkdir(parents=True)
    filelist = tb_directory / "top.f"
    filelist.write_text("dut.sv\n", encoding="utf-8")
    (rules_directory / "default.rules").write_text(
        f"""\
filelist: {filelist}
simulator: vcs
flow: two-step
{yaml_fragment}
""",
        encoding="utf-8",
    )
    (tests_directory / "smoke.tc").write_text("{}\n", encoding="utf-8")
    compiler = ConfigurationCompiler(
        environment={"DV_HOME": str(dv_home), "DV_TMP": str(tmp_path / "runs")}
    )
    request = RunRequest(tc_selector="chip.core:smoke")

    with pytest.raises(ConfigurationError, match=f"field: {field}"):
        compiler.compile(
            CompileRequest(located=compiler.locate(request), run_request=request)
        )


def test_duplicate_filelists_report_every_source_and_include_chain(
    tmp_path: Path,
) -> None:
    dv_home = tmp_path / "dv"
    rules_directory = dv_home / "chip/core/rules"
    tests_directory = dv_home / "chip/core/tests"
    tb_directory = dv_home / "chip/core/tb"
    rules_directory.mkdir(parents=True)
    tests_directory.mkdir(parents=True)
    tb_directory.mkdir(parents=True)
    first_filelist = tb_directory / "first.f"
    second_filelist = tb_directory / "second.f"
    first_filelist.write_text("first.sv\n", encoding="utf-8")
    second_filelist.write_text("second.sv\n", encoding="utf-8")
    base_rules = rules_directory / "base.rules"
    base_rules.write_text(
        f"filelist: {first_filelist}\nsimulator: vcs\nflow: two-step\n",
        encoding="utf-8",
    )
    entry_rules = rules_directory / "default.rules"
    entry_rules.write_text(
        f"include: [./base.rules]\nfilelist: {second_filelist}\n",
        encoding="utf-8",
    )
    (tests_directory / "smoke.tc").write_text("{}\n", encoding="utf-8")
    compiler = ConfigurationCompiler(
        environment={"DV_HOME": str(dv_home), "DV_TMP": str(tmp_path / "runs")}
    )
    request = RunRequest(tc_selector="chip.core:smoke")

    with pytest.raises(ConfigurationError) as captured:
        compiler.compile(
            CompileRequest(located=compiler.locate(request), run_request=request)
        )

    message = str(captured.value)
    assert f"source: {base_rules}" in message
    assert f"filelist: {first_filelist}" in message
    assert f"include chain: {entry_rules} -> {base_rules}" in message
    assert f"source: {entry_rules}" in message
    assert f"filelist: {second_filelist}" in message
    assert f"include chain: {entry_rules}" in message


@pytest.mark.parametrize("tc_content", ["", "null\n"])
def test_compile_rejects_tc_without_a_top_level_mapping(
    tmp_path: Path,
    tc_content: str,
) -> None:
    dv_home = tmp_path / "dv"
    rules_directory = dv_home / "chip/core/rules"
    tests_directory = dv_home / "chip/core/tests"
    tb_directory = dv_home / "chip/core/tb"
    rules_directory.mkdir(parents=True)
    tests_directory.mkdir(parents=True)
    tb_directory.mkdir(parents=True)
    filelist = tb_directory / "top.f"
    filelist.write_text("dut.sv\n", encoding="utf-8")
    (rules_directory / "default.rules").write_text(
        f"filelist: {filelist}\nsimulator: vcs\nflow: two-step\n",
        encoding="utf-8",
    )
    (tests_directory / "smoke.tc").write_text(tc_content, encoding="utf-8")
    compiler = ConfigurationCompiler(
        environment={"DV_HOME": str(dv_home), "DV_TMP": str(tmp_path / "runs")}
    )
    request = RunRequest(tc_selector="chip.core:smoke")

    with pytest.raises(ConfigurationError, match="field: <root>"):
        compiler.compile(
            CompileRequest(located=compiler.locate(request), run_request=request)
        )


@pytest.mark.parametrize(
    ("source_role", "field"),
    [
        ("tc", "description"),
        ("tc", "owner"),
        ("rules", "filelist"),
        ("rules", "simulator"),
        ("rules", "flow"),
    ],
)
def test_compile_rejects_explicit_null_string_field(
    tmp_path: Path,
    source_role: str,
    field: str,
) -> None:
    dv_home = tmp_path / "dv"
    rules_directory = dv_home / "chip/core/rules"
    tests_directory = dv_home / "chip/core/tests"
    tb_directory = dv_home / "chip/core/tb"
    rules_directory.mkdir(parents=True)
    tests_directory.mkdir(parents=True)
    tb_directory.mkdir(parents=True)
    filelist = tb_directory / "top.f"
    filelist.write_text("dut.sv\n", encoding="utf-8")
    rules_values = {
        "filelist": str(filelist),
        "simulator": "vcs",
        "flow": "two-step",
    }
    if source_role == "rules":
        rules_values[field] = "null"
    (rules_directory / "default.rules").write_text(
        "".join(f"{key}: {value}\n" for key, value in rules_values.items()),
        encoding="utf-8",
    )
    tc_content = f"{field}: null\n" if source_role == "tc" else "{}\n"
    (tests_directory / "smoke.tc").write_text(tc_content, encoding="utf-8")
    compiler = ConfigurationCompiler(
        environment={"DV_HOME": str(dv_home), "DV_TMP": str(tmp_path / "runs")}
    )
    request = RunRequest(tc_selector="chip.core:smoke")

    with pytest.raises(ConfigurationError, match=f"field: {field}"):
        compiler.compile(
            CompileRequest(located=compiler.locate(request), run_request=request)
        )
