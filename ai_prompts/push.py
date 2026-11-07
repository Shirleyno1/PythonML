"""Creates the LangSmith prompts the app reads, from the local copies in catalog.py.

    uv run python -m ai_prompts.push            # list what would be created
    uv run python -m ai_prompts.push --apply    # create the missing prompts

Prompts that already exist in LangSmith are left alone, so edits made there are
never overwritten. Prompts that send no instructions today (the agent and
streaming chat) have nothing to upload; create them in LangSmith if wanted.
"""
import argparse

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ai_prompts.catalog import ALL_PROMPTS, PromptSpec
from settings.config import settings


def build_prompt(spec: PromptSpec):
    prompt = ChatPromptTemplate.from_messages(list(spec.messages))
    if not spec.uses_model:
        return prompt
    # Saved with the prompt so the model can be changed in LangSmith too. The key
    # isn't uploaded: LangChain stores a reference to OPENAI_API_KEY instead.
    model = ChatOpenAI(model=spec.model or settings.OPENAI_MODEL, api_key="unused")
    return prompt | model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="create the missing prompts")
    args = parser.parse_args()

    from langsmith import Client
    from langsmith.utils import LangSmithError

    client = Client(api_key=settings.LANGSMITH_API_KEY)
    try:
        _push(client, apply=args.apply)
    except LangSmithError as error:
        if "not allowed for tracing keys" in str(error):
            raise SystemExit(
                "LANGSMITH_API_KEY is a tracing-only key, which can't read or create prompts. "
                "Create a Personal Access Token or Service Key in LangSmith (Settings > API "
                "Keys) in the same workspace, and use it as LANGSMITH_API_KEY."
            ) from None
        if "No prompt owner specified" in str(error):
            raise SystemExit(
                "LangSmith doesn't know which workspace the prompts belong to: the API key "
                "covers more than one. Set LANGSMITH_WORKSPACE_ID to the workspace's ID "
                "(Settings > Workspaces in LangSmith)."
            ) from None
        raise


def _push(client, apply: bool) -> None:
    for spec in ALL_PROMPTS:
        if spec.optional:
            print(f"skip    {spec.name}: no local instructions ({spec.description})")
        elif client.get_prompt(spec.name) is not None:
            print(f"exists  {spec.name}")
        elif apply:
            client.push_prompt(spec.name, object=build_prompt(spec), description=spec.description)
            print(f"created {spec.name}")
        else:
            print(f"missing {spec.name} (run with --apply to create it)")


if __name__ == "__main__":
    main()
