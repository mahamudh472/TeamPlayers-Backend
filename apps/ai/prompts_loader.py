from pathlib import Path


PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(file_name: str) -> str:
    """
    Load a prompt from the prompts directory.

    Args:
        file_name: Prompt file name.

    Returns:
        Prompt text.
    """

    prompt_path = PROMPTS_DIR / file_name

    return prompt_path.read_text(
        encoding="utf-8"
    )
