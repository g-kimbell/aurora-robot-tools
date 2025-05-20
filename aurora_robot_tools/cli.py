"""Command line interface for robot tools."""

from typer import Argument, Typer

app = Typer(
    add_completion=False,
    pretty_exceptions_enable=False,
)


@app.command()
def import_excel() -> None:
    """Import excel file and load into robot database."""
    from aurora_robot_tools.import_excel import main as import_excel_main

    import_excel_main()


@app.command()
def electrolyte(safety_factor: float = Argument(1.1)) -> None:
    """Determine electrolyte mixing steps."""
    from aurora_robot_tools.electrolyte_calculation import main as electrolyte_main

    electrolyte_main(safety_factor)


@app.command()
def backup() -> None:
    """Backup the robot database."""
    from aurora_robot_tools.backup_database import main as backup_main

    backup_main()


@app.command()
def balance(mode: int = Argument(6)) -> None:
    """Perform electrode balancing."""
    from aurora_robot_tools.capacity_balance import main as balance_main

    balance_main(mode)


@app.command()
def assign(link: bool = Argument(True), elyte_limit: int = Argument(0)) -> None:  # noqa: FBT003
    """Assign cells to presses."""
    from aurora_robot_tools.assign_cells_to_press import main as assign_main

    assign_main(link, elyte_limit)


@app.command()
def startcam() -> None:
    """Start the camera daemon."""
    from aurora_robot_tools.camera.camera_daemon import main as startcam_main

    startcam_main()


@app.command()
def top_photo() -> None:
    """Save a photo of the pressing tools."""
    from aurora_robot_tools.camera.send_camera_command import main

    main("capturetop")


@app.command()
def bottom_photo() -> None:
    """Save a photo from the bottom-up alignment camera."""
    from aurora_robot_tools.camera.send_camera_command import main

    main("capturebottom")


@app.command()
def output() -> None:
    """Output the robot database to a JSON file."""
    from aurora_robot_tools.output_json import main as output_main

    output_main()

@app.command()
def led(setting: str) -> None:
    """Set the LED ring light color."""
    from aurora_robot_tools.camera.ringlight import set_light
    set_light(setting)

if __name__ == "__main__":
    app()
