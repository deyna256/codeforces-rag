from __future__ import annotations

import os

import httpx
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, LoadingIndicator, Static

RAG_URL = os.environ.get("RAG_URL", "http://localhost:8000")
CF_API_URL = "https://codeforces.com/api/contest.list"

STATUS_LOADED = "[green]✓[/green]"
STATUS_LOADING = "[yellow]⟳[/yellow]"
STATUS_ERROR = "[red]✗[/red]"
STATUS_EMPTY = ""

COL_STATUS = "status"
COL_ID = "id"
COL_NAME = "name"


class ContestLoaderApp(App):
    CSS = """
    DataTable {
        height: 1fr;
    }
    LoadingIndicator {
        height: 3;
    }
    #rag-url {
        height: 1;
        color: $text-disabled;
        padding: 0 1;
    }
    """

    TITLE = "Codeforces Contest Loader"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._contests: list[dict] = []
        self._loaded_ids: set[str] = set()
        self._loading_ids: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Header()
        yield LoadingIndicator()
        yield DataTable(cursor_type="row")
        yield Static(f"RAG: {RAG_URL}", id="rag-url")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_column("Status", key=COL_STATUS, width=8)
        table.add_column("ID", key=COL_ID, width=10)
        table.add_column("Name", key=COL_NAME)
        table.display = False
        self._fetch_data()

    @work(exclusive=True, group="fetch")
    async def _fetch_data(self) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            cf_contests, loaded_ids = await self._fetch_both(client)

        self._contests = [
            {"id": str(c["id"]), "name": c["name"]}
            for c in cf_contests
            if c.get("phase") == "FINISHED"
        ]
        self._contests.sort(key=lambda c: int(c["id"]), reverse=True)
        self._loaded_ids = set(loaded_ids)
        self._rebuild_table()

    async def _fetch_both(self, client: httpx.AsyncClient) -> tuple[list[dict], list[str]]:
        try:
            cf_response = await client.get(CF_API_URL)
            cf_response.raise_for_status()
            cf_data = cf_response.json()
            contests = cf_data.get("result", [])
        except Exception:
            contests = []

        try:
            loaded_response = await client.get(f"{RAG_URL}/contests/loaded")
            loaded_response.raise_for_status()
            loaded = loaded_response.json()
        except Exception:
            loaded = []

        return contests, loaded

    def _rebuild_table(self) -> None:
        self.query_one(LoadingIndicator).display = False
        table = self.query_one(DataTable)
        table.display = True
        table.clear()

        for contest in self._contests:
            cid = contest["id"]
            if cid in self._loading_ids:
                status = STATUS_LOADING
            elif cid in self._loaded_ids:
                status = STATUS_LOADED
            else:
                status = STATUS_EMPTY
            table.add_row(status, cid, contest["name"], key=cid)

        self.sub_title = f"{len(self._contests)} contests, {len(self._loaded_ids)} loaded"
        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        contest_id = str(event.row_key.value)

        if contest_id in self._loaded_ids or contest_id in self._loading_ids:
            return

        self._loading_ids.add(contest_id)
        self._update_row_status(contest_id, STATUS_LOADING)
        self._do_load_contest(contest_id)

    @work(thread=False)
    async def _do_load_contest(self, contest_id: str) -> None:
        try:
            url = f"https://codeforces.com/contest/{contest_id}"
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{RAG_URL}/contests/load",
                    json={"contest_url": url},
                )
                response.raise_for_status()
            self._loading_ids.discard(contest_id)
            self._loaded_ids.add(contest_id)
            self._update_row_status(contest_id, STATUS_LOADED)
            self.sub_title = f"{len(self._contests)} contests, {len(self._loaded_ids)} loaded"
        except Exception:
            self._loading_ids.discard(contest_id)
            self._update_row_status(contest_id, STATUS_ERROR)

    def _update_row_status(self, contest_id: str, status: str) -> None:
        table = self.query_one(DataTable)
        table.update_cell(contest_id, COL_STATUS, status)

    def action_refresh(self) -> None:
        self.query_one(LoadingIndicator).display = True
        self.query_one(DataTable).display = False
        self._fetch_data()

    def action_quit(self) -> None:
        self.exit()


def main():
    app = ContestLoaderApp()
    app.run()


if __name__ == "__main__":
    main()
