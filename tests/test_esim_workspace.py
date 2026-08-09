from pathlib import Path

import pytest

from esim.errors import InputError, WorkspaceBusyError
from esim.model import SimulationIdentity
from esim.workspace import InputSnapshotBundle, WorkspaceManager, WorkspaceMode


def test_clean_workspace_discards_only_the_exact_simulation_directory(
    tmp_path: Path,
) -> None:
    simulation_directory = tmp_path / "runs/xxx.yyy/default/func.smoke"
    simulation_directory.mkdir(parents=True)
    (simulation_directory / "stale.log").write_text("stale\n", encoding="utf-8")
    sibling = simulation_directory.parent / "other.test"
    sibling.mkdir()
    (sibling / "keep.txt").write_text("keep\n", encoding="utf-8")
    identity = SimulationIdentity(
        dtb_key="xxx.yyy",
        rules_key="default",
        test_key="func.smoke",
        directory=simulation_directory,
    )

    with WorkspaceManager().open(identity, WorkspaceMode.CLEAN) as session:
        assert session.layout.directory == simulation_directory
        assert session.layout.flattened_filelist == simulation_directory / "flattened.f"
        assert not (simulation_directory / "stale.log").exists()
        assert (sibling / "keep.txt").read_text(encoding="utf-8") == "keep\n"


def test_workspace_publishes_input_snapshots_and_total_waivers(
    tmp_path: Path,
) -> None:
    simulation_directory = tmp_path / "runs/xxx.yyy/default/func.smoke"
    identity = SimulationIdentity(
        dtb_key="xxx.yyy",
        rules_key="default",
        test_key="func.smoke",
        directory=simulation_directory,
    )

    with WorkspaceManager().open(identity, WorkspaceMode.CLEAN) as session:
        session.publish_inputs(
            InputSnapshotBundle(
                rules_yaml="name: default\n",
                tc_yaml="name: smoke\n",
                waive_text="// source: common\n*UVM_ERROR : 0*\n",
                exclude_text="",
            )
        )

    assert (simulation_directory / "rules.yaml").read_text(encoding="utf-8") == (
        "name: default\n"
    )
    assert (simulation_directory / "tc.yaml").read_text(encoding="utf-8") == (
        "name: smoke\n"
    )
    assert (simulation_directory / "waive.txt").read_text(encoding="utf-8") == (
        "// source: common\n*UVM_ERROR : 0*\n"
    )
    assert (simulation_directory / "exclude.txt").read_text(encoding="utf-8") == ""


def test_workspace_atomically_replaces_the_current_result(tmp_path: Path) -> None:
    simulation_directory = tmp_path / "runs/xxx.yyy/default/func.smoke"
    identity = SimulationIdentity(
        dtb_key="xxx.yyy",
        rules_key="default",
        test_key="func.smoke",
        directory=simulation_directory,
    )

    with WorkspaceManager().open(identity, WorkspaceMode.CLEAN) as session:
        session.layout.result_snapshot.write_text(
            "status: NOT_RUN\n",
            encoding="utf-8",
        )
        session.publish_result("status: PASS\n")

    assert (simulation_directory / "result.yaml").read_text(encoding="utf-8") == (
        "status: PASS\n"
    )
    assert list(simulation_directory.glob(".result.yaml.*")) == []


def test_workspace_rejects_a_non_directory_simulation_target(
    tmp_path: Path,
) -> None:
    simulation_directory = tmp_path / "runs/xxx.yyy/default/func.smoke"
    simulation_directory.parent.mkdir(parents=True)
    simulation_directory.write_text("not a directory\n", encoding="utf-8")
    identity = SimulationIdentity(
        dtb_key="xxx.yyy",
        rules_key="default",
        test_key="func.smoke",
        directory=simulation_directory,
    )

    with (
        pytest.raises(
            InputError,
            match="simulation directory path is not a directory",
        ),
        WorkspaceManager().open(identity, WorkspaceMode.CLEAN),
    ):
        pass


def test_lock_conflict_is_non_waiting_and_happens_before_clean(
    tmp_path: Path,
) -> None:
    simulation_directory = tmp_path / "runs/xxx.yyy/default/func.smoke"
    identity = SimulationIdentity(
        dtb_key="xxx.yyy",
        rules_key="default",
        test_key="func.smoke",
        directory=simulation_directory,
    )
    manager = WorkspaceManager()

    with manager.open(identity, WorkspaceMode.KEEP):
        stale = simulation_directory / "stale.log"
        stale.write_text("must remain\n", encoding="utf-8")
        with (
            pytest.raises(WorkspaceBusyError),
            manager.open(identity, WorkspaceMode.CLEAN),
        ):
            pass
        assert stale.read_text(encoding="utf-8") == "must remain\n"


def test_cached_workspace_loads_the_three_required_snapshots(tmp_path: Path) -> None:
    simulation_directory = tmp_path / "runs/xxx.yyy/default/func.smoke"
    simulation_directory.mkdir(parents=True)
    (simulation_directory / "rules.yaml").write_text(
        "name: default\n",
        encoding="utf-8",
    )
    (simulation_directory / "tc.yaml").write_text(
        "name: smoke\n",
        encoding="utf-8",
    )
    (simulation_directory / "result.yaml").write_text(
        "status: PASS\n",
        encoding="utf-8",
    )
    identity = SimulationIdentity(
        dtb_key="xxx.yyy",
        rules_key="default",
        test_key="func.smoke",
        directory=simulation_directory,
    )

    with WorkspaceManager().open(identity, WorkspaceMode.ACTION) as session:
        cached = session.load_cached_state()

    assert cached.rules_yaml == "name: default\n"
    assert cached.tc_yaml == "name: smoke\n"
    assert cached.result_yaml == "status: PASS\n"
