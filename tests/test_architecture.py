import ast
from pathlib import Path

PACKAGE = "satyaapply"
PACKAGE_ROOT = Path(__file__).resolve().parent.parent / PACKAGE
LAYERS = {
    "core": 0,
    "store": 1,
    "ai": 1,
    "browser": 1,
    "sites": 1,
    "resume": 2,
    "sources": 2,
    "apply": 2,
    "inbox": 2,
    "report": 2,
    "run": 3,
    "doctor": 3,
    "tracker": 3,
    "onboarding": 3,
    "cli": 4,
    "__main__": 5,
}


def owner(path: Path, root: Path) -> str:
    return path.relative_to(root).parts[0].removesuffix(".py")


def imported_packages(source: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
        if isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        found.update(
            name.split(".")[1]
            for name in names
            if name.startswith(f"{PACKAGE}.") and name.count(".") >= 1
        )
    return found


def layer_violations(root: Path) -> list[str]:
    problems = []
    for path in sorted(root.rglob("*.py")):
        own = owner(path, root)
        if own == "__init__":
            continue
        for target in sorted(imported_packages(path.read_text(encoding="utf-8")) - {own}):
            if own not in LAYERS or target not in LAYERS:
                problems.append(f"{path}: `{own}` or `{target}` has no layer")
            elif LAYERS[target] >= LAYERS[own]:
                problems.append(
                    f"{path}: `{own}` (layer {LAYERS[own]}) imports `{target}` "
                    f"(layer {LAYERS[target]})"
                )
    return problems


def test_layers_only_import_downward() -> None:
    assert layer_violations(PACKAGE_ROOT) == []


def test_a_planted_upward_import_is_caught(tmp_path: Path) -> None:
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "models.py").write_text(f"from {PACKAGE}.cli import main\n")
    assert len(layer_violations(tmp_path)) == 1


def test_a_planted_sideways_import_is_caught(tmp_path: Path) -> None:
    (tmp_path / "store").mkdir()
    (tmp_path / "store" / "jobs.py").write_text(f"from {PACKAGE}.ai.client import ask\n")
    assert len(layer_violations(tmp_path)) == 1
