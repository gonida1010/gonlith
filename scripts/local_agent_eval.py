# 로컬 모델(Ollama)이 MCP로 gonlith를 쓰게 하는 하네스: 세션 A에서 기억시키고 새 세션 B에서 물어 교차 세션 기억을 판정한다 (docs/design.md §17)
import argparse
import json
import os
import shutil
import sys
import tempfile
import time
import tomllib
import urllib.request
from pathlib import Path

import anyio
from mcp import Client, StdioServerParameters

from gonlith.config import HOME_ENV

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def ollama_chat(config, messages, tools):
    payload = {"model": config["model"], "messages": messages, "tools": tools, "stream": False, "think": config["think"]}
    request = urllib.request.Request(
        config["endpoint"], data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=config["request_timeout_seconds"]) as response:
        return json.loads(response.read())


def tool_specs(listed):
    return [
        {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.input_schema}}
        for t in listed.tools
    ]


async def run_session(config, home, user_text):
    params = StdioServerParameters(command=shutil.which("gonlith"), args=["serve"], env={**os.environ, HOME_ENV: str(home)})
    calls, usage, started = [], {"prompt": 0, "completion": 0}, time.perf_counter()
    async with Client(params) as client:
        tools = tool_specs(await client.list_tools())
        messages = [{"role": "system", "content": client.instructions or ""}, {"role": "user", "content": user_text}]
        for _ in range(config["max_steps"]):
            reply = await anyio.to_thread.run_sync(ollama_chat, config, messages, tools)
            usage["prompt"] += reply.get("prompt_eval_count", 0)
            usage["completion"] += reply.get("eval_count", 0)
            message = reply["message"]
            messages.append(message)
            if not message.get("tool_calls"):
                return {"answer": message.get("content", ""), "calls": calls, "usage": usage, "seconds": time.perf_counter() - started}
            for call in message["tool_calls"]:
                name, arguments = call["function"]["name"], call["function"]["arguments"]
                result = await client.call_tool(name, arguments)
                text = "\n".join(block.text for block in result.content if getattr(block, "text", None))
                calls.append({"tool": name, "arguments": arguments, "is_error": bool(result.is_error)})
                messages.append({"role": "tool", "tool_name": name, "content": text})
    return {"answer": None, "calls": calls, "usage": usage, "seconds": time.perf_counter() - started, "stopped": "max_steps"}


async def run_scenario(config, scenario):
    with tempfile.TemporaryDirectory() as home:
        saved = await run_session(config, Path(home), scenario["save"])
        asked = await run_session(config, Path(home), scenario["ask"])
    remembered = any(c["tool"] == "remember" and not c["is_error"] for c in saved["calls"])
    searched = any(c["tool"] == "search" and not c["is_error"] for c in asked["calls"])
    answered = asked["answer"] is not None and all(word.lower() in asked["answer"].lower() for word in scenario["expect"])
    return {"scenario": scenario["name"], "remembered": remembered, "searched": searched, "answered": answered, "save": saved, "ask": asked}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "eval" / "local_agent.toml")
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    results = [anyio.run(run_scenario, config, scenario) for scenario in config["scenario"]]
    passed = sum(r["remembered"] and r["searched"] and r["answered"] for r in results)
    json.dump({"model": config["model"], "passed": passed, "total": len(results), "results": results}, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
