"""
Plugin loader: scan plugins dir, read manifests, load handlers, register tools.
"""
import importlib.util
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from tools.models import PluginManifest, ToolDefinition, ToolManifestItem
from tools.registry import ToolRegistry, get_registry

logger = logging.getLogger(__name__)

IGNORE_DIRS = {"__pycache__", ".git", ".idea", "node_modules", ".venv", "venv"}


def _should_scan_dir(dirname: str) -> bool:
    return (
        not dirname.startswith(".")
        and not dirname.startswith("_")
        and dirname not in IGNORE_DIRS
    )


@dataclass
class LoadError:
    """Plugin load error."""
    plugin_id: Optional[str]
    plugin_path: str
    error: str
    exception: Optional[Exception] = None


@dataclass
class LoadResult:
    """Plugin load result."""
    loaded: List[str]
    failed: List[LoadError]
    total_tools: int


def _load_yaml(path: Path) -> Optional[dict]:
    """Load YAML file. Returns None on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning("Failed to load YAML %s: %s", path, e)
        return None


def _load_manifest(plugin_path: Path) -> Optional[PluginManifest]:
    """Read and validate plugin.yaml."""
    yaml_path = plugin_path / "plugin.yaml"
    if not yaml_path.exists():
        logger.warning("No plugin.yaml in %s", plugin_path)
        return None
    data = _load_yaml(yaml_path)
    if not data:
        return None
    try:
        return PluginManifest.model_validate(data)
    except Exception as e:
        logger.warning("Invalid plugin manifest %s: %s", yaml_path, e)
        return None


def _load_handlers_module(plugin_path: Path, plugin_id: str):
    """Load handlers.py as a module. Returns module or None."""
    handlers_path = plugin_path / "handlers.py"
    if not handlers_path.exists():
        logger.warning("No handlers.py in %s", plugin_path)
        return None
    try:
        spec = importlib.util.spec_from_file_location(
            f"plugins_{plugin_id.replace('-', '_')}_handlers",
            handlers_path,
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.warning("Failed to load handlers %s: %s", handlers_path, e)
        return None


def _build_tool_definition(
    manifest: PluginManifest,
    item: ToolManifestItem,
    handler: Any,
) -> ToolDefinition:
    """Build ToolDefinition from manifest item and bound handler."""
    return ToolDefinition(
        name=item.name,
        description=item.description,
        plugin_id=manifest.id,
        handler=handler,
        parameters=item.parameters,
        timeout=item.timeout,
        enabled=manifest.enabled,
    )


async def load_plugin(
    plugin_path: str,
    registry: Optional[ToolRegistry] = None,
) -> Optional[PluginManifest]:
    """
    Load one plugin from the given folder. Register plugin and tools.
    Returns PluginManifest if success, None on error.
    """
    reg = registry or get_registry()
    path = Path(plugin_path).resolve()
    if not path.is_dir():
        logger.warning("Plugin path is not a directory: %s", plugin_path)
        return None

    manifest = _load_manifest(path)
    if not manifest:
        return None

    module = _load_handlers_module(path, manifest.id)
    if not module:
        return None

    reg.register_plugin(manifest)
    for item in manifest.tools:
        handler = getattr(module, item.handler, None)
        if not callable(handler):
            logger.warning("Handler %s not found or not callable in %s", item.handler, path)
            continue
        tool_def = _build_tool_definition(manifest, item, handler)
        try:
            reg.register_tool(tool_def)
        except ValueError as e:
            logger.warning("Skip tool %s: %s", item.name, e)
    logger.info("Loaded plugin %s (%d tools)", manifest.id, len(manifest.tools))
    return manifest


async def load_all_plugins(
    plugins_dir: str = "plugins",
    registry: Optional[ToolRegistry] = None,
) -> LoadResult:
    """
    Load all plugins from the given directory.
    """
    reg = registry or get_registry()
    path = Path(plugins_dir).resolve()
    if not path.exists() or not path.is_dir():
        return LoadResult(loaded=[], failed=[], total_tools=0)

    loaded: List[str] = []
    failed: List[LoadError] = []
    for child in sorted(path.iterdir()):
        if not child.is_dir() or not _should_scan_dir(child.name):
            continue
        try:
            manifest = await load_plugin(str(child), registry=reg)
            if manifest:
                loaded.append(manifest.id)
            else:
                failed.append(LoadError(
                    plugin_id=None,
                    plugin_path=str(child),
                    error="Load returned None",
                    exception=None,
                ))
        except Exception as e:
            logger.exception("Error loading plugin %s: %s", child, e)
            failed.append(LoadError(
                plugin_id=None,
                plugin_path=str(child),
                error=str(e),
                exception=e,
            ))
    total = reg.get_stats()["total_tools"]
    return LoadResult(loaded=loaded, failed=failed, total_tools=total)


async def reload_plugin(
    plugin_id: str,
    plugins_dir: str = "plugins",
    registry: Optional[ToolRegistry] = None,
) -> bool:
    """Reload plugin: unregister then load again. Returns True if successful."""
    reg = registry or get_registry()
    path = Path(plugins_dir).resolve()
    if not path.exists():
        return False
    # Find plugin folder by id (direct children only)
    plugin_path = None
    for child in path.iterdir():
        if not child.is_dir() or not _should_scan_dir(child.name):
            continue
        manifest = _load_manifest(child)
        if manifest and manifest.id == plugin_id:
            plugin_path = child
            break
    if not plugin_path:
        logger.warning("Plugin %s not found in %s", plugin_id, plugins_dir)
        return False
    reg.unregister_plugin(plugin_id)
    manifest = await load_plugin(str(plugin_path), registry=reg)
    return manifest is not None


async def reload_all_plugins(
    plugins_dir: str = "plugins",
    registry: Optional[ToolRegistry] = None,
) -> LoadResult:
    """Clear registry and load all plugins again."""
    reg = registry or get_registry()
    reg.clear()
    return await load_all_plugins(plugins_dir=plugins_dir, registry=reg)
