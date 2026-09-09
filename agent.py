import json
import os
import subprocess

from dotenv import load_dotenv
from openai import  OpenAI

load_dotenv()
api_key = os.environ["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

MODEL = "gpt-5-mini"
SYSTEM_PROMPT = """You are a coding agent runnning in the user's terminal.
You can list files, read files write files, and run shell commands.
Use your tools to complete the user's task, then briefly summarize what you did.
The working directory is the folder the user launched you from."""

def list_files(path="."):
    entries = []
    for entry in os.scandir(path):
        entries.append(entry.name + ("/" if entry.is_dir() else ""))
    return "\n".join(entries) or "(empty directory)"

def read_file(path):
    try:
        with open(path, "r", "utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"File {path} does not exist"

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Saved {path} ({len(content)} characters)successfully"

def run_command(command):
    answer = input(f" Run '{command}'?[y/N] ")
    if answer.strip().lower() != "y":
        return "The user declined to run this command"
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=120
    )

    output = (result.stdout + result.stderr).strip()
    return output or f"(no output, exit code {result.returncode})"

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The file path to read."},
                },
                "required": ["path"]
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file, overwriting it if it already exists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The file path to write to."},
                    "content": {"type": "string", "description": "The text content to write to the file."},
                },
                "required": ["path", "content"]
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command after prompting the user for confirmation, and return its output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute."},
                },
                "required": ["command"]
            },
        }
    }
]

TOOLS = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "run_command": run_command
}

def run_tool(tool_call):
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    print(f" tool: {name}(){args}")
    try:
        return str(TOOLS[name](**args))
    except Exception as e:
        return f"Error: {e}"

def run_agent(messages):
    while True:
        response = client.chat.completions.create(
            model = MODEL,
            messages=messages,
            tools = TOOL_SCHEMAS,
        )
        message = response.choices[0].message
        messages.append(message)

        # No tool calls means the model is done and answered in plain text
        if not message.tool_calls:
            return message.content

        for tool_call in message.tool_calls:
            result = run_tool(tool_call)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })
def main():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("Mini agent ready. Type 'exit' to quit")
    while True:
        user_input = input("\nYou: ")
        if user_input.strip().lower() == ("exit", "quit"):
            break
        messages.append({"role": "user", "content": user_input})
        reply = run_agent(messages)
        print(f"\nAgent: {reply}")

if __name__ == "__main__":
    main()