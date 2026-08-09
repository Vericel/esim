from pathlib import Path

import pytest

from esim.errors import WaiverError
from esim.log_policy import LogEvaluationRequest, LogPolicy, WaiverSources

DEMO_DV = Path(__file__).parent / "fixtures/esim-demo-project/dv"


def test_waivers_merge_common_then_entry_rules_and_render_source_blocks(
    tmp_path: Path,
) -> None:
    common_rules = tmp_path / "dv/dtb_common/rules"
    entry_rules = tmp_path / "dv/xxx/yyy/rules"
    common_rules.mkdir(parents=True)
    entry_rules.mkdir(parents=True)
    (common_rules / "waive.txt").write_text(
        "// common comment\n*UVM_ERROR : 0*\n\n",
        encoding="utf-8",
    )
    (common_rules / "exclude.txt").write_text(
        "# no common regex yet\n",
        encoding="utf-8",
    )
    (entry_rules / "waive.txt").write_text(
        " *EXPECTED_ERROR* \n",
        encoding="utf-8",
    )
    (entry_rules / "exclude.txt").write_text(
        "^known_error: waived$\n",
        encoding="utf-8",
    )

    compiled = LogPolicy().compile(
        WaiverSources(
            common_rules_directory=common_rules,
            entry_rules_directory=entry_rules,
        )
    )

    assert compiled.rendered_waive == (
        f"// source: {common_rules / 'waive.txt'}\n"
        "*UVM_ERROR : 0*\n"
        f"// source: {entry_rules / 'waive.txt'}\n"
        "*EXPECTED_ERROR*\n"
    )
    assert compiled.rendered_exclude == (
        f"// source: {entry_rules / 'exclude.txt'}\n^known_error: waived$\n"
    )


def test_log_evaluation_finds_substrings_inside_words_and_applies_both_waivers(
    tmp_path: Path,
) -> None:
    common_rules = tmp_path / "dv/dtb_common/rules"
    entry_rules = tmp_path / "dv/xxx/yyy/rules"
    common_rules.mkdir(parents=True)
    entry_rules.mkdir(parents=True)
    (common_rules / "waive.txt").write_text(
        "*UVM_ERROR : 0*\n",
        encoding="utf-8",
    )
    (entry_rules / "exclude.txt").write_text(
        "^known_error: waived$\n",
        encoding="utf-8",
    )
    log = tmp_path / "simv.log"
    log.write_text(
        "failover enabled\nUVM_ERROR : 0\nknown_error: waived\nsimulation complete\n",
        encoding="utf-8",
    )
    policy = LogPolicy()
    waivers = policy.compile(
        WaiverSources(
            common_rules_directory=common_rules,
            entry_rules_directory=entry_rules,
        )
    )

    evaluation = policy.evaluate(
        LogEvaluationRequest(
            phase="run",
            log_path=log,
            waivers=waivers,
        )
    )

    assert [finding.text for finding in evaluation.findings] == [
        "failover enabled",
        "UVM_ERROR : 0",
        "known_error: waived",
    ]
    assert [finding.reasons for finding in evaluation.findings] == [
        ("generic:fail",),
        ("generic:error",),
        ("generic:error",),
    ]
    assert [finding.waived for finding in evaluation.findings] == [
        False,
        True,
        True,
    ]
    assert evaluation.passed is False


def test_demo_waives_known_y2026_license_fallback_codes(tmp_path: Path) -> None:
    log = tmp_path / "vcs.log"
    log.write_text(
        "FlexNet Licensing error:-5,147\nFlexNet Licensing error:-5,357\n",
        encoding="utf-8",
    )
    policy = LogPolicy()
    waivers = policy.compile(
        WaiverSources(
            common_rules_directory=DEMO_DV / "dtb_common/rules",
            entry_rules_directory=DEMO_DV / "xxx/yyy/rules",
        )
    )

    evaluation = policy.evaluate(
        LogEvaluationRequest(
            phase="build",
            log_path=log,
            waivers=waivers,
        )
    )

    assert [finding.text for finding in evaluation.findings] == [
        "FlexNet Licensing error:-5,147",
        "FlexNet Licensing error:-5,357",
    ]
    assert all(finding.waived for finding in evaluation.findings)
    assert evaluation.passed is True


def test_all_invalid_regex_waivers_are_reported_before_execution(
    tmp_path: Path,
) -> None:
    common_rules = tmp_path / "dv/dtb_common/rules"
    entry_rules = tmp_path / "dv/xxx/yyy/rules"
    common_rules.mkdir(parents=True)
    entry_rules.mkdir(parents=True)
    common_exclude = common_rules / "exclude.txt"
    entry_exclude = entry_rules / "exclude.txt"
    common_exclude.write_text("[\n", encoding="utf-8")
    entry_exclude.write_text("# comment\n(?P<\n", encoding="utf-8")

    with pytest.raises(WaiverError) as captured:
        LogPolicy().compile(
            WaiverSources(
                common_rules_directory=common_rules,
                entry_rules_directory=entry_rules,
            )
        )

    message = str(captured.value)
    assert "invalid waiver patterns" in message
    assert f"{common_exclude}:1" in message
    assert "  pattern: [" in message
    assert f"{entry_exclude}:2" in message
    assert "  pattern: (?P<" in message


def test_invalid_glob_and_regex_waivers_are_reported_together(
    tmp_path: Path,
) -> None:
    common_rules = tmp_path / "dv/dtb_common/rules"
    entry_rules = tmp_path / "dv/xxx/yyy/rules"
    common_rules.mkdir(parents=True)
    entry_rules.mkdir(parents=True)
    common_waive = common_rules / "waive.txt"
    entry_exclude = entry_rules / "exclude.txt"
    common_waive.write_text("*[unterminated\n", encoding="utf-8")
    entry_exclude.write_text("(?P<\n", encoding="utf-8")

    with pytest.raises(WaiverError) as captured:
        LogPolicy().compile(
            WaiverSources(
                common_rules_directory=common_rules,
                entry_rules_directory=entry_rules,
            )
        )

    message = str(captured.value)
    assert f"{common_waive}:1" in message
    assert "  pattern: *[unterminated" in message
    assert "unterminated character class" in message
    assert f"{entry_exclude}:1" in message
    assert "  pattern: (?P<" in message


def test_existing_unreadable_waiver_source_is_a_controlled_input_error(
    tmp_path: Path,
) -> None:
    common_rules = tmp_path / "dv/dtb_common/rules"
    entry_rules = tmp_path / "dv/xxx/yyy/rules"
    common_rules.mkdir(parents=True)
    entry_rules.mkdir(parents=True)
    unreadable = common_rules / "waive.txt"
    unreadable.write_text("*EXPECTED_ERROR*\n", encoding="utf-8")
    unreadable.chmod(0o000)

    with pytest.raises(WaiverError) as captured:
        LogPolicy().compile(
            WaiverSources(
                common_rules_directory=common_rules,
                entry_rules_directory=entry_rules,
            )
        )

    assert str(captured.value) == (
        f"waiver source is not a readable file\n  source: {unreadable}"
    )
