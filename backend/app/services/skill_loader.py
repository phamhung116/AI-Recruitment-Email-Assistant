import json
import re
from dataclasses import dataclass
from pathlib import Path


SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SKILL_BYTES = 64 * 1024
SUPPORTED_RESOURCE_SUFFIXES = {".json", ".md"}


class SkillLoadError(ValueError):
    """Raised when a domain skill is missing, invalid, or unsafe to load."""


@dataclass(frozen=True)
class SkillResource:
    name: str
    content: str


@dataclass(frozen=True)
class SkillBundle:
    name: str
    version: str
    description: str
    instructions: str
    resources: tuple[SkillResource, ...]

    def as_context(self) -> str:
        sections = [
            f"# Skill: {self.name}",
            f"Version: {self.version}",
            f"Description: {self.description}",
            self.instructions,
        ]
        sections.extend(
            f"# Resource: {resource.name}\n\n{resource.content}"
            for resource in self.resources
        )
        return "\n\n".join(sections)


class SkillLoader:
    def __init__(self, root: Path | None = None, max_bytes: int = MAX_SKILL_BYTES) -> None:
        self.root = (root or _default_skill_root()).resolve()
        self.max_bytes = max_bytes

    def load(self, skill_name: str) -> SkillBundle:
        if not SKILL_NAME_RE.fullmatch(skill_name):
            raise SkillLoadError("Skill name must contain lowercase letters, numbers, and hyphens only.")

        skill_dir = (self.root / skill_name).resolve()
        if skill_dir.parent != self.root:
            raise SkillLoadError("Skill path must stay within the configured skill root.")
        if not skill_dir.is_dir():
            raise SkillLoadError(f"Skill '{skill_name}' does not exist.")

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            raise SkillLoadError(f"Skill '{skill_name}' is missing SKILL.md.")

        total_bytes = 0
        raw_skill, skill_bytes = _read_bounded(skill_file, self.max_bytes)
        total_bytes += skill_bytes
        metadata, instructions = _parse_frontmatter(raw_skill)

        if metadata.get("name") != skill_name:
            raise SkillLoadError("SKILL.md name must match its directory name.")

        version = metadata.get("version", "").strip()
        description = metadata.get("description", "").strip()
        if not version or not description:
            raise SkillLoadError("SKILL.md requires non-empty version and description metadata.")

        resources: list[SkillResource] = []
        for resource_path in sorted(skill_dir.iterdir(), key=lambda path: path.name.lower()):
            if resource_path.name == "SKILL.md" or not resource_path.is_file():
                continue
            if resource_path.resolve().parent != skill_dir:
                raise SkillLoadError(f"Skill resource escapes its directory: {resource_path.name}.")
            if resource_path.suffix.lower() not in SUPPORTED_RESOURCE_SUFFIXES:
                raise SkillLoadError(f"Unsupported skill resource: {resource_path.name}.")

            remaining_bytes = self.max_bytes - total_bytes
            content, resource_bytes = _read_bounded(resource_path, remaining_bytes)
            total_bytes += resource_bytes
            if resource_path.suffix.lower() == ".json":
                try:
                    json.loads(content)
                except json.JSONDecodeError as error:
                    raise SkillLoadError(f"Invalid JSON resource: {resource_path.name}.") from error
            resources.append(SkillResource(name=resource_path.name, content=content))

        return SkillBundle(
            name=skill_name,
            version=version,
            description=description,
            instructions=instructions,
            resources=tuple(resources),
        )


def _default_skill_root() -> Path:
    return Path(__file__).resolve().parents[2] / "agent_skills"


def _read_bounded(path: Path, remaining_bytes: int) -> tuple[str, int]:
    if remaining_bytes <= 0:
        raise SkillLoadError("Skill exceeds the configured size limit.")

    size = path.stat().st_size
    if size > remaining_bytes:
        raise SkillLoadError("Skill exceeds the configured size limit.")

    return path.read_text(encoding="utf-8"), size


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillLoadError("SKILL.md must start with YAML-style frontmatter.")

    try:
        closing_index = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        )
    except StopIteration as error:
        raise SkillLoadError("SKILL.md frontmatter is not closed.") from error

    metadata: dict[str, str] = {}
    for line in lines[1:closing_index]:
        key, separator, value = line.partition(":")
        if not separator or not key.strip() or not value.strip():
            raise SkillLoadError(f"Invalid SKILL.md metadata line: {line!r}.")
        metadata[key.strip()] = value.strip().strip('"')

    instructions = "\n".join(lines[closing_index + 1 :]).strip()
    if not instructions:
        raise SkillLoadError("SKILL.md instructions cannot be empty.")

    return metadata, instructions
