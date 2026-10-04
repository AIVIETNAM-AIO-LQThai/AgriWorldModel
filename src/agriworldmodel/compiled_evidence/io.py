from pathlib import Path

from agriworldmodel.compiled_evidence.schemas import CompiledStudy

def load_compiled_study(path: str | Path) -> CompiledStudy:
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(f"Compiled evidence DNE: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"Compiled evidence path is not a file: {source_path}")

    return CompiledStudy.model_validate_json(
        source_path.read_text(encoding="utf-8")
    )