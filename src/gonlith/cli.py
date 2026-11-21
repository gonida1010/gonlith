# gonlith 명령줄: MCP 서버 실행(serve), 데이터 폴더 초기화(init), 로그 전체 재검증(verify) (docs/design.md §12.2, §13)
import json
import os
import sys
import uuid

import typer

from gonlith.config import SPACE_ENV, data_home, load_settings
from gonlith.store import Store, StoreError
from gonlith.verify import replay

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _open_store():
    home = data_home()
    return Store.open(home, load_settings(home))


@app.command()
def serve():
    """Run the MCP server over stdio (used by MCP clients)."""
    from gonlith.server import build_server
    from gonlith.service import MemoryService

    home = data_home()
    settings = load_settings(home)
    service = MemoryService(home, settings, session=uuid.uuid4().hex, default_space=os.environ.get(SPACE_ENV))
    try:
        build_server(service, settings).run("stdio")
    finally:
        service.close()


@app.command()
def init():
    """Create the log (normally done automatically on first run)."""
    store = _open_store()
    try:
        origin = store.initialize()
    except StoreError as error:
        typer.echo(f"error: {error}", err=True)
        raise typer.Exit(1) from error
    finally:
        store.close()
    typer.echo(f"initialized {origin}")


@app.command()
def verify(as_json: bool = typer.Option(False, "--json", help="Print the result as JSON.")):
    """Replay the whole log and report integrity problems."""
    store = _open_store()
    try:
        state = replay(store)
    finally:
        store.close()
    result = {
        "ok": state.ok,
        "size": state.size,
        "memories": len(state.memories),
        "broken": sorted(p for p, m in state.memories.items() if m["integrity"] != "ok"),
        "first_bad_position": state.first_bad_position,
        "problems": [{"position": p.position, "reason": p.reason} for p in state.problems],
        "checkpoint": state.checkpoint() if state.origin else None,
    }
    if as_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        typer.echo("OK" if state.ok else "PROBLEMS FOUND")
        typer.echo(f"entries: {result['size']}  memories: {result['memories']}  broken: {len(result['broken'])}")
        for problem in result["problems"]:
            typer.echo(f"  position {problem['position']}: {problem['reason']}")
        if result["checkpoint"]:
            typer.echo("checkpoint:")
            typer.echo(result["checkpoint"], nl=False)
    raise typer.Exit(0 if state.ok else 1)
