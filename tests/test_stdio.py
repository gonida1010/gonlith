# 실제 클라이언트처럼 gonlith serve를 하위 프로세스로 띄워 stdio로 연결하고, 두 연결 사이에 기억이 공유되는지 확인하는 시험 (docs/design.md §11.4)
import os
import shutil

import anyio
from mcp import Client, StdioServerParameters

from gonlith.config import HOME_ENV, SPACE_ENV


def params(home, space=None):
    env = {**os.environ, HOME_ENV: str(home)}
    if space:
        env[SPACE_ENV] = space
    return StdioServerParameters(command=shutil.which("gonlith"), args=["serve"], env=env)


def test_two_stdio_clients_share_memory(home):
    async def main():
        async with Client(params(home)) as writer:
            saved = await writer.call_tool("remember", {"content": "stdio로 저장한 기억입니다"})
        async with Client(params(home)) as reader:
            found = await reader.call_tool("search", {"query": "저장한"})
        return saved, found

    saved, found = anyio.run(main)
    assert not saved.is_error
    assert [result["id"] for result in found.structured_content["results"]] == [saved.structured_content["id"]]


def test_space_from_environment_is_used(home):
    async def main():
        async with Client(params(home, space="project-x")) as client:
            return await client.call_tool("remember", {"content": "프로젝트 공간 기억"})

    assert anyio.run(main).structured_content["space"] == "project-x"
