# MCP 서버: remember·search·forget 도구와 상태 리소스, 결과를 텍스트와 구조화 출력에 함께 담는다 (docs/design.md §11, §14.2)
import json
import secrets
from importlib.metadata import version

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import CallToolResult, TextContent

from gonlith.service import ServiceError


def _client_name(ctx):
    try:
        params = ctx.request_context.session.client_params
    except (AttributeError, ValueError):
        return None
    info = getattr(params, "client_info", None)
    return getattr(info, "name", None)


def _error(message):
    return CallToolResult(content=[TextContent(type="text", text=f"error: {message}")], is_error=True)


def _result(text, structured):
    return CallToolResult(content=[TextContent(type="text", text=text)], structured_content=structured)


def _render_memory(memory, text_settings, nonce):
    meta = " · ".join(
        str(part)
        for part in (
            f"#{memory['id']}",
            memory["category"],
            memory["space"],
            memory["client"] or "unknown client",
            memory["recorded_at"][:10],
            f"source: {memory['source']}",
        )
    )
    body = memory["content"]
    if memory["origin"] == "external":
        body = "\n".join(
            [text_settings["external_open"].format(nonce=nonce), body, text_settings["external_close"].format(nonce=nonce)]
        )
    return f"{meta}\n{body}"


def _public_fields(memory):
    keys = ("id", "content", "category", "space", "tags", "origin", "source", "client", "recorded_at", "valid_from", "valid_to", "score")
    return {key: memory[key] for key in keys}


def build_server(service, settings):
    server_settings, text_settings = settings["server"], settings["text"]
    search_settings, memory_settings = settings["search"], settings["memory"]
    server = MCPServer(
        name=server_settings["name"], version=version("gonlith"), instructions=server_settings["instructions"]
    )

    @server.tool(name="remember", description=server_settings["remember_description"])
    async def remember(
        content: str,
        ctx: Context,
        category: str | None = None,
        space: str | None = None,
        tags: list[str] | None = None,
        valid_from: str | None = None,
        valid_to: str | None = None,
        source: str | None = None,
    ) -> CallToolResult:
        category = category or memory_settings["default_category"]
        if category not in memory_settings["categories"]:
            return _error(f"category must be one of {memory_settings['categories']}")
        try:
            outcome = service.remember(
                content,
                category=category,
                space=space,
                tags=tags or [],
                valid_from=valid_from,
                valid_to=valid_to,
                source=source or memory_settings["default_source"],
                client=_client_name(ctx),
            )
        except ServiceError as error:
            return _error(str(error))
        verb = "already saved as" if outcome["duplicate"] else "saved as"
        return _result(f"{verb} #{outcome['id']} in space '{outcome['space']}'", outcome)

    @server.tool(name="search", description=server_settings["search_description"])
    async def search(query: str, space: str | None = None, limit: int | None = None) -> CallToolResult:
        spaces = [space, service.personal_space] if space else None
        found = service.search(query, spaces=spaces, limit=limit or search_settings["default_limit"])
        nonce = secrets.token_hex(text_settings["nonce_bytes"])
        notices = list(found["warnings"])
        if any(memory["origin"] == "external" for memory in found["results"]):
            notices.append(text_settings["external_notice"])
        budget = search_settings["max_output_chars"] - sum(len(line) + 1 for line in notices) - len(
            text_settings["omitted_notice"]
        )
        kept, blocks = [], []
        for memory in found["results"]:
            block = _render_memory(memory, text_settings, nonce)
            if sum(len(b) + 2 for b in blocks) + len(block) > budget:
                break
            kept.append(memory)
            blocks.append(block)
        omitted = len(found["results"]) - len(kept)
        if omitted:
            notices.append(text_settings["omitted_notice"].format(count=omitted))
        header = f"{len(kept)} result(s) in spaces {found['spaces']}"
        text = "\n\n".join(["\n".join([header, *notices]), *blocks])
        structured = {
            "results": [_public_fields(memory) for memory in kept],
            "warnings": found["warnings"],
            "spaces": found["spaces"],
            "omitted": omitted,
        }
        return _result(text, structured)

    @server.tool(name="forget", description=server_settings["forget_description"])
    async def forget(id: int, ctx: Context, reason: str | None = None) -> CallToolResult:
        try:
            outcome = service.forget(id, client=_client_name(ctx), reason=reason)
        except ServiceError as error:
            return _error(str(error))
        return _result(f"#{id} moved to the trash", outcome)

    @server.resource("gonlith://status", name="status", mime_type="application/json")
    async def status() -> str:
        return json.dumps(service.status(), ensure_ascii=False)

    return server
