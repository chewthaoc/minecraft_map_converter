from __future__ import annotations

import importlib
import shutil
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Literal, Optional

Direction = Literal[
    "bedrock-to-java",
    "java-to-bedrock",
    "java-to-java",
    "bedrock-to-bedrock",
]
LogFn = Callable[[str], None]


class ConversionError(RuntimeError):
    pass


@dataclass
class ConversionResult:
    success: bool
    message: str
    details: Optional[str] = None


def convert_world(
    input_path: str | Path,
    output_path: str | Path,
    direction: Direction,
    target_version: Optional[str] = None,
    force_repair: bool = False,
    log: Optional[LogFn] = None,
) -> ConversionResult:
    input_path = Path(input_path).expanduser().resolve()
    output_path = Path(output_path).expanduser().resolve()

    _log(log, f"输入路径: {input_path}")
    _log(log, f"输出路径: {output_path}")

    if not input_path.exists():
        return ConversionResult(False, "输入路径不存在。")
    if not input_path.is_dir():
        return ConversionResult(False, "输入路径必须是存档文件夹。")
    if output_path.exists():
        if not output_path.is_dir():
            return ConversionResult(False, "输出路径必须是文件夹。")
        if any(output_path.iterdir()):
            return ConversionResult(False, "输出路径非空，请选择空目录。")
    else:
        output_path.mkdir(parents=True, exist_ok=True)

    try:
        amulet = importlib.import_module("amulet")
    except Exception as exc:  # pragma: no cover - depends on runtime
        return ConversionResult(
            False,
            "缺少转换依赖。请在构建环境中安装 Amulet 相关组件后再尝试。",
            details=str(exc),
        )

    target_platform = _resolve_target_platform(direction)
    _log(log, f"目标平台: {target_platform}")

    try:
        level = amulet.load_level(str(input_path))
    except Exception as exc:
        return ConversionResult(False, "无法读取存档。", details=str(exc))

    try:
        current_platform = _get_level_platform(level)
        if current_platform:
            _log(log, f"检测到源平台: {current_platform}")
        if current_platform == target_platform and not force_repair and not target_version:
            _log(log, "检测到目标平台与源平台一致，直接复制存档。")
            _copy_world_folder(input_path, output_path)
            return ConversionResult(True, "已完成复制。")

        _log(log, "开始尝试转换存档格式。")
        _convert_with_best_effort(
            amulet, level, output_path, target_platform, target_version, log
        )
        return ConversionResult(True, "转换完成。")
    except ConversionError as exc:
        return ConversionResult(False, str(exc))
    except Exception as exc:
        return ConversionResult(False, "转换失败。", details=traceback.format_exc())
    finally:
        try:
            level.close()
        except Exception:
            pass


def _convert_with_best_effort(
    amulet_module,
    level,
    output_path: Path,
    target_platform: str,
    target_version: Optional[str],
    log: Optional[LogFn],
) -> None:
    wrapper = _create_world_wrapper(target_platform, output_path, target_version, log)
    _log(log, f"已创建目标格式包装器: {wrapper.__class__.__name__}")

    try:
        if hasattr(level, "save_iter"):
            _log(log, "使用 save_iter 进行转换...")
            _log_save_progress(level.save_iter(wrapper), log)
        elif hasattr(level, "save"):
            _log(log, "使用 save 进行转换...")
            level.save(wrapper)
        else:
            raise ConversionError("当前存档对象不支持保存接口。")
    except Exception as exc:
        details = traceback.format_exc()
        raise ConversionError(f"转换失败: {exc}\n{details}")
    finally:
        try:
            wrapper.close()
        except Exception:
            pass


def _create_world_wrapper(
    target_platform: str,
    output_path: Path,
    target_version: Optional[str],
    log: Optional[LogFn],
):
    if target_platform == "java":
        from amulet.level.formats.anvil_world.format import AnvilFormat

        wrapper = AnvilFormat(str(output_path))
    elif target_platform == "bedrock":
        from amulet.level.formats.leveldb_world.format import LevelDBFormat

        wrapper = LevelDBFormat(str(output_path))
    else:
        raise ConversionError(f"不支持的目标平台: {target_platform}")

    version = _pick_target_version(wrapper, target_platform, target_version)
    _log(log, f"目标版本: {version}")

    try:
        wrapper.create_and_open(target_platform, version, overwrite=True)
    except Exception as exc:
        details = traceback.format_exc()
        raise ConversionError(f"创建目标存档失败: {exc}\n{details}")

    return wrapper


def _pick_target_version(
    wrapper, target_platform: str, target_version: Optional[str]
):
    parsed_version = _parse_version(target_version) if target_version else None
    if parsed_version is not None:
        return parsed_version
    try:
        versions = wrapper.translation_manager.version_numbers(target_platform)
    except Exception:
        versions = []
    if versions:
        return versions[-1]
    max_world = getattr(wrapper, "max_world_version", None)
    if isinstance(max_world, tuple) and len(max_world) == 2:
        return max_world[1]
    raise ConversionError("无法确定目标平台版本。")


def list_target_versions(target_platform: str, limit: Optional[int] = 40) -> list[str]:
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tempdir:
        if target_platform == "java":
            from amulet.level.formats.anvil_world.format import AnvilFormat

            wrapper = AnvilFormat(tempdir)
        elif target_platform == "bedrock":
            from amulet.level.formats.leveldb_world.format import LevelDBFormat

            wrapper = LevelDBFormat(tempdir)
        else:
            raise ConversionError(f"不支持的目标平台: {target_platform}")

        try:
            versions = wrapper.translation_manager.version_numbers(target_platform)
        except Exception:
            versions = []

    if limit and len(versions) > limit:
        versions = versions[-limit:]

    return [_format_version(v) for v in versions]


def convert_batch(
    input_paths: Iterable[str | Path],
    output_root: str | Path,
    direction: Direction,
    target_version: Optional[str] = None,
    force_repair: bool = False,
    log: Optional[LogFn] = None,
) -> ConversionResult:
    output_root = Path(output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    total = 0
    for input_path in input_paths:
        total += 1
        input_path = Path(input_path)
        output_path = output_root / input_path.name
        _log(log, f"\n=== 批量处理 {total} ===")
        result = convert_world(
            input_path=input_path,
            output_path=output_path,
            direction=direction,
            target_version=target_version,
            force_repair=force_repair,
            log=log,
        )
        if not result.success:
            failures.append(f"{input_path}: {result.message}")

    if failures:
        details = "\n".join(failures)
        return ConversionResult(False, "批量转换完成，但存在失败项。", details)

    return ConversionResult(True, "批量转换完成。")


def _log_save_progress(progress_iter, log: Optional[LogFn]) -> None:
    last_percent = -1
    for done, total in progress_iter:
        if total:
            percent = int(done / total * 100)
            if percent != last_percent:
                last_percent = percent
                _log(log, f"进度: {percent}% ({done}/{total})")


def _get_level_platform(level) -> Optional[str]:
    wrapper = getattr(level, "level_wrapper", None)
    if wrapper is not None:
        platform = getattr(wrapper, "platform", None)
        if platform:
            return platform
    return getattr(level, "platform", None)


def _copy_world_folder(source: Path, destination: Path) -> None:
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def _log(log: Optional[LogFn], message: str) -> None:
    if log is not None:
        log(message)


def _resolve_target_platform(direction: Direction) -> str:
    if direction in {"bedrock-to-java", "java-to-java"}:
        return "java"
    return "bedrock"


def _parse_version(value: Optional[str]):
    if not value:
        return None
    normalized = value.strip()
    if not normalized or normalized in {"最新", "latest"}:
        return None
    if "." in normalized:
        parts = [p for p in normalized.split(".") if p]
        if all(part.isdigit() for part in parts):
            return tuple(int(part) for part in parts)
    if normalized.isdigit():
        return int(normalized)
    return None


def _format_version(value) -> str:
    if isinstance(value, (tuple, list)):
        return ".".join(str(part) for part in value)
    return str(value)


