import os
from pathlib import Path

import pytest


def test_success_atomically_replaces_existing_output_inode(tmp_path: Path) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_filelist = tmp_path / "flattened.f"
    output_filelist.write_text("old content\n", encoding="utf-8")
    old_inode = output_filelist.stat().st_ino

    flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
            output_filelist=output_filelist,
        )
    )

    assert output_filelist.read_text(encoding="utf-8") == f"{source}\n"
    assert output_filelist.stat().st_ino != old_inode


def test_replacing_regular_output_preserves_rw_bits_and_clears_execute(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_filelist = tmp_path / "flattened.f"
    output_filelist.write_text("old content\n", encoding="utf-8")
    output_filelist.chmod(0o765)

    flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
            output_filelist=output_filelist,
        )
    )

    assert output_filelist.stat().st_mode & 0o777 == 0o664


def test_new_output_permissions_respect_process_umask(tmp_path: Path) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_filelist = tmp_path / "new.f"

    previous_umask = os.umask(0o027)
    try:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )
    finally:
        os.umask(previous_umask)

    assert output_filelist.stat().st_mode & 0o777 == 0o640


def test_output_parent_directory_must_already_exist(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_filelist = tmp_path / "missing" / "flattened.f"

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )

    assert str(caught.value) == (
        "output parent directory does not exist\n"
        f"  output: {output_filelist}\n"
        f"  parent: {output_filelist.parent}\n"
        "  suggestion: create the parent directory or choose another output"
    )
    assert not output_filelist.parent.exists()


def test_output_parent_must_be_a_writable_directory(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    parent_file = tmp_path / "not-a-directory"
    parent_file.write_text("content\n", encoding="utf-8")
    output_filelist = parent_file / "flattened.f"

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )

    assert str(caught.value) == (
        "output parent is not a directory\n"
        f"  output: {output_filelist}\n"
        f"  parent: {parent_file}\n"
        "  suggestion: choose an output path inside a directory"
    )


def test_output_parent_directory_must_be_writable(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_parent = tmp_path / "read-only"
    output_parent.mkdir()
    output_parent.chmod(0o555)
    output_filelist = output_parent / "flattened.f"

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )

    assert str(caught.value) == (
        "output parent directory is not writable\n"
        f"  output: {output_filelist}\n"
        f"  parent: {output_parent}\n"
        "  suggestion: grant write and search permission to the directory"
    )


def test_output_parent_access_uses_effective_process_permissions(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("", encoding="utf-8")
    output_parent = tmp_path / "other-only"
    output_parent.mkdir()
    output_parent.chmod(0o003)
    output_filelist = output_parent / "flattened.f"

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )
    output_parent.chmod(0o700)

    assert "output parent directory is not writable" in str(caught.value)


def test_existing_output_directory_is_rejected_before_publication(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_filelist = tmp_path / "flattened.f"
    output_filelist.mkdir()

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )

    assert str(caught.value) == (
        "output path is not a regular file\n"
        f"  output: {output_filelist}\n"
        "  suggestion: choose a file path for the flattened filelist"
    )
    assert output_filelist.is_dir()


def test_output_symlink_node_is_replaced_without_touching_target(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_target = tmp_path / "preserved.f"
    output_target.write_text("target stays\n", encoding="utf-8")
    output_filelist = tmp_path / "flattened.f"
    output_filelist.symlink_to(output_target)

    flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
            output_filelist=output_filelist,
        )
    )

    assert not output_filelist.is_symlink()
    assert output_filelist.read_text(encoding="utf-8") == f"{source}\n"
    assert output_target.read_text(encoding="utf-8") == "target stays\n"


def test_flatten_failure_preserves_existing_output_bytes_and_inode(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("missing.sv\n", encoding="utf-8")
    output_filelist = tmp_path / "flattened.f"
    original_content = b"existing output\n"
    output_filelist.write_bytes(original_content)
    original_inode = output_filelist.stat().st_ino

    with pytest.raises(FlattenError):
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )

    assert output_filelist.read_bytes() == original_content
    assert output_filelist.stat().st_ino == original_inode


def test_output_cannot_replace_an_input_filelist(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    original_content = "top.sv\n"
    top_filelist.write_text(original_content, encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=top_filelist,
            )
        )

    assert str(caught.value) == (
        "output conflicts with an input filelist\n"
        f"  output: {top_filelist}\n"
        f"  input: {top_filelist}\n"
        "  suggestion: choose a different output path"
    )
    assert top_filelist.read_text(encoding="utf-8") == original_content


def test_output_symlink_to_nested_input_is_rejected_by_real_identity(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    child_filelist = tmp_path / "child.f"
    original_child = ""
    child_filelist.write_text(original_child, encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("-F child.f\n", encoding="utf-8")
    output_filelist = tmp_path / "flattened.f"
    output_filelist.symlink_to(child_filelist)

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )

    assert "output conflicts with an input filelist" in str(caught.value)
    assert f"  input: {child_filelist}" in str(caught.value)
    assert output_filelist.is_symlink()
    assert child_filelist.read_text(encoding="utf-8") == original_child
    assert top_filelist.read_text(encoding="utf-8") == "-F child.f\n"


def test_symlinked_source_keeps_logical_path_with_physical_target_comment(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    physical_source = tmp_path / "physical" / "top.sv"
    physical_source.parent.mkdir()
    physical_source.write_text("module top; endmodule\n", encoding="utf-8")
    logical_source = tmp_path / "logical" / "top.sv"
    logical_source.parent.mkdir()
    logical_source.symlink_to(physical_source)
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("logical/top.sv\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"// symlink target: {physical_source}\n{logical_source}\n"
    )


def test_all_recognized_simulator_paths_annotate_symlink_targets(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    physical_directory = tmp_path / "physical"
    physical_directory.mkdir()
    physical_library = physical_directory / "models.v"
    physical_library.write_text("module model; endmodule\n", encoding="utf-8")
    logical_directory = tmp_path / "logical"
    logical_directory.symlink_to(physical_directory, target_is_directory=True)
    logical_library = logical_directory / "models.v"
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "-v logical/models.v\n-y logical\n+incdir+logical\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"// symlink target: {physical_directory}\n"
        f"+incdir+{logical_directory}\n"
        f"// symlink target: {physical_library}\n"
        f"-v {logical_library}\n"
        f"// symlink target: {physical_directory}\n"
        f"-y {logical_directory}\n"
    )


def test_symlinked_child_filelist_is_annotated_before_its_expansion(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "lists" / "top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n", encoding="utf-8")
    physical_child = tmp_path / "physical" / "child.f"
    physical_child.parent.mkdir()
    physical_child.write_text("../lists/top.sv\n", encoding="utf-8")
    logical_child = tmp_path / "lists" / "child.f"
    logical_child.symlink_to(physical_child)
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("-F lists/child.f\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"// symlink target: {physical_child}\n{source}\n"
    )


def test_symlinked_top_filelist_is_annotated_before_flattened_content(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "logical" / "top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n", encoding="utf-8")
    physical_filelist = tmp_path / "physical" / "top.f"
    physical_filelist.parent.mkdir()
    physical_filelist.write_text("top.sv\n", encoding="utf-8")
    logical_filelist = tmp_path / "logical" / "top.f"
    logical_filelist.symlink_to(physical_filelist)

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=logical_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"// symlink target: {physical_filelist}\n{source}\n"
    )


def test_utf8_bom_and_crlf_input_renders_utf8_lf_without_bom(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_bytes(b"\xef\xbb\xbftop.sv\r\n")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_bytes() == f"{source}\n".encode()


def test_non_utf8_filelist_reports_structured_error(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_bytes(b"top.sv\xff\n")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "filelist is not valid UTF-8\n"
        f"  input: {top_filelist}\n"
        "  suggestion: convert the filelist to UTF-8"
    )
