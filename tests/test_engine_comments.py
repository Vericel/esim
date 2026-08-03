import os
from pathlib import Path

import pytest

def test_active_blank_lines_and_line_comments_preserve_source_order(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    first_source = tmp_path / "first.sv"
    first_source.write_text("module first; endmodule\n", encoding="utf-8")
    second_source = tmp_path / "second.sv"
    second_source.write_text("module second; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "first.sv\n"
        "\n"
        "  // between sources\n"
        "second.sv\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"{first_source}\n"
        "\n"
        "  // between sources\n"
        f"{second_source}\n"
    )


def test_multiline_block_comments_follow_conditional_branch_selection(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "active.sv"
    source.write_text("module active; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "`ifdef OMITTED\n"
        "/* removed\n"
        "   comment */\n"
        "`else\n"
        "/* retained\n"
        "   comment */\n"
        "active.sv\n"
        "`endif\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        "/* retained\n"
        "   comment */\n"
        f"{source}\n"
    )


def test_multiline_block_comment_follows_normalized_source_path(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "rtl" / "top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "rtl/top.sv /* primary\n"
        "               source */\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"{source} /* primary\n"
        "               source */\n"
    )


def test_filelist_reference_trailing_comment_is_promoted_before_expansion(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    child_filelist = tmp_path / "child.f"
    child_filelist.write_text("top.sv\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "-F child.f // expanded child sources\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        "// expanded child sources\n"
        f"{source}\n"
    )


def test_filelist_reference_promotes_complete_multiline_block_comment(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    child_filelist = tmp_path / "child.f"
    child_filelist.write_text("top.sv\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "-F child.f /* expanded\n"
        "               child sources */\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        "/* expanded\n"
        "               child sources */\n"
        f"{source}\n"
    )


def test_block_comment_must_close_inside_the_filelist_that_opened_it(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    child_filelist = tmp_path / "child.f"
    child_filelist.write_text("/* not closed here\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "-F child.f\n"
        "*/\n",
        encoding="utf-8",
    )

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "unterminated block comment\n"
        "  source chain:\n"
        f"    {top_filelist}:1 -> {child_filelist}\n"
        f"  opened at: {child_filelist}:1\n"
        "  suggestion: close the comment with */ in the same filelist"
    )


@pytest.mark.parametrize(
    "entry",
    ["top.sv /* note */ extra", "/* note */ top.sv"],
)
def test_block_comment_closure_rejects_additional_logical_content(
    tmp_path: Path,
    entry: str,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(f"{entry}\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "content after block comment is not supported\n"
        f"  at: {top_filelist}:1\n"
        f"  input: {entry}\n"
        "  suggestion: put the next logical entry on a separate line"
    )


def test_source_trailing_comment_follows_normalized_absolute_path(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "rtl" / "top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "rtl/top.sv // primary source\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"{source} // primary source\n"
    )
