"""Common configuration settings for the Aurora robot tools."""

from pathlib import Path

DATABASE_FILEPATH = Path("C:/Modules/Database/chemspeedDB.db")
DATABASE_BACKUP_DIR = Path("C:/Modules/Database/Backup/")
TIME_ZONE = "Europe/Zurich"
INPUT_DIR = Path("%userprofile%/Desktop/Inputs/")
OUTPUT_DIR = Path("%userprofile%/Desktop/Outputs/")
IMAGE_DIR = Path("C:/Aurora_images/")

# Current step definitions
STEP_DEFINITION = {
    10: {
        "Step": "Bottom",
        "Description": "Place bottom casing",
    },
    20: {
        "Step": "Spacer",
        "Description": "Place bottom spacer",
    },
    30: {
        "Step": "Anode",
        "Description": "Place anode face up",
    },
    40: {
        "Step": "Cathode",
        "Description": "Place cathode face up",
    },
    50: {
        "Step": "Electrolyte",
        "Description": "Add electrolyte before separator",
    },
    60: {
        "Step": "Separator",
        "Description": "Place separator",
    },
    70: {
        "Step": "Electrolyte",
        "Description": "Add electrolyte after separator",
    },
    80: {
        "Step": "Anode",
        "Description": "Place anode face down",
    },
    90: {
        "Step": "Cathode",
        "Description": "Place cathode face down",
    },
    100: {
        "Step": "Spacer",
        "Description": "Place top spacer",
    },
    110: {
        "Step": "Spring",
        "Description": "Place spring",
    },
    120: {
        "Step": "Top",
        "Description": "Place top casing",
    },
    130: {
        "Step": "Press",
        "Description": "Press cell using 7.8 kN hydraulic press",
    },
    140: {
        "Step": "Return",
        "Description": "Return completed cell to rack",
    },
}

# Step definitions from robot tools 0.1.x
STEP_DEFINITION_0_1 = {
    1: {
        "Step": "Bottom",
        "Description": "Place bottom casing",
    },
    2: {
        "Step": "Anode",
        "Description": "Place anode face up",
    },
    3: {
        "Step": "Electrolyte",
        "Description": "Add electrolyte before separator",
    },
    4: {
        "Step": "Separator",
        "Description": "Place separator",
    },
    5: {
        "Step": "Electrolyte",
        "Description": "Add electrolyte after separator",
    },
    6: {
        "Step": "Cathode",
        "Description": "Place cathode face down",
    },
    7: {
        "Step": "Spacer",
        "Description": "Place top spacer",
    },
    8: {
        "Step": "Spring",
        "Description": "Place spring",
    },
    9: {
        "Step": "Top",
        "Description": "Place top casing",
    },
    10: {
        "Step": "Press",
        "Description": "Press cell using 7.8 kN hydraulic press",
    },
    11: {
        "Step": "Return",
        "Description": "Return completed cell to rack",
    },
}
