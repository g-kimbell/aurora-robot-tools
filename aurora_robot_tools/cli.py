"""Command line interface for robot tools."""
from typer import Typer

from aurora_robot_tools.import_excel import main as import_excel_main
from aurora_robot_tools.assign_cells_to_press import main as assign_main
app = Typer()

@app.command()
def import_excel() -> None:
    """Import excel file and load into robot database."""
    import_excel_main()

@app.command()
def backup() -> None:
    """Backup the robot database."""
    raise NotImplementedError

@app.command()
def balance(mode: int) -> None:
    """Perform electrode balancing."""
    print(f"Received mode: {mode}")
    raise NotImplementedError

@app.command()
def assign(link: bool = True, elyte_limit: int = 0) -> None:
    """Assign cells to presses."""
    assign_main(link, elyte_limit)

@app.command()
def photo(step_number: int) -> None:
    """Save a photo of the pressing tools."""
    print(f"Received step number {step_number}")
    raise NotImplementedError

@app.command()
def output() -> None:
    """Output sample details to JSON."""
    raise NotImplementedError

if __name__ == "__main__":
    app()
