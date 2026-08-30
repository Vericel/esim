from __future__ import annotations

import os
import re
import shlex
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from esim.errors import (
    CacheCompatibilityError,
    ConfigurationError,
    InputError,
    SelectorError,
)
from esim.model import (
    Action,
    BuildConfiguration,
    CompiledInvocation,
    ConfigurationDiagnostic,
    EffectiveTestcase,
    FfConfiguration,
    Flow,
    IgnoredField,
    LocatedInvocation,
    PhaseConfiguration,
    PhaseHooks,
    ResolvedRules,
    RunRequest,
    SimulationIdentity,
)
from esim.yaml_codec import decode_configuration, decode_mapping, encode_mapping

_MACRO_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*")
_DOTTED_SELECTOR_PATTERN = re.compile(r"[^./\\:]+(?:\.[^./\\:]+)*")


@dataclass(frozen=True)
class CompileRequest:
    located: LocatedInvocation
    run_request: RunRequest
    cached_tc_yaml: str | None = None


@dataclass(frozen=True)
class _PhaseHooksFragment:
    before: tuple[str, ...] = ()
    after: tuple[str, ...] = ()
    continue_on_error: bool | None = None


@dataclass(frozen=True)
class _SourceConfig:
    includes: tuple[Path, ...]
    ignored_fields: tuple[IgnoredField, ...]
    description: str | None
    owner: str | None
    tags: tuple[str, ...]
    filelist: Path | None
    simulator: str | None
    flow: Flow | None
    ff_args: tuple[str, ...]
    ff_hooks: _PhaseHooksFragment
    build_args_declared: bool
    build_args: tuple[str, ...]
    build_hooks: _PhaseHooksFragment
    analyze_declared: bool
    analyze_args: tuple[str, ...]
    analyze_hooks: _PhaseHooksFragment
    elaborate_declared: bool
    elaborate_args: tuple[str, ...]
    elaborate_hooks: _PhaseHooksFragment
    run_args: tuple[str, ...]
    run_hooks: _PhaseHooksFragment


@dataclass(frozen=True)
class _LoadedConfig:
    path: Path
    source: _SourceConfig
    include_chain: tuple[Path, ...]


class ConfigurationCompiler:
    def __init__(self, *, environment: Mapping[str, str]) -> None:
        self._environment = dict(environment)

    def locate(self, request: RunRequest) -> LocatedInvocation:
        dv_home = self._required_path("DV_HOME")
        dv_tmp = self._required_path("DV_TMP")
        entry_tc, dtb_key, test_key = self._locate_tc(
            request.tc_selector,
            dv_home,
        )
        dtb_directory = dv_home / Path(*dtb_key.split("."))
        entry_rules, rules_key = self._locate_rules(
            request.rules_selector,
            dv_home,
            dtb_directory,
        )
        identity = SimulationIdentity(
            dtb_key=dtb_key,
            rules_key=rules_key,
            test_key=test_key,
            directory=self._absolute(dv_tmp / dtb_key / rules_key / test_key),
        )
        return LocatedInvocation(
            entry_tc=self._absolute(entry_tc),
            entry_rules=self._absolute(entry_rules),
            identity=identity,
        )

    def compile(self, request: CompileRequest) -> CompiledInvocation:
        merged_paths: set[Path] = set()
        diagnostics: list[ConfigurationDiagnostic] = []
        rules_nodes = self._load_graph(
            request.located.entry_rules,
            merged_paths,
            diagnostics,
        )
        tc_nodes = self._load_graph(
            request.located.entry_tc,
            merged_paths,
            diagnostics,
        )
        rules_source = self._merge_sources(rules_nodes, "Rules")
        effective_source = self._merge_sources(
            (*rules_nodes, *tc_nodes),
            "Effective TC",
        )
        entry_rules_source = self._load_source(request.located.entry_rules)
        entry_tc_source = self._load_source(request.located.entry_tc)
        if rules_source.filelist is None:
            raise ConfigurationError("no filelist is declared by the Rules graph")
        if rules_source.simulator is None:
            raise ConfigurationError("no simulator is declared by the Rules graph")
        if rules_source.flow is None:
            raise ConfigurationError("no flow is declared by the Rules graph")
        resolved_ff = self._ff_configuration(
            rules_source.ff_args,
            rules_source.ff_hooks,
        )
        resolved_build = self._build_configuration(
            rules_source,
            rules_source.flow,
        )
        resolved_run = self._phase_configuration(
            rules_source.run_args,
            rules_source.run_hooks,
        )
        resolved_rules = ResolvedRules(
            name=request.located.entry_rules.stem,
            description=entry_rules_source.description,
            tags=rules_source.tags,
            filelist=rules_source.filelist,
            simulator=rules_source.simulator,
            flow=rules_source.flow,
            ff=resolved_ff,
            build=resolved_build,
            run=resolved_run,
            entry_rules=request.located.entry_rules,
            merge_order=tuple(node.path for node in rules_nodes),
        )

        effective_ff = self._ff_configuration(
            effective_source.ff_args,
            effective_source.ff_hooks,
        )
        effective_build = self._build_configuration(
            effective_source,
            rules_source.flow,
            build_cli_args=request.run_request.build_args,
            elaborate_cli_args=request.run_request.elaborate_args,
        )
        effective_run = self._phase_configuration(
            (
                *effective_source.run_args,
                *request.run_request.run_args,
            ),
            effective_source.run_hooks,
        )
        if (
            effective_source.filelist is None
            or effective_source.simulator is None
            or effective_source.flow is None
        ):
            raise ConfigurationError(
                "Effective TC is missing a required Rules declaration"
            )
        effective_tc = EffectiveTestcase(
            name=request.located.entry_tc.stem,
            description=entry_tc_source.description,
            tags=effective_source.tags,
            filelist=effective_source.filelist,
            simulator=effective_source.simulator,
            flow=effective_source.flow,
            ff=effective_ff,
            build=effective_build,
            run=effective_run,
            entry_rules=request.located.entry_rules,
            merge_order=tuple(node.path for node in (*rules_nodes, *tc_nodes)),
            owner=entry_tc_source.owner,
            entry_tc=request.located.entry_tc,
        )
        tc_yaml = self._render_tc_yaml(effective_tc)
        self._validate_action_compatibility(request, tc_yaml)
        return CompiledInvocation(
            resolved_rules=resolved_rules,
            effective_tc=effective_tc,
            ignored_fields=effective_source.ignored_fields,
            diagnostics=tuple(diagnostics),
            rules_yaml=self._render_rules_yaml(resolved_rules),
            tc_yaml=tc_yaml,
        )

    def _validate_action_compatibility(
        self,
        request: CompileRequest,
        current_tc_yaml: str,
    ) -> None:
        action = request.run_request.action
        if action is Action.FULL:
            return
        if action is Action.BUILD and request.run_request.run_args:
            raise ConfigurationError("build action does not accept run CLI arguments")
        if action is Action.RUN and (
            request.run_request.build_args or request.run_request.elaborate_args
        ):
            raise ConfigurationError("run action only accepts run-stage CLI arguments")
        if action is Action.BUILD:
            fields = ("filelist", "ff")
        else:
            fields = ("filelist", "ff", "simulator", "flow", "build")
        if request.cached_tc_yaml is None:
            raise CacheCompatibilityError(
                "cached tc.yaml is required for a stage action"
            )
        current = decode_mapping(
            current_tc_yaml,
            "current tc.yaml",
            CacheCompatibilityError,
        )
        cached = decode_mapping(
            request.cached_tc_yaml,
            "cached tc.yaml",
            CacheCompatibilityError,
        )
        changed = tuple(
            field for field in fields if current.get(field) != cached.get(field)
        )
        if changed:
            raise CacheCompatibilityError(
                "cached upstream configuration is incompatible\n"
                f"  action: {action.value}\n"
                f"  changed: {', '.join(changed)}"
            )

    def _render_rules_yaml(self, rules: ResolvedRules) -> str:
        snapshot = self._configuration_snapshot(rules)
        snapshot["source"] = {
            "entry": str(rules.entry_rules),
            "merge_order": [str(path) for path in rules.merge_order],
        }
        return encode_mapping(snapshot)

    def _render_tc_yaml(self, testcase: EffectiveTestcase) -> str:
        snapshot = self._configuration_snapshot(testcase)
        if testcase.owner is not None:
            snapshot["owner"] = testcase.owner
        snapshot["source"] = {
            "entry_tc": str(testcase.entry_tc),
            "entry_rules": str(testcase.entry_rules),
            "merge_order": [str(path) for path in testcase.merge_order],
        }
        return encode_mapping(snapshot)

    def _configuration_snapshot(self, config: ResolvedRules) -> dict[str, object]:
        snapshot: dict[str, object] = {"name": config.name}
        if config.description is not None:
            snapshot["description"] = config.description
        if config.tags:
            snapshot["tags"] = list(config.tags)
        snapshot.update(
            {
                "filelist": str(config.filelist),
                "simulator": config.simulator,
                "flow": config.flow.value,
            }
        )
        ff = self._ff_snapshot(config.ff)
        if ff:
            snapshot["ff"] = ff
        build = self._build_snapshot(config.build)
        if build:
            snapshot["build"] = build
        run = self._phase_snapshot(config.run)
        if run:
            snapshot["run"] = run
        return snapshot

    def _ff_snapshot(self, phase: FfConfiguration) -> dict[str, object]:
        snapshot: dict[str, object] = {}
        if phase.args:
            snapshot["args"] = list(phase.args)
        hooks = self._hooks_snapshot(phase.hooks)
        if hooks:
            snapshot["hooks"] = hooks
        return snapshot

    def _build_snapshot(self, build: BuildConfiguration) -> dict[str, object]:
        snapshot: dict[str, object] = {}
        if build.args:
            snapshot["args"] = list(build.args)
        hooks = self._hooks_snapshot(build.hooks)
        if hooks:
            snapshot["hooks"] = hooks
        if build.analyze is not None:
            analyze = self._phase_snapshot(build.analyze)
            if analyze:
                snapshot["analyze"] = analyze
        if build.elaborate is not None:
            elaborate = self._phase_snapshot(build.elaborate)
            if elaborate:
                snapshot["elaborate"] = elaborate
        return snapshot

    def _phase_snapshot(self, phase: PhaseConfiguration) -> dict[str, object]:
        snapshot: dict[str, object] = {}
        if phase.args:
            snapshot["args"] = list(phase.args)
        hooks = self._hooks_snapshot(phase.hooks)
        if hooks:
            snapshot["hooks"] = hooks
        return snapshot

    @staticmethod
    def _hooks_snapshot(hooks: PhaseHooks) -> dict[str, object]:
        snapshot: dict[str, object] = {}
        if hooks.before:
            snapshot["before"] = list(hooks.before)
        if hooks.after:
            snapshot["after"] = list(hooks.after)
        if hooks.continue_on_error:
            snapshot["continue_on_error"] = True
        return snapshot

    def _load_graph(
        self,
        entry: Path,
        merged_paths: set[Path],
        diagnostics: list[ConfigurationDiagnostic],
    ) -> tuple[_LoadedConfig, ...]:
        ordered: list[_LoadedConfig] = []
        active: list[Path] = []

        def visit(path: Path) -> None:
            path = self._absolute(path)
            if path in active:
                cycle_start = active.index(path)
                cycle = (*active[cycle_start:], path)
                raise ConfigurationError(
                    "configuration include cycle\n"
                    + "\n".join(f"  source: {item}" for item in cycle)
                )
            if path in merged_paths:
                diagnostics.append(
                    ConfigurationDiagnostic(
                        kind="duplicate_include",
                        source=path,
                        include_chain=(*active, path),
                    )
                )
                return
            include_chain = (*active, path)
            source = self._load_source(path)
            active.append(path)
            for included in source.includes:
                visit(included)
            active.pop()
            if path in merged_paths:
                return
            merged_paths.add(path)
            ordered.append(
                _LoadedConfig(
                    path=path,
                    source=source,
                    include_chain=include_chain,
                )
            )

        visit(entry)
        return tuple(ordered)

    def _merge_sources(
        self,
        nodes: tuple[_LoadedConfig, ...],
        graph_name: str,
    ) -> _SourceConfig:
        filelists = tuple(
            (node.path, node.source.filelist, node.include_chain)
            for node in nodes
            if node.source.filelist is not None
        )
        if len(filelists) != 1:
            details = "\n".join(
                f"  source: {path}\n"
                f"  filelist: {filelist}\n"
                "  include chain: " + " -> ".join(str(item) for item in include_chain)
                for path, filelist, include_chain in filelists
            )
            raise ConfigurationError(
                f"{graph_name} must contain exactly one filelist declaration"
                + (f"\n{details}" if details else "")
            )
        simulators = self._consistent_values(nodes, "simulator", graph_name)
        flows = self._consistent_values(nodes, "flow", graph_name)
        ff_hooks = _PhaseHooksFragment()
        build_hooks = _PhaseHooksFragment()
        run_hooks = _PhaseHooksFragment()
        for node in nodes:
            ff_hooks = self._merge_hooks(ff_hooks, node.source.ff_hooks)
            build_hooks = self._merge_hooks(build_hooks, node.source.build_hooks)
            run_hooks = self._merge_hooks(run_hooks, node.source.run_hooks)
        return _SourceConfig(
            includes=(),
            ignored_fields=self._stable_unique_ignored(
                tuple(
                    ignored for node in nodes for ignored in node.source.ignored_fields
                )
            ),
            description=None,
            owner=None,
            tags=self._stable_unique(
                tuple(tag for node in nodes for tag in node.source.tags)
            ),
            filelist=filelists[0][1],
            simulator=cast(str | None, simulators),
            flow=cast(Flow | None, flows),
            ff_args=tuple(arg for node in nodes for arg in node.source.ff_args),
            ff_hooks=ff_hooks,
            build_args_declared=any(node.source.build_args_declared for node in nodes),
            build_args=tuple(arg for node in nodes for arg in node.source.build_args),
            build_hooks=build_hooks,
            analyze_declared=any(node.source.analyze_declared for node in nodes),
            analyze_args=tuple(
                arg for node in nodes for arg in node.source.analyze_args
            ),
            analyze_hooks=self._merge_phase_hooks(
                tuple(node.source.analyze_hooks for node in nodes)
            ),
            elaborate_declared=any(node.source.elaborate_declared for node in nodes),
            elaborate_args=tuple(
                arg for node in nodes for arg in node.source.elaborate_args
            ),
            elaborate_hooks=self._merge_phase_hooks(
                tuple(node.source.elaborate_hooks for node in nodes)
            ),
            run_args=tuple(arg for node in nodes for arg in node.source.run_args),
            run_hooks=run_hooks,
        )

    @staticmethod
    def _consistent_values(
        nodes: tuple[_LoadedConfig, ...],
        field: str,
        graph_name: str,
    ) -> object | None:
        declarations = tuple(
            (node.path, getattr(node.source, field))
            for node in nodes
            if getattr(node.source, field) is not None
        )
        distinct = tuple(dict.fromkeys(value for _, value in declarations))
        if len(distinct) > 1:
            details = "\n".join(
                f"  source: {path}\n  {field}: {value}" for path, value in declarations
            )
            raise ConfigurationError(
                f"conflicting {field} declarations in {graph_name}\n{details}"
            )
        return distinct[0] if distinct else None

    def _load_source(self, path: Path) -> _SourceConfig:
        path = self._absolute(path)
        is_rules = self._is_rules_path(path)
        try:
            yaml_text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ConfigurationError(
                f"cannot load YAML configuration\n  source: {path}\n  reason: {error}"
            ) from error
        loaded = decode_configuration(yaml_text, path)
        data = self._mapping(loaded, path, "<root>")
        if not is_rules and any(
            field in data for field in ("filelist", "simulator", "flow")
        ):
            raise ConfigurationError(
                f"TC declares a Rules-only field\n  source: {path}"
            )
        if is_rules and "owner" in data:
            raise ConfigurationError(
                f"Rules declares the TC-only owner field\n  source: {path}"
            )
        description = self._optional_nonempty_string(data, "description", path)
        owner = self._optional_nonempty_string(data, "owner", path)
        if owner is not None and ("\n" in owner or "\r" in owner):
            raise ConfigurationError(
                f"owner must be a single-line string\n  source: {path}"
            )
        filelist = self._optional_filelist(data, path)
        simulator = self._optional_string(data, "simulator", path)
        if simulator is not None and simulator != "vcs":
            raise ConfigurationError(
                f"unsupported simulator\n  source: {path}\n  simulator: {simulator}"
            )
        flow_text = self._optional_string(data, "flow", path)
        try:
            flow = Flow(flow_text) if flow_text is not None else None
        except ValueError as error:
            raise ConfigurationError(
                f"unsupported build flow\n  source: {path}\n  flow: {flow_text}"
            ) from error
        ff = self._phase_source(data, "ff", path)
        build = self._phase_source(data, "build", path)
        build_mapping = self._optional_mapping(data, "build", path)
        analyze = self._nested_phase_source(build_mapping, "analyze", path, "build")
        elaborate = self._nested_phase_source(
            build_mapping,
            "elaborate",
            path,
            "build",
        )
        run = self._phase_source(data, "run", path)
        return _SourceConfig(
            includes=self._includes(data, path),
            ignored_fields=self._collect_ignored_fields(data, path),
            description=description,
            owner=owner,
            tags=self._tags(data, path),
            filelist=filelist,
            simulator=simulator,
            flow=flow,
            ff_args=ff[0],
            ff_hooks=ff[1],
            build_args_declared=build_mapping is not None and "args" in build_mapping,
            build_args=build[0],
            build_hooks=build[1],
            analyze_declared=(build_mapping is not None and "analyze" in build_mapping),
            analyze_args=analyze[0],
            analyze_hooks=analyze[1],
            elaborate_declared=(
                build_mapping is not None and "elaborate" in build_mapping
            ),
            elaborate_args=elaborate[0],
            elaborate_hooks=elaborate[1],
            run_args=run[0],
            run_hooks=run[1],
        )

    def _collect_ignored_fields(
        self,
        data: dict[str, object],
        source: Path,
    ) -> tuple[IgnoredField, ...]:
        ignored: list[IgnoredField] = []
        top_level = {
            "include",
            "description",
            "tags",
            "filelist",
            "simulator",
            "flow",
            "owner",
            "ff",
            "build",
            "run",
        }

        def record(path: str) -> None:
            ignored.append(IgnoredField(source=source, path=path))

        def visit_hooks(value: object, prefix: str) -> None:
            if not isinstance(value, dict):
                return
            hooks = cast(dict[str, object], value)
            for key in hooks:
                path = f"{prefix}.{key}"
                if key not in {"before", "after", "continue_on_error"}:
                    record(path)

        def visit_phase(
            value: object,
            prefix: str,
            *,
            build: bool = False,
        ) -> None:
            if not isinstance(value, dict):
                return
            phase = cast(dict[str, object], value)
            allowed = {"args", "hooks"}
            if build:
                allowed.update({"analyze", "elaborate"})
            for key, item in phase.items():
                path = f"{prefix}.{key}"
                if key not in allowed:
                    record(path)
                elif key == "hooks":
                    visit_hooks(item, path)
                elif build and key in {"analyze", "elaborate"}:
                    visit_phase(item, path)

        for key, value in data.items():
            if key not in top_level:
                record(key)
            elif key in {"ff", "run"}:
                visit_phase(value, key)
            elif key == "build":
                visit_phase(value, key, build=True)
        return tuple(ignored)

    def _includes(self, data: dict[str, object], source: Path) -> tuple[Path, ...]:
        value = data.get("include", [])
        if not isinstance(value, list):
            raise ConfigurationError(
                f"include must be a list of path strings\n  source: {source}"
            )
        items = cast(list[object], value)
        if any(not isinstance(item, str) for item in items):
            raise ConfigurationError(
                f"include must be a list of path strings\n  source: {source}"
            )
        included_paths: list[Path] = []
        for item in cast(list[str], items):
            expanded = self._expand_environment(item, source, "include")
            candidate = Path(expanded)
            if not candidate.is_absolute():
                candidate = source.parent / candidate
            candidate = self._absolute(candidate)
            self._is_rules_path(candidate)
            if not self._is_readable_file(candidate):
                raise ConfigurationError(
                    "included configuration must be a readable regular file\n"
                    f"  source: {source}\n"
                    f"  include: {candidate}"
                )
            included_paths.append(candidate)
        return tuple(included_paths)

    def _is_rules_path(self, path: Path) -> bool:
        dv_home = self._required_path("DV_HOME")
        try:
            relative = path.relative_to(dv_home)
        except ValueError as error:
            raise ConfigurationError(
                f"configuration must be located below DV_HOME\n  source: {path}"
            ) from error
        is_rules = path.suffix in {".rules", ".yaml"} and path.parent.name == "rules"
        is_tc = (
            path.suffix in {".tc", ".yaml"}
            and "tests" in relative.parts
            and relative.parts.index("tests") > 0
        )
        if is_rules == is_tc:
            raise ConfigurationError(
                "configuration path does not identify exactly one TC/Rules role\n"
                f"  source: {path}"
            )
        return is_rules

    def _optional_filelist(self, data: dict[str, object], path: Path) -> Path | None:
        value = self._optional_string(data, "filelist", path)
        if value is None:
            return None
        expanded = self._expand_environment(value, path, "filelist")
        candidate = Path(expanded)
        if not candidate.is_absolute():
            candidate = path.parent / candidate
        candidate = self._absolute(candidate)
        if not self._is_readable_file(candidate):
            raise ConfigurationError(
                "filelist must be a readable regular file\n"
                f"  source: {path}\n"
                f"  filelist: {candidate}"
            )
        return candidate

    def _expand_environment(self, value: str, source: Path, field: str) -> str:
        if any(character in value for character in ("`", "~", "*", "?", "[")):
            raise ConfigurationError(
                "unsupported path expansion syntax\n"
                f"  source: {source}\n"
                f"  field: {field}\n"
                f"  value: {value}"
            )
        pattern = re.compile(
            r"\$(?:([A-Za-z_][A-Za-z0-9_]*)|\{([A-Za-z_][A-Za-z0-9_]*)\})"
        )

        def expand(text: str, stack: tuple[str, ...]) -> str:
            def replace(match: re.Match[str]) -> str:
                name = match.group(1) or match.group(2)
                if name in stack:
                    chain = " -> ".join((*stack, name))
                    raise ConfigurationError(
                        "environment variable expansion cycle\n"
                        f"  source: {source}\n"
                        f"  field: {field}\n"
                        f"  chain: {chain}"
                    )
                replacement = self._environment.get(name)
                if replacement is None or replacement == "":
                    raise ConfigurationError(
                        "environment variable is missing or empty\n"
                        f"  source: {source}\n"
                        f"  field: {field}\n"
                        f"  variable: {name}"
                    )
                return expand(replacement, (*stack, name))

            expanded = pattern.sub(replace, text)
            if "$" in expanded:
                raise ConfigurationError(
                    "unsupported environment variable syntax\n"
                    f"  source: {source}\n"
                    f"  field: {field}\n"
                    f"  value: {value}"
                )
            return expanded

        return expand(value, ())

    def _phase_source(
        self,
        data: dict[str, object],
        field: str,
        path: Path,
    ) -> tuple[tuple[str, ...], _PhaseHooksFragment]:
        if field not in data:
            return (), _PhaseHooksFragment()
        value = data[field]
        phase = self._mapping(value, path, field)
        args_value = phase.get("args", [])
        if not isinstance(args_value, list):
            raise ConfigurationError(
                "phase args must be a list of strings\n"
                f"  source: {path}\n"
                f"  field: {field}.args"
            )
        args_items = cast(list[object], args_value)
        if any(not isinstance(item, str) for item in args_items):
            raise ConfigurationError(
                "phase args must be a list of strings\n"
                f"  source: {path}\n"
                f"  field: {field}.args"
            )
        return tuple(cast(list[str], args_items)), self._hooks(phase, field, path)

    def _nested_phase_source(
        self,
        parent: dict[str, object] | None,
        field: str,
        path: Path,
        parent_name: str,
    ) -> tuple[tuple[str, ...], _PhaseHooksFragment]:
        if parent is None or field not in parent:
            return (), _PhaseHooksFragment()
        phase = self._mapping(parent[field], path, f"{parent_name}.{field}")
        args_value = phase.get("args", [])
        if not isinstance(args_value, list):
            raise ConfigurationError(
                "phase args must be a list of strings\n"
                f"  source: {path}\n"
                f"  field: {parent_name}.{field}.args"
            )
        args_items = cast(list[object], args_value)
        if any(not isinstance(item, str) for item in args_items):
            raise ConfigurationError(
                "phase args must be a list of strings\n"
                f"  source: {path}\n"
                f"  field: {parent_name}.{field}.args"
            )
        return tuple(cast(list[str], args_items)), self._hooks(
            phase,
            f"{parent_name}.{field}",
            path,
        )

    def _optional_mapping(
        self,
        data: dict[str, object],
        field: str,
        path: Path,
    ) -> dict[str, object] | None:
        if field not in data:
            return None
        return self._mapping(data[field], path, field)

    def _hooks(
        self,
        phase: dict[str, object],
        phase_name: str,
        path: Path,
    ) -> _PhaseHooksFragment:
        if "hooks" not in phase:
            return _PhaseHooksFragment()
        value = phase["hooks"]
        hooks = self._mapping(value, path, f"{phase_name}.hooks")
        continue_value = hooks.get("continue_on_error")
        if continue_value is not None and not isinstance(continue_value, bool):
            raise ConfigurationError(
                "continue_on_error must be a boolean\n"
                f"  source: {path}\n"
                f"  field: {phase_name}.hooks.continue_on_error"
            )
        return _PhaseHooksFragment(
            before=self._hook_commands(hooks, "before", phase_name, path),
            after=self._hook_commands(hooks, "after", phase_name, path),
            continue_on_error=continue_value,
        )

    def _hook_commands(
        self,
        hooks: dict[str, object],
        timing: str,
        phase_name: str,
        path: Path,
    ) -> tuple[str, ...]:
        if timing not in hooks:
            return ()
        commands_value = hooks[timing]
        if not isinstance(commands_value, list):
            raise ConfigurationError(
                "hook commands must be nonempty single-line strings\n"
                f"  source: {path}\n"
                f"  field: {phase_name}.hooks.{timing}"
            )
        command_items = cast(list[object], commands_value)
        if any(
            not isinstance(item, str)
            or not item.strip()
            or "\n" in item
            or "\r" in item
            for item in command_items
        ):
            raise ConfigurationError(
                "hook commands must be nonempty single-line strings\n"
                f"  source: {path}\n"
                f"  field: {phase_name}.hooks.{timing}"
            )
        return tuple(cast(list[str], command_items))

    @staticmethod
    def _mapping(value: object, path: Path, field: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise ConfigurationError(
                "YAML node must be a mapping with string keys\n"
                f"  source: {path}\n"
                f"  field: {field}"
            )
        items = cast(dict[object, object], value)
        if any(not isinstance(key, str) for key in items):
            raise ConfigurationError(
                "YAML node must be a mapping with string keys\n"
                f"  source: {path}\n"
                f"  field: {field}"
            )
        return cast(dict[str, object], items)

    @staticmethod
    def _optional_string(data: dict[str, object], field: str, path: Path) -> str | None:
        if field not in data:
            return None
        value = data[field]
        if not isinstance(value, str):
            raise ConfigurationError(
                "configuration field must be a string\n"
                f"  source: {path}\n"
                f"  field: {field}"
            )
        return value

    def _optional_nonempty_string(
        self,
        data: dict[str, object],
        field: str,
        path: Path,
    ) -> str | None:
        value = self._optional_string(data, field, path)
        if value is not None and not value.strip():
            raise ConfigurationError(
                "configuration field must not be empty\n"
                f"  source: {path}\n"
                f"  field: {field}"
            )
        return value

    @staticmethod
    def _tags(data: dict[str, object], path: Path) -> tuple[str, ...]:
        value = data.get("tags", [])
        if not isinstance(value, list):
            raise ConfigurationError(
                f"tags must be a list of nonempty strings\n  source: {path}"
            )
        items = cast(list[object], value)
        if any(not isinstance(item, str) or not item for item in items):
            raise ConfigurationError(
                f"tags must be a list of nonempty strings\n  source: {path}"
            )
        return tuple(cast(list[str], items))

    def _phase_configuration(
        self,
        args: tuple[str, ...],
        hooks: _PhaseHooksFragment,
    ) -> PhaseConfiguration:
        return PhaseConfiguration(
            args=args,
            argv=self._split_args(args),
            hooks=self._finalize_hooks(hooks),
        )

    def _build_configuration(
        self,
        source: _SourceConfig,
        flow: Flow,
        *,
        build_cli_args: tuple[str, ...] = (),
        elaborate_cli_args: tuple[str, ...] = (),
    ) -> BuildConfiguration:
        if flow is Flow.TWO_STEP:
            if source.analyze_declared or source.elaborate_declared:
                raise ConfigurationError(
                    "two-step flow does not allow build.analyze or build.elaborate"
                )
            if elaborate_cli_args:
                raise ConfigurationError(
                    "elaborate CLI arguments are not valid for a two-step flow"
                )
            args = (*source.build_args, *build_cli_args)
            return BuildConfiguration(
                args=args,
                argv=self._split_args(args),
                hooks=self._finalize_hooks(source.build_hooks),
                analyze=None,
                elaborate=None,
            )
        if source.build_args_declared:
            raise ConfigurationError("three-step flow does not allow direct build.args")
        analyze_args = (*source.analyze_args, *build_cli_args)
        elaborate_args = (*source.elaborate_args, *elaborate_cli_args)
        return BuildConfiguration(
            args=(),
            argv=(),
            hooks=self._finalize_hooks(source.build_hooks),
            analyze=self._phase_configuration(analyze_args, source.analyze_hooks),
            elaborate=self._phase_configuration(
                elaborate_args,
                source.elaborate_hooks,
            ),
        )

    def _ff_configuration(
        self,
        args: tuple[str, ...],
        hooks: _PhaseHooksFragment,
    ) -> FfConfiguration:
        tokens = self._split_args(args)
        macros: list[str] = []
        accepting_macros = False
        for token in tokens:
            if token in {"-d", "--define"}:
                accepting_macros = True
                continue
            if not accepting_macros or _MACRO_PATTERN.fullmatch(token) is None:
                raise ConfigurationError(
                    "ff.args only supports -d/--define followed by macro names\n"
                    f"  token: {token}"
                )
            macros.append(token)
        if tokens and (not macros or tokens[-1] in {"-d", "--define"}):
            raise ConfigurationError("ff define option requires at least one macro")
        return FfConfiguration(
            args=args,
            predefined_macros=frozenset(macros),
            hooks=self._finalize_hooks(hooks),
        )

    def _split_args(self, fragments: tuple[str, ...]) -> tuple[str, ...]:
        tokens: list[str] = []
        for fragment in fragments:
            try:
                split_tokens = shlex.split(fragment, posix=True)
            except ValueError as error:
                raise ConfigurationError(
                    "invalid POSIX quoting in phase args\n"
                    f"  fragment: {fragment}\n"
                    f"  reason: {error}"
                ) from error
            tokens.extend(self._expand_arg_token(token) for token in split_tokens)
        return tuple(tokens)

    def _expand_arg_token(self, token: str) -> str:
        literal_dollar = "\x00ESIM_LITERAL_DOLLAR\x00"
        protected = token.replace("$$", literal_dollar)
        expanded = self._expand_environment(
            protected,
            Path("<merged phase args>"),
            "args",
        )
        return expanded.replace(literal_dollar, "$")

    @staticmethod
    def _merge_hooks(
        earlier: _PhaseHooksFragment,
        later: _PhaseHooksFragment,
    ) -> _PhaseHooksFragment:
        return _PhaseHooksFragment(
            before=(*earlier.before, *later.before),
            after=(*earlier.after, *later.after),
            continue_on_error=(
                later.continue_on_error
                if later.continue_on_error is not None
                else earlier.continue_on_error
            ),
        )

    @staticmethod
    def _merge_phase_hooks(
        values: tuple[_PhaseHooksFragment, ...],
    ) -> _PhaseHooksFragment:
        merged = _PhaseHooksFragment()
        for value in values:
            merged = ConfigurationCompiler._merge_hooks(merged, value)
        return merged

    @staticmethod
    def _finalize_hooks(hooks: _PhaseHooksFragment) -> PhaseHooks:
        return PhaseHooks(
            before=hooks.before,
            after=hooks.after,
            continue_on_error=bool(hooks.continue_on_error),
        )

    @staticmethod
    def _stable_unique(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(values))

    @staticmethod
    def _stable_unique_ignored(
        values: tuple[IgnoredField, ...],
    ) -> tuple[IgnoredField, ...]:
        return tuple(dict.fromkeys(values))

    def _locate_tc(
        self,
        selector: str,
        dv_home: Path,
    ) -> tuple[Path, str, str]:
        selected_path = Path(selector)
        if selected_path.is_absolute():
            entry_tc = self._absolute(selected_path)
            try:
                relative = entry_tc.relative_to(dv_home)
            except ValueError:
                relative = Path()
            is_valid_tree = (
                relative.parts.count("tests") == 1
                and relative.parts.index("tests") > 0
                and relative.parts.index("tests") < len(relative.parts) - 1
                and entry_tc.suffix in {".tc", ".yaml"}
                and self._is_readable_file(entry_tc)
            )
            if not is_valid_tree:
                raise SelectorError(
                    "absolute TC must be below DV_HOME/<dtb>/tests\n"
                    f"  selector: {selector}\n"
                    f"  DV_HOME: {dv_home}"
                )
            tests_index = relative.parts.index("tests")
            dtb_parts = relative.parts[:tests_index]
            test_parts = relative.parts[tests_index + 1 :]
            dtb_key = ".".join(dtb_parts)
            test_key = ".".join((*test_parts[:-1], Path(test_parts[-1]).stem))
            return entry_tc, dtb_key, test_key

        if ":" not in selector:
            raise SelectorError(
                "relative TC paths are not supported\n"
                f"  selector: {selector}\n"
                "  suggestion: use an absolute path or <dotted-dtb>:<dotted-test>"
            )
        dtb_key, test_key = selector.split(":", 1)
        if (
            _DOTTED_SELECTOR_PATTERN.fullmatch(dtb_key) is None
            or _DOTTED_SELECTOR_PATTERN.fullmatch(test_key) is None
        ):
            raise SelectorError(
                "invalid logical TC selector\n"
                f"  selector: {selector}\n"
                "  expected: <dotted-dtb>:<dotted-test>"
            )
        dtb_directory = dv_home / Path(*dtb_key.split("."))
        test_relative = Path(*test_key.split("."))
        entry_tc = self._first_readable(
            "TC",
            dtb_directory / "tests" / test_relative.with_suffix(".tc"),
            dtb_directory / "tests" / test_relative.with_suffix(".yaml"),
        )
        return entry_tc, dtb_key, test_key

    def _locate_rules(
        self,
        selector: str | None,
        dv_home: Path,
        dtb_directory: Path,
    ) -> tuple[Path, str]:
        rules_selector = selector or "default"
        selected_path = Path(rules_selector)
        if selected_path.is_absolute():
            entry_rules = self._absolute(selected_path)
            try:
                rules_parent = entry_rules.parent.relative_to(dv_home)
            except ValueError:
                rules_parent = Path()
            is_valid_rules = (
                len(rules_parent.parts) >= 2
                and rules_parent.parts[-1] == "rules"
                and entry_rules.suffix in {".rules", ".yaml"}
                and self._is_readable_file(entry_rules)
            )
            if not is_valid_rules:
                raise SelectorError(
                    "absolute Rules must be inside a DV_HOME rules directory\n"
                    f"  selector: {rules_selector}\n"
                    f"  DV_HOME: {dv_home}"
                )
            return entry_rules, entry_rules.stem

        if (
            not rules_selector
            or any(separator in rules_selector for separator in ("/", "\\", ":"))
            or selected_path.suffix in {".rules", ".yaml"}
        ):
            raise SelectorError(
                "invalid logical Rules selector; "
                "relative Rules paths are not supported\n"
                f"  selector: {rules_selector}\n"
                "  suggestion: use an absolute path or a Rules logical name"
            )

        entry_rules = self._first_readable(
            "Rules",
            dtb_directory / "rules" / f"{rules_selector}.rules",
            dtb_directory / "rules" / f"{rules_selector}.yaml",
            dv_home / "dtb_common" / "rules" / f"{rules_selector}.rules",
            dv_home / "dtb_common" / "rules" / f"{rules_selector}.yaml",
        )
        return entry_rules, rules_selector

    @staticmethod
    def _first_readable(kind: str, *candidates: Path) -> Path:
        for candidate in candidates:
            if ConfigurationCompiler._is_readable_file(candidate):
                return candidate
        rendered = "\n".join(f"  candidate: {candidate}" for candidate in candidates)
        raise SelectorError(
            f"{kind} selector did not match a readable file\n{rendered}"
        )

    @staticmethod
    def _is_readable_file(path: Path) -> bool:
        if not path.is_file():
            return False
        mode = stat.S_IMODE(path.stat().st_mode)
        return bool(mode & 0o444) and os.access(path, os.R_OK)

    def _required_path(self, name: str) -> Path:
        value = self._environment.get(name)
        if value is None or not value:
            raise InputError(
                "required environment variable is not set\n"
                f"  variable: {name}\n"
                f"  suggestion: export {name} with an absolute directory path"
            )
        return self._absolute(Path(value))

    @staticmethod
    def _absolute(path: Path) -> Path:
        return Path(os.path.abspath(path))


__all__ = ["CompileRequest", "ConfigurationCompiler"]
