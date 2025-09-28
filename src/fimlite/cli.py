from pathlib import Path
import typer
from rich.console import Console

app = typer.Typer(add_completion=False, help="FIMLite: File-Integrity Monitor")
console = Console()

@app.command()
def version():
    """Show the current version."""
    console.print("FIMLite v0.1.0")

@app.command()
def init(
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config file")
):
    """Create the baseline database and signature (implementation comes next)."""
    console.print(f"[bold]init[/] (stub) using config: {config}")

@app.command()
def scan(
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config file"),
    html: Path | None = typer.Option(None, "--html", help="Optional HTML report path"),
):
    """Scan and record changes (implementation comes next)."""
    console.print(f"[bold]scan[/] (stub) config={config} html={html}")

@app.command()
def verify():
    """Verify the baseline signature (implementation comes next)."""
    console.print("[bold]verify[/] (stub)")

@app.command("show")
def show_latest():
    """Show the latest run summary (implementation comes next)."""
    console.print("[bold]show latest[/] (stub)")

if __name__ == "__main__":
    app()
