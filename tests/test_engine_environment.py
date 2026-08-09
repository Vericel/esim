from pathlib import Path

import pytest

DEMO_DV = Path(__file__).parent / "fixtures/esim-demo-project/dv"


def test_demo_nested_error_reports_source_and_environment_chains(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    case_root = DEMO_DV / "xxx/yyy/tb/ff_cases/environment-cycle"
    top = case_root / "top.f"
    middle = case_root / "nested/middle.f"
    leaf = case_root / "nested/leaf.f"

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top,
                working_directory=tmp_path,
                environment={
                    "FF_DEMO_CYCLE_A": "$FF_DEMO_CYCLE_B",
                    "FF_DEMO_CYCLE_B": "${FF_DEMO_CYCLE_A}",
                },
            )
        )

    assert str(caught.value) == (
        "environment variable expansion cycle\n"
        "  source chain:\n"
        f"    {top}:1 -> {middle}\n"
        f"    {middle}:1 -> {leaf}\n"
        f"  at: {leaf}:1\n"
        "  input: $FF_DEMO_CYCLE_A/missing.sv\n"
        "  expansion chain: FF_DEMO_CYCLE_A -> FF_DEMO_CYCLE_B -> "
        "FF_DEMO_CYCLE_A\n"
        "  suggestion: remove the recursive environment variable reference"
    )


@pytest.mark.parametrize(
    "entry",
    ["$PROJ_DIR/rtl/top.sv", "${PROJ_DIR}/rtl/top.sv"],
)
def test_source_path_expands_standard_environment_variable_forms(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entry: str,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    project_directory = tmp_path / "project"
    source = project_directory / "rtl" / "top.sv"
    source.parent.mkdir(parents=True)
    source.write_text("module top; endmodule\n", encoding="utf-8")
    monkeypatch.setenv("PROJ_DIR", str(project_directory))
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(f"{entry}\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{source}\n"


def test_missing_environment_variable_reports_its_name_and_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    monkeypatch.delenv("DV_HOME", raising=False)
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("$DV_HOME/rtl/top.sv\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "environment variable is not set\n"
        f"  at: {top_filelist}:1\n"
        "  input: $DV_HOME/rtl/top.sv\n"
        "  variable: DV_HOME\n"
        "  suggestion: export DV_HOME before running ff"
    )


def test_empty_environment_variable_reports_its_name_and_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    monkeypatch.setenv("DV_HOME", "")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("$DV_HOME/rtl/top.sv\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "environment variable is empty\n"
        f"  at: {top_filelist}:1\n"
        "  input: $DV_HOME/rtl/top.sv\n"
        "  variable: DV_HOME\n"
        "  suggestion: export DV_HOME with a non-empty value before running ff"
    )


def test_environment_values_are_expanded_recursively(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "project" / "rtl" / "top.sv"
    source.parent.mkdir(parents=True)
    source.write_text("module top; endmodule\n", encoding="utf-8")
    monkeypatch.setenv("BASE_DIR", str(tmp_path))
    monkeypatch.setenv("PROJ_DIR", "$BASE_DIR/project")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("$PROJ_DIR/rtl/top.sv\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{source}\n"


def test_environment_expansion_cycle_reports_expansion_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    monkeypatch.setenv("ROOT_A", "$ROOT_B")
    monkeypatch.setenv("ROOT_B", "${ROOT_A}")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("$ROOT_A/rtl/top.sv\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "environment variable expansion cycle\n"
        f"  at: {top_filelist}:1\n"
        "  input: $ROOT_A/rtl/top.sv\n"
        "  expansion chain: ROOT_A -> ROOT_B -> ROOT_A\n"
        "  suggestion: remove the recursive environment variable reference"
    )


def test_filelist_reference_path_expands_environment_variables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    lists_directory = tmp_path / "lists"
    lists_directory.mkdir()
    source = lists_directory / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    child_filelist = lists_directory / "child.f"
    child_filelist.write_text("top.sv\n", encoding="utf-8")
    monkeypatch.setenv("LISTS_DIR", str(lists_directory))
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("-F $LISTS_DIR/child.f\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{source}\n"


def test_engine_can_expand_from_an_invocation_environment_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "project/rtl/top.sv"
    source.parent.mkdir(parents=True)
    source.write_text("module top; endmodule\n", encoding="utf-8")
    monkeypatch.delenv("SNAPSHOT_ROOT", raising=False)
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("$SNAPSHOT_ROOT/rtl/top.sv\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
            environment={"SNAPSHOT_ROOT": str(tmp_path / "project")},
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{source}\n"
