from pathlib import Path

from esim.process import CommandSpec, SubprocessRunner


def test_subprocess_runner_combines_complete_output_and_returns_nonzero_status(
    tmp_path: Path,
) -> None:
    log = tmp_path / "hook.log"

    result = SubprocessRunner().run(
        CommandSpec(
            argv=(
                "/bin/bash",
                "-c",
                "printf 'stdout line\\n'; printf 'stderr line\\n' >&2; exit 7",
            ),
            cwd=tmp_path,
            log_path=log,
        )
    )

    assert result.returncode == 7
    assert log.read_text(encoding="utf-8") == "stdout line\nstderr line\n"


def test_missing_tool_is_recorded_as_a_command_failure_in_its_log(
    tmp_path: Path,
) -> None:
    log = tmp_path / "vcs.log"

    result = SubprocessRunner().run(
        CommandSpec(
            argv=("definitely-missing-esim-tool", "-version"),
            cwd=tmp_path,
            log_path=log,
        )
    )

    assert result.returncode == 127
    assert log.read_text(encoding="utf-8").startswith(
        "cannot execute command: definitely-missing-esim-tool:"
    )
