from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from esim import RunRequest
from esim.configuration import CompileRequest, ConfigurationCompiler
from esim.errors import InputError, SelectorError


def test_logical_tc_uses_default_rules_and_derives_simulation_identity(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    dv_tmp = tmp_path / "runs"

    located = ConfigurationCompiler(
        environment={"DV_HOME": str(dv_home), "DV_TMP": str(dv_tmp)}
    ).locate(RunRequest(tc_selector="xxx.yyy:func.smoke"))

    assert located.entry_tc == dv_home / "xxx/yyy/tests/func/smoke.yaml"
    assert located.entry_rules == dv_home / "xxx/yyy/rules/default.yaml"
    assert located.identity.dtb_key == "xxx.yyy"
    assert located.identity.rules_key == "default"
    assert located.identity.test_key == "func.smoke"
    assert located.identity.directory == dv_tmp / "xxx.yyy/default/func.smoke"


def test_logical_tc_supports_traditional_suffixes_and_local_three_step_rules(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    dv_tmp = tmp_path / "runs"

    located = ConfigurationCompiler(
        environment={"DV_HOME": str(dv_home), "DV_TMP": str(dv_tmp)}
    ).locate(RunRequest(tc_selector="xxx.zzz:func.smoke"))

    assert located.entry_tc == dv_home / "xxx/zzz/tests/func/smoke.tc"
    assert located.entry_rules == dv_home / "xxx/zzz/rules/default.rules"
    assert located.identity.dtb_key == "xxx.zzz"
    assert located.identity.rules_key == "default"
    assert located.identity.test_key == "func.smoke"
    assert located.identity.directory == dv_tmp / "xxx.zzz/default/func.smoke"


def test_absolute_tc_and_rules_derive_the_same_simulation_identity(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    dv_tmp = tmp_path / "runs"
    entry_tc = dv_home / "xxx/yyy/tests/func/smoke.yaml"
    entry_rules = dv_home / "xxx/yyy/rules/coverage.yaml"

    located = ConfigurationCompiler(
        environment={"DV_HOME": str(dv_home), "DV_TMP": str(dv_tmp)}
    ).locate(
        RunRequest(
            tc_selector=str(entry_tc),
            rules_selector=str(entry_rules),
        )
    )

    assert located.entry_tc == entry_tc
    assert located.entry_rules == entry_rules
    assert located.identity.dtb_key == "xxx.yyy"
    assert located.identity.rules_key == "coverage"
    assert located.identity.test_key == "func.smoke"
    assert located.identity.directory == dv_tmp / "xxx.yyy/coverage/func.smoke"


def test_logical_rules_fall_back_to_a_runnable_common_configuration(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    dv_tmp = tmp_path / "runs"
    filelist = dv_home / "xxx/yyy/tb/top.f"
    environment = {
        "DV_HOME": str(dv_home),
        "DV_TMP": str(dv_tmp),
        "ESIM_DEMO_COMMON_FILELIST": str(filelist),
    }
    compiler = ConfigurationCompiler(environment=environment)
    request = RunRequest(
        tc_selector="xxx.yyy:func.smoke",
        rules_selector="portable",
    )

    located = compiler.locate(request)
    compiled = compiler.compile(CompileRequest(located=located, run_request=request))

    assert located.entry_rules == dv_home / "dtb_common/rules/portable.yaml"
    assert located.identity.directory == dv_tmp / "xxx.yyy/portable/func.smoke"
    assert compiled.resolved_rules.filelist == filelist
    assert compiled.resolved_rules.tags == ("vcs", "portable", "common-rules")
    assert compiled.resolved_rules.build.argv == (
        "-full64",
        "-sverilog",
        "-top",
        "top_tb",
    )


def test_relative_tc_path_is_rejected_as_an_input_error(tmp_path: Path) -> None:
    with pytest.raises(
        SelectorError,
        match="relative TC paths are not supported",
    ):
        ConfigurationCompiler(
            environment={
                "DV_HOME": str(tmp_path / "dv"),
                "DV_TMP": str(tmp_path / "runs"),
            }
        ).locate(RunRequest(tc_selector="tests/func/smoke.tc"))


def test_missing_logical_tc_reports_the_searched_candidates(tmp_path: Path) -> None:
    dv_home = tmp_path / "dv"

    with pytest.raises(SelectorError) as captured:
        ConfigurationCompiler(
            environment={
                "DV_HOME": str(dv_home),
                "DV_TMP": str(tmp_path / "runs"),
            }
        ).locate(RunRequest(tc_selector="xxx.yyy:func.missing"))

    assert str(captured.value) == (
        "TC selector did not match a readable file\n"
        f"  candidate: {dv_home}/xxx/yyy/tests/func/missing.tc\n"
        f"  candidate: {dv_home}/xxx/yyy/tests/func/missing.yaml"
    )


def test_relative_rules_path_is_rejected_as_an_input_error(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)

    with pytest.raises(
        SelectorError,
        match="relative Rules paths are not supported",
    ):
        ConfigurationCompiler(
            environment={
                "DV_HOME": str(project / "dv"),
                "DV_TMP": str(tmp_path / "runs"),
            }
        ).locate(
            RunRequest(
                tc_selector="xxx.yyy:func.smoke",
                rules_selector="rules/coverage.rules",
            )
        )


def test_absolute_tc_outside_the_tests_tree_is_rejected(tmp_path: Path) -> None:
    dv_home = tmp_path / "dv"
    invalid_tc = dv_home / "xxx/yyy/rules/smoke.tc"
    invalid_tc.parent.mkdir(parents=True)
    invalid_tc.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        SelectorError,
        match="absolute TC must be below DV_HOME/<dtb>/tests",
    ):
        ConfigurationCompiler(
            environment={
                "DV_HOME": str(dv_home),
                "DV_TMP": str(tmp_path / "runs"),
            }
        ).locate(RunRequest(tc_selector=str(invalid_tc)))


def test_absolute_rules_outside_a_rules_directory_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    invalid_rules = dv_home / "xxx/yyy/tests/coverage.rules"
    invalid_rules.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        SelectorError,
        match="absolute Rules must be inside a DV_HOME rules directory",
    ):
        ConfigurationCompiler(
            environment={
                "DV_HOME": str(dv_home),
                "DV_TMP": str(tmp_path / "runs"),
            }
        ).locate(
            RunRequest(
                tc_selector="xxx.yyy:func.smoke",
                rules_selector=str(invalid_rules),
            )
        )


def test_missing_required_environment_is_a_controlled_input_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(InputError, match="required environment variable is not set"):
        ConfigurationCompiler(environment={"DV_HOME": str(tmp_path / "dv")}).locate(
            RunRequest(tc_selector="xxx.yyy:func.smoke")
        )


@pytest.mark.parametrize(
    "selector",
    (
        "xxx/yyy:func.smoke",
        "xxx..yyy:func.smoke",
        "xxx.yyy:func/../../smoke",
        "xxx.yyy:.func.smoke",
        r"xxx\yyy:func.smoke",
    ),
)
def test_logical_tc_rejects_non_dotted_path_segments_before_search(
    tmp_path: Path,
    selector: str,
) -> None:
    with pytest.raises(SelectorError, match="invalid logical TC selector"):
        ConfigurationCompiler(
            environment={
                "DV_HOME": str(tmp_path / "dv"),
                "DV_TMP": str(tmp_path / "runs"),
            }
        ).locate(RunRequest(tc_selector=selector))


@pytest.mark.parametrize("selector", ("cov/erage", r"cov\erage", "coverage.yaml"))
def test_logical_rules_name_rejects_path_syntax(
    tmp_path: Path,
    selector: str,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)

    with pytest.raises(SelectorError, match="invalid logical Rules selector"):
        ConfigurationCompiler(
            environment={
                "DV_HOME": str(project / "dv"),
                "DV_TMP": str(tmp_path / "runs"),
            }
        ).locate(
            RunRequest(
                tc_selector="xxx.yyy:func.smoke",
                rules_selector=selector,
            )
        )
