"""Executable architecture rules.

These tests parse every module's imports and assert the dependency direction
declared in ``docs/ARCHITECTURE.md``. They are the reason a five-person team
can work in parallel without eroding the boundaries: a violation fails CI with
the offending file and import named.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterator

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "libra"


def _modules() -> Iterator[tuple[str, Path]]:
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        relative = path.relative_to(PACKAGE_ROOT.parent).with_suffix("")
        yield ".".join(relative.parts), path


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.append(node.module)
    return found


def _violations(
    *, source_prefix: str, forbidden_prefixes: tuple[str, ...], exempt: tuple[str, ...] = ()
) -> list[str]:
    problems: list[str] = []
    for module, path in _modules():
        if not module.startswith(source_prefix) or module.startswith(exempt):
            continue
        for imported in _imports(path):
            if imported.startswith(forbidden_prefixes):
                problems.append(f"{module} imports {imported}")
    return problems


def test_banking_domains_do_not_depend_on_the_ai_layer() -> None:
    """Balances must stay correct even if every agent is removed."""
    assert _violations(source_prefix="libra.domains", forbidden_prefixes=("libra.ai",)) == []


def test_core_depends_on_no_higher_layer() -> None:
    assert (
        _violations(
            source_prefix="libra.core",
            forbidden_prefixes=("libra.ai", "libra.api"),
            # The composition root is the one place allowed to know everything;
            # it is the graph builder, not a core abstraction.
            exempt=("libra.core.container",),
        )
        == []
    )


def test_agents_never_reach_into_banking_domains_directly() -> None:
    """An agent's only route to banking functionality is a typed tool."""
    assert (
        _violations(
            source_prefix="libra.ai.agents", forbidden_prefixes=("libra.domains",)
        )
        == []
    )


def test_orchestration_never_reaches_into_banking_domains_directly() -> None:
    assert (
        _violations(
            source_prefix="libra.ai.orchestration", forbidden_prefixes=("libra.domains",)
        )
        == []
    )


def test_only_repositories_and_the_mongo_provider_import_a_database_driver() -> None:
    """No agent, tool, service or router may talk to MongoDB directly."""
    allowed = ("libra.core.persistence.mongo",)
    problems = [
        f"{module} imports a MongoDB driver"
        for module, path in _modules()
        if not module.startswith(allowed)
        and not module.endswith("mongo_repository")
        and any(imported.startswith(("motor", "pymongo", "bson")) for imported in _imports(path))
    ]
    assert problems == []


def test_routers_do_not_import_repositories() -> None:
    """Routers go through services; that is where authorization lives."""
    problems = [
        f"{module} imports {imported}"
        for module, path in _modules()
        if module.startswith("libra.api")
        for imported in _imports(path)
        if imported.endswith("repository") or imported.endswith("memory_repository")
    ]
    assert problems == []


def test_no_module_reads_the_environment_outside_configuration() -> None:
    """Settings are injected; a stray ``os.getenv`` would bypass validation."""
    problems = []
    for module, path in _modules():
        if module == "libra.core.config":
            continue
        source = path.read_text(encoding="utf-8")
        if "os.getenv" in source or "os.environ" in source:
            problems.append(module)
    assert problems == []


def test_no_provider_fallback_infrastructure_exists() -> None:
    """Explicit non-goal: no automatic switch to another AI provider."""
    forbidden = ("ollama", "fallback_provider", "provider_fallback")
    problems = [
        module
        for module, path in _modules()
        if any(term in path.read_text(encoding="utf-8").lower() for term in forbidden)
    ]
    assert problems == []


def test_no_generic_vision_infrastructure_exists() -> None:
    """Explicit non-goal: no VisionProvider or multimodal routing yet."""
    problems = [
        module
        for module, path in _modules()
        if "visionprovider" in path.read_text(encoding="utf-8").lower().replace(" ", "")
    ]
    assert problems == []


def test_no_interview_domain_leaked_from_the_reference_project() -> None:
    terms = ("candidate", "interview", "cv_analyzer", "study_plan")
    problems = [
        f"{module}: {term}"
        for module, path in _modules()
        for term in terms
        if term in path.read_text(encoding="utf-8").lower()
    ]
    assert problems == []


def test_no_module_level_service_singletons() -> None:
    """The reference project's import-time singletons are not repeated here."""
    suspicious = []
    for module, path in _modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            func = node.value.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name.endswith(("Service", "Registry", "Repository", "Executor", "Orchestrator")):
                suspicious.append(f"{module}: {name}()")
    assert suspicious == []
