from __future__ import annotations

import fcntl
import os
import shutil
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from esim.errors import InputError, WorkspaceBusyError
from esim.model import SimulationIdentity


class WorkspaceMode(Enum):
    CLEAN = "clean"
    KEEP = "keep"
    ACTION = "action"
    CHECK = "check"


@dataclass(frozen=True)
class WorkspaceLayout:
    directory: Path
    flattened_filelist: Path
    ff_log: Path
    rules_snapshot: Path
    tc_snapshot: Path
    result_snapshot: Path
    waive_file: Path
    exclude_file: Path
    simv: Path
    vlogan_log: Path
    vcs_log: Path
    simv_log: Path

    def hook_log(self, phase: str, timing: str) -> Path:
        prefix = "pre" if timing == "before" else "post"
        return self.directory / f"{prefix}_{phase}.log"

    @classmethod
    def for_directory(cls, directory: Path) -> WorkspaceLayout:
        root = Path(os.path.abspath(directory))
        return cls(
            directory=root,
            flattened_filelist=root / "flattened.f",
            ff_log=root / "ff.log",
            rules_snapshot=root / "rules.yaml",
            tc_snapshot=root / "tc.yaml",
            result_snapshot=root / "result.yaml",
            waive_file=root / "waive.txt",
            exclude_file=root / "exclude.txt",
            simv=root / "simv",
            vlogan_log=root / "vlogan.log",
            vcs_log=root / "vcs.log",
            simv_log=root / "simv.log",
        )


@dataclass(frozen=True)
class InputSnapshotBundle:
    rules_yaml: str
    tc_yaml: str
    waive_text: str
    exclude_text: str


@dataclass(frozen=True)
class CachedRunState:
    rules_yaml: str
    tc_yaml: str
    result_yaml: str


@dataclass(frozen=True)
class WorkspaceSession:
    layout: WorkspaceLayout

    def publish_inputs(self, bundle: InputSnapshotBundle) -> None:
        for path, content in (
            (self.layout.rules_snapshot, bundle.rules_yaml),
            (self.layout.tc_snapshot, bundle.tc_yaml),
        ):
            self._atomic_write(path, content)
        self.publish_waivers(bundle.waive_text, bundle.exclude_text)

    def publish_waivers(self, waive_text: str, exclude_text: str) -> None:
        for path, content in (
            (self.layout.waive_file, waive_text),
            (self.layout.exclude_file, exclude_text),
        ):
            self._atomic_write(path, content)

    def publish_result(self, result_yaml: str) -> None:
        self._atomic_write(self.layout.result_snapshot, result_yaml)

    def load_cached_state(self) -> CachedRunState:
        return CachedRunState(
            rules_yaml=self._read_required(self.layout.rules_snapshot),
            tc_yaml=self._read_required(self.layout.tc_snapshot),
            result_yaml=self._read_required(self.layout.result_snapshot),
        )

    @staticmethod
    def _read_required(path: Path) -> str:
        if not path.is_file():
            raise InputError(
                f"required cached snapshot does not exist\n  snapshot: {path}"
            )
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        temporary_fd, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            dir=path.parent,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(temporary_fd, "w", encoding="utf-8", newline="") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


class WorkspaceManager:
    @contextmanager
    def open(
        self,
        identity: SimulationIdentity,
        mode: WorkspaceMode,
    ) -> Generator[WorkspaceSession, None, None]:
        layout = WorkspaceLayout.for_directory(identity.directory)
        self._validate_target(layout.directory)
        layout.directory.parent.mkdir(parents=True, exist_ok=True)
        lock_path = layout.directory.parent / f".{layout.directory.name}.esim.lock"
        lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        os.set_inheritable(lock_fd, False)
        try:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise WorkspaceBusyError(
                    "simulation directory is locked by another invocation\n"
                    f"  directory: {layout.directory}\n"
                    f"  lock: {lock_path}"
                ) from error
            self._prepare(layout, mode)
            yield WorkspaceSession(layout=layout)
        finally:
            os.close(lock_fd)

    @staticmethod
    def _prepare(layout: WorkspaceLayout, mode: WorkspaceMode) -> None:
        if layout.directory.exists() and (
            not layout.directory.is_dir() or layout.directory.is_symlink()
        ):
            raise InputError(
                "simulation directory path is not a directory\n"
                f"  directory: {layout.directory}"
            )
        if mode is WorkspaceMode.CLEAN:
            if layout.directory.exists():
                shutil.rmtree(layout.directory)
            layout.directory.mkdir(parents=True)
            return
        if mode is WorkspaceMode.KEEP:
            layout.directory.mkdir(parents=True, exist_ok=True)
            return
        if not layout.directory.is_dir():
            raise InputError(
                "simulation directory does not exist for cached operation\n"
                f"  directory: {layout.directory}"
            )

    @staticmethod
    def _validate_target(directory: Path) -> None:
        if not directory.is_absolute() or directory == Path("/"):
            raise InputError(
                "simulation directory must be a specific absolute path\n"
                f"  directory: {directory}"
            )


__all__ = [
    "CachedRunState",
    "InputSnapshotBundle",
    "WorkspaceLayout",
    "WorkspaceManager",
    "WorkspaceMode",
    "WorkspaceSession",
]
