"""Command line interface for robot tools."""
from typer import Argument, Typer

from aurora_robot_tools.assign_cells_to_press import main as assign_main
from aurora_robot_tools.backup_database import main as backup_main
from aurora_robot_tools.capacity_balance import main as balance_main
from aurora_robot_tools.import_excel import main as import_excel_main
from aurora_robot_tools.output_json import main as output_main
from aurora_robot_tools.camera.capture_image import main as photo_main

app = Typer()

@app.command()
def import_excel() -> None:
    """Import excel file and load into robot database."""
    import_excel_main()

@app.command()
def backup() -> None:
    """Backup the robot database."""
    backup_main()

@app.command()
def balance(mode: int = Argument(6)) -> None:
    """Perform electrode balancing."""
    balance_main(mode)

@app.command()
def assign(link: bool = Argument(True), elyte_limit: int = Argument(0)) -> None:  # noqa: FBT003
    """Assign cells to presses."""
    assign_main(link, elyte_limit)

@app.command()
def photo() -> None:
    """Save a photo of the pressing tools."""
    photo_main()

@app.command()
def output() -> None:
    """Output the robot database to a JSON file."""
    output_main()

if __name__ == "__main__":
    app()
