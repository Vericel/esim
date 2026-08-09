from __future__ import annotations

import fnmatch
import os
import re
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from re import Pattern

from esim.errors import WaiverError


@dataclass(frozen=True)
class WaiverSources:
    common_rules_directory: Path
    entry_rules_directory: Path


@dataclass(frozen=True)
class WaiverRule:
    pattern: str
    source: Path | str
    line_number: int
    matcher: Pattern[str]


@dataclass(frozen=True)
class CompiledWaivers:
    glob_rules: tuple[WaiverRule, ...]
    regex_rules: tuple[WaiverRule, ...]
    rendered_waive: str
    rendered_exclude: str


@dataclass(frozen=True)
class WaiverHit:
    kind: str
    pattern: str
    source: Path | str
    line_number: int


@dataclass(frozen=True)
class Finding:
    phase: str
    log_path: Path
    line_number: int
    text: str
    reasons: tuple[str, ...]
    waiver_hits: tuple[WaiverHit, ...]

    @property
    def waived(self) -> bool:
        return bool(self.waiver_hits)


Detector = Callable[[str], tuple[str, ...]]


@dataclass(frozen=True)
class LogEvaluationRequest:
    phase: str
    log_path: Path
    waivers: CompiledWaivers
    detector: Detector | None = None


@dataclass(frozen=True)
class LogEvaluation:
    findings: tuple[Finding, ...]

    @property
    def passed(self) -> bool:
        return all(finding.waived for finding in self.findings)


@dataclass(frozen=True)
class _RuleBlock:
    source: Path | str
    rules: tuple[tuple[int, str], ...]


class LogPolicy:
    _BUILT_IN_GLOBS: tuple[str, ...] = ()
    _BUILT_IN_REGEXES: tuple[str, ...] = ()

    def compile(self, sources: WaiverSources) -> CompiledWaivers:
        common = Path(os.path.abspath(sources.common_rules_directory))
        entry = Path(os.path.abspath(sources.entry_rules_directory))
        glob_blocks = self._blocks(
            self._BUILT_IN_GLOBS,
            common / "waive.txt",
            entry / "waive.txt",
        )
        regex_blocks = self._blocks(
            self._BUILT_IN_REGEXES,
            common / "exclude.txt",
            entry / "exclude.txt",
        )
        glob_rules, glob_errors = self._compile_glob_rules(glob_blocks)
        regex_rules, regex_errors = self._compile_regex_rules(regex_blocks)
        errors = (*glob_errors, *regex_errors)
        if errors:
            raise WaiverError("invalid waiver patterns\n" + "\n".join(errors))
        return CompiledWaivers(
            glob_rules=glob_rules,
            regex_rules=regex_rules,
            rendered_waive=self._render(glob_blocks),
            rendered_exclude=self._render(regex_blocks),
        )

    def evaluate(self, request: LogEvaluationRequest) -> LogEvaluation:
        log_path = Path(os.path.abspath(request.log_path))
        findings: list[Finding] = []
        for line_number, text in enumerate(
            log_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            reasons = self._reasons(text, request.detector)
            if not reasons:
                continue
            findings.append(
                Finding(
                    phase=request.phase,
                    log_path=log_path,
                    line_number=line_number,
                    text=text,
                    reasons=reasons,
                    waiver_hits=self._waiver_hits(text, request.waivers),
                )
            )
        return LogEvaluation(findings=tuple(findings))

    @staticmethod
    def _reasons(text: str, detector: Detector | None) -> tuple[str, ...]:
        lowered = text.lower()
        reasons: list[str] = []
        if "fail" in lowered:
            reasons.append("generic:fail")
        if "error" in lowered:
            reasons.append("generic:error")
        if detector is not None:
            reasons.extend(detector(text))
        return tuple(dict.fromkeys(reasons))

    @staticmethod
    def _waiver_hits(
        text: str,
        waivers: CompiledWaivers,
    ) -> tuple[WaiverHit, ...]:
        hits: list[WaiverHit] = []
        for kind, rules in (
            ("glob", waivers.glob_rules),
            ("regex", waivers.regex_rules),
        ):
            for rule in rules:
                matches = (
                    rule.matcher.fullmatch(text) is not None
                    if kind == "glob"
                    else rule.matcher.search(text) is not None
                )
                if matches:
                    hits.append(
                        WaiverHit(
                            kind=kind,
                            pattern=rule.pattern,
                            source=rule.source,
                            line_number=rule.line_number,
                        )
                    )
        return tuple(hits)

    def _blocks(
        self,
        built_in: tuple[str, ...],
        common_file: Path,
        entry_file: Path,
    ) -> tuple[_RuleBlock, ...]:
        blocks: list[_RuleBlock] = []
        if built_in:
            blocks.append(
                _RuleBlock(
                    source="esim built-in",
                    rules=tuple(enumerate(built_in, start=1)),
                )
            )
        for source_file in (common_file, entry_file):
            rules = self._read_rules(source_file)
            if rules:
                blocks.append(_RuleBlock(source=source_file, rules=rules))
        return tuple(blocks)

    @staticmethod
    def _compile_glob_rules(
        blocks: tuple[_RuleBlock, ...],
    ) -> tuple[tuple[WaiverRule, ...], tuple[str, ...]]:
        compiled: list[WaiverRule] = []
        errors: list[str] = []
        for block in blocks:
            for line_number, pattern in block.rules:
                reason = LogPolicy._invalid_glob_reason(pattern)
                if reason is not None:
                    errors.append(
                        f"  at: {block.source}:{line_number}\n"
                        f"  pattern: {pattern}\n"
                        f"  reason: {reason}"
                    )
                    continue
                compiled.append(
                    WaiverRule(
                        pattern=pattern,
                        source=block.source,
                        line_number=line_number,
                        matcher=re.compile(fnmatch.translate(pattern)),
                    )
                )
        return tuple(compiled), tuple(errors)

    @staticmethod
    def _invalid_glob_reason(pattern: str) -> str | None:
        index = 0
        while index < len(pattern):
            if pattern[index] != "[":
                index += 1
                continue
            opening = index
            index += 1
            if index < len(pattern) and pattern[index] in {"!", "^"}:
                index += 1
            if index < len(pattern) and pattern[index] == "]":
                index += 1
            while index < len(pattern) and pattern[index] != "]":
                index += 1
            if index == len(pattern):
                return f"unterminated character class at column {opening + 1}"
            index += 1
        return None

    @staticmethod
    def _compile_regex_rules(
        blocks: tuple[_RuleBlock, ...],
    ) -> tuple[tuple[WaiverRule, ...], tuple[str, ...]]:
        compiled: list[WaiverRule] = []
        errors: list[str] = []
        for block in blocks:
            for line_number, pattern in block.rules:
                try:
                    matcher = re.compile(pattern)
                except re.error as error:
                    errors.append(
                        f"  at: {block.source}:{line_number}\n"
                        f"  pattern: {pattern}\n"
                        f"  reason: {error}"
                    )
                    continue
                compiled.append(
                    WaiverRule(
                        pattern=pattern,
                        source=block.source,
                        line_number=line_number,
                        matcher=matcher,
                    )
                )
        return tuple(compiled), tuple(errors)

    @staticmethod
    def _read_rules(path: Path) -> tuple[tuple[int, str], ...]:
        if not path.exists():
            return ()
        mode = stat.S_IMODE(path.stat().st_mode)
        if not path.is_file() or not mode & 0o444 or not os.access(path, os.R_OK):
            raise WaiverError(f"waiver source is not a readable file\n  source: {path}")
        rules: list[tuple[int, str]] = []
        for line_number, original in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            rule = original.strip()
            if not rule or rule.startswith(("#", "//")):
                continue
            rules.append((line_number, rule))
        return tuple(rules)

    @staticmethod
    def _render(blocks: tuple[_RuleBlock, ...]) -> str:
        lines: list[str] = []
        for block in blocks:
            lines.append(f"// source: {block.source}")
            lines.extend(pattern for _, pattern in block.rules)
        return "" if not lines else "\n".join(lines) + "\n"


__all__ = [
    "CompiledWaivers",
    "Finding",
    "LogEvaluation",
    "LogEvaluationRequest",
    "LogPolicy",
    "WaiverHit",
    "WaiverRule",
    "WaiverSources",
]
