from pathlib import Path
from typing import Any


class PromptBuilder:
    """
    Builds the instructions and conversation input sent to OpenAI.

    The builder is responsible for:
    - loading the permanent Sonic Forge system prompt;
    - loading the prompt for the current workshop stage;
    - adding optional project context;
    - normalizing conversation messages.
    """

    STAGE_PROMPTS = {
        "concept": "workshop_stage_concept.md",
        "tracks": "workshop_stage_tracks.md",
        "lyrics": "workshop_stage_lyrics.md",
    }

    def __init__(self, project_root: Path | None = None):
        if project_root is None:
            project_root = Path(__file__).resolve().parent.parent

        self.project_root = project_root
        self.prompt_directory = project_root / "prompts"

    def build(
        self,
        stage: str,
        conversation: list[dict[str, str]],
        project_context: dict[str, Any] | None = None,
    ) -> tuple[str, list[dict[str, str]]]:
        """
        Return:
            instructions: combined system and stage instructions
            messages: normalized conversation messages
        """

        system_prompt = self.load_prompt(
            "workshop_system.md"
        )

        stage_filename = self.STAGE_PROMPTS.get(stage)

        if stage_filename is None:
            raise ValueError(
                f"Unknown workshop stage: {stage}"
            )

        stage_prompt = self.load_prompt(
            stage_filename
        )

        instruction_parts = [
            system_prompt,
            stage_prompt,
        ]

        if project_context:
            instruction_parts.append(
                self.format_project_context(
                    project_context
                )
            )

        instructions = "\n\n".join(
            part.strip()
            for part in instruction_parts
            if part.strip()
        )

        messages = self.normalize_conversation(
            conversation
        )

        return instructions, messages

    def load_prompt(self, filename: str) -> str:
        prompt_path = self.prompt_directory / filename

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_path}"
            )

        content = prompt_path.read_text(
            encoding="utf-8"
        )

        marker = "## Prompt"

        if marker in content:
            content = content.split(
                marker,
                1
            )[1]

        return content.strip()

    def normalize_conversation(
        self,
        conversation: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []

        for message in conversation:
            role = message.get("role", "").strip()
            content = message.get(
                "content",
                ""
            ).strip()

            if role not in {
                "user",
                "assistant",
            }:
                continue

            if not content:
                continue

            normalized.append({
                "role": role,
                "content": content,
            })

        return normalized

    def format_project_context(
        self,
        project_context: dict[str, Any],
    ) -> str:
        lines = [
            "CURRENT ALBUM PROJECT CONTEXT",
            "",
        ]

        for key, value in project_context.items():
            label = key.replace(
                "_",
                " "
            ).title()

            lines.append(
                f"{label}: {value}"
            )

        return "\n".join(lines)