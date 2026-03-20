"""LinkedinTouch CLI — orchestrate scraping, message generation, and sending."""
import asyncio
import json
import signal
import sys
import logging

import click
from rich.console import Console
from rich.table import Table

import config
import db.repo as repo
from db.schema import init_db
from utils import setup_logging

console = Console()
logger = logging.getLogger(__name__)

# ── Graceful shutdown ────────────────────────────────────────────────────────

_current_prospect_id: int | None = None


def _handle_sigint(sig, frame):
    if _current_prospect_id is not None:
        logger.warning("SIGINT received — marking prospect %d as skipped.", _current_prospect_id)
        repo.set_prospect_status(_current_prospect_id, "skipped")
    console.print("\n[yellow]Interrupted. Goodbye.[/yellow]")
    sys.exit(0)


signal.signal(signal.SIGINT, _handle_sigint)

# ── CLI ──────────────────────────────────────────────────────────────────────


@click.group()
def cli():
    """LinkedinTouch — LinkedIn cold outreach automation."""
    setup_logging()
    init_db()


@cli.command()
@click.option("--limit", default=20, show_default=True, help="Max profiles to scrape.")
def scrape(limit: int):
    """Scrape LinkedIn search results and save prospects to the database."""
    asyncio.run(_scrape(limit))


async def _scrape(limit: int):
    from playwright.async_api import async_playwright
    from auth.session import load_context
    from scraper.search import collect_profile_urls
    from scraper.profile import scrape_profile
    from scraper.rate_limiter import check_scrape_cap, DailyCapExceeded

    global _current_prospect_id

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await load_context(browser)
        page = await context.new_page()

        console.print(f"[cyan]Collecting up to {limit} profile URLs...[/cyan]")
        urls = await collect_profile_urls(page, limit=limit)
        console.print(f"[green]Found {len(urls)} profile URLs.[/green]")

        saved = 0
        for url in urls:
            try:
                check_scrape_cap()
            except DailyCapExceeded as e:
                console.print(f"[yellow]{e}[/yellow]")
                break

            profile = await scrape_profile(page, url)
            pid = repo.upsert_prospect(**profile)
            _current_prospect_id = pid
            repo.increment_scraped()
            saved += 1
            console.print(f"  [+] {profile['name']} ({profile['headline'][:50]})")

        console.print(f"[bold green]Scraped and saved {saved} prospects.[/bold green]")
        await browser.close()


def _has_cjk(text: str) -> bool:
    """Return True if text contains any CJK (Chinese/Japanese/Korean) characters."""
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _mock_message(profile: dict) -> str:
    """Return a sample message without calling OpenAI."""
    name = profile.get("name", "您好")
    company = profile.get("company", "貴公司")
    headline = profile.get("headline", "")
    location = profile.get("location", "")

    # Use Traditional Chinese if location keywords match OR company/name has Chinese characters
    is_tw_hk = any(kw in location for kw in ("Taiwan", "Hong Kong", "台灣", "香港", "Taipei", "臺北"))
    has_chinese = _has_cjk(company) or _has_cjk(name)

    if is_tw_hk or has_chinese:
        return (
            f"{name} 您好，看到您在 {company} 負責 {headline}，"
            f"ChainThink 專注加密專案的用戶增長與媒體廣告投放，"
            f"目前有協助多個 Web3 項目做冷啟動。"
            f"請問您目前在用戶增長上最大的挑戰是什麼？"
        )[:300]
    else:
        return (
            f"Hi {name}, saw you're leading {headline} at {company}. "
            f"ChainThink helps Web3 projects grow their user base through targeted media and growth campaigns. "
            f"What's your biggest acquisition challenge right now?"
        )[:300]


@cli.command()
@click.option("--mock", is_flag=True, default=False,
              help="Use sample messages instead of calling OpenAI (for testing).")
def generate(mock: bool):
    """Generate outreach messages for all new prospects."""
    import json as _json
    if not mock:
        from generator.generate import generate_message

    prospects = repo.get_pending_prospects()
    if not prospects:
        console.print("[yellow]No new prospects to generate messages for.[/yellow]")
        return

    label = "[MOCK]" if mock else ""
    console.print(f"[cyan]{label} Generating messages for {len(prospects)} prospects...[/cyan]")

    for prospect in prospects:
        profile = dict(prospect)
        try:
            profile["experiences"] = _json.loads(profile.get("experiences") or "[]")
        except Exception:
            profile["experiences"] = []

        try:
            msg = _mock_message(profile) if mock else generate_message(profile)
            repo.save_message(prospect["id"], msg)
            console.print(
                f"  [+] {prospect['name']} ({len(msg)} chars)\n"
                f"      [dim]{msg}[/dim]\n"
            )
        except Exception as exc:
            console.print(f"  [red]Failed for {prospect['name']}: {exc}[/red]")
            logger.error("generate failed for prospect %d: %s", prospect["id"], exc)

    console.print("[bold green]Done generating messages.[/bold green]")


@cli.command()
@click.option("--dry-run", is_flag=True, default=False, help="Simulate sending without clicking Send.")
def send(dry_run: bool):
    """Send pending messages (respects daily cap)."""
    asyncio.run(_send(dry_run))


async def _send(dry_run: bool):
    from playwright.async_api import async_playwright
    from auth.session import load_context
    from outreach.dispatcher import dispatch

    global _current_prospect_id

    messages = repo.get_pending_messages()
    if not messages:
        console.print("[yellow]No pending messages to send.[/yellow]")
        return

    if dry_run:
        console.print("[yellow][DRY RUN] No messages will actually be sent.[/yellow]")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await load_context(browser)
        page = await context.new_page()

        sent = failed = 0
        for msg in messages:
            _current_prospect_id = msg["prospect_id"]
            ok = await dispatch(
                page=page,
                prospect_id=msg["prospect_id"],
                profile_url=msg["profile_url"],
                message_text=msg["message_text"],
                message_id=msg["id"],
                dry_run=dry_run,
            )
            if ok:
                sent += 1
                console.print(f"  [green][OK][/green] {msg['name']}")
            else:
                failed += 1
                console.print(f"  [red][FAIL][/red] {msg['name']}")

        console.print(
            f"[bold]Done. Sent: {sent}, Failed: {failed}[/bold]"
            + (" [yellow](dry run)[/yellow]" if dry_run else "")
        )
        await browser.close()


@cli.command()
@click.option("--limit", default=20, show_default=True)
@click.option("--dry-run", is_flag=True, default=False)
def run(limit: int, dry_run: bool):
    """Full pipeline: scrape → generate → send."""
    asyncio.run(_run(limit, dry_run))


async def _run(limit: int, dry_run: bool):
    # Import inline to avoid circular issues
    from playwright.async_api import async_playwright
    from auth.session import load_context
    from scraper.search import collect_profile_urls
    from scraper.profile import scrape_profile
    from scraper.rate_limiter import check_scrape_cap, DailyCapExceeded
    from generator.generate import generate_message
    from outreach.dispatcher import dispatch

    global _current_prospect_id

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await load_context(browser)
        page = await context.new_page()

        # ── Scrape ──
        console.print(f"[cyan]Phase 1: Scraping up to {limit} profiles...[/cyan]")
        urls = await collect_profile_urls(page, limit=limit)

        prospect_ids = []
        for url in urls:
            try:
                check_scrape_cap()
            except DailyCapExceeded as e:
                console.print(f"[yellow]{e}[/yellow]")
                break

            profile = await scrape_profile(page, url)
            pid = repo.upsert_prospect(**profile)
            _current_prospect_id = pid
            repo.increment_scraped()
            prospect_ids.append(pid)
            console.print(f"  Scraped: {profile['name']}")

        # ── Generate ──
        console.print("\n[cyan]Phase 2: Generating messages...[/cyan]")
        import json as _json
        for prospect in repo.get_pending_prospects():
            profile = dict(prospect)
            try:
                profile["experiences"] = _json.loads(profile.get("experiences") or "[]")
            except Exception:
                profile["experiences"] = []

            try:
                msg = generate_message(profile)
                repo.save_message(prospect["id"], msg)
                console.print(f"  Generated for {prospect['name']}")
            except Exception as exc:
                console.print(f"  [red]Generate failed for {prospect['name']}: {exc}[/red]")

        # ── Send ──
        console.print("\n[cyan]Phase 3: Sending messages...[/cyan]")
        if dry_run:
            console.print("[yellow][DRY RUN][/yellow]")

        sent = failed = 0
        for msg in repo.get_pending_messages():
            _current_prospect_id = msg["prospect_id"]
            ok = await dispatch(
                page=page,
                prospect_id=msg["prospect_id"],
                profile_url=msg["profile_url"],
                message_text=msg["message_text"],
                message_id=msg["id"],
                dry_run=dry_run,
            )
            if ok:
                sent += 1
            else:
                failed += 1

        console.print(f"\n[bold green]Pipeline complete. Sent: {sent}, Failed: {failed}[/bold green]")
        await browser.close()


@cli.command("status")
def status_cmd():
    """Print a stats table of the current campaign."""
    stats = repo.get_stats()
    daily = repo.get_daily_counts()

    table = Table(title="LinkedinTouch — Campaign Status", show_header=True)
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")

    table.add_row("Prospects: new", str(stats["new"]))
    table.add_row("Prospects: messaged", str(stats["messaged"]))
    table.add_row("Prospects: skipped", str(stats["skipped"]))
    table.add_row("Prospects: failed", str(stats["failed"]))
    table.add_row("Messages sent (total)", str(stats["messages_sent"]))
    table.add_row("Messages failed (total)", str(stats["messages_failed"]))
    table.add_row("─" * 20, "─" * 6)
    table.add_row(f"Scraped today (cap {config.DAILY_SCRAPE_CAP})", str(daily["scraped"]))
    table.add_row(f"Messaged today (cap {config.DAILY_MESSAGE_CAP})", str(daily["messaged"]))

    console.print(table)


@cli.command("login")
def login_cmd():
    """Manually trigger LinkedIn login and save session."""
    asyncio.run(_login())


async def _login():
    from auth.login import login
    await login(headless=False)


if __name__ == "__main__":
    cli()
