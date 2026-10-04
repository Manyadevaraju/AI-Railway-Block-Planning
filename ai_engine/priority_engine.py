import pandas as pd
from pathlib import Path
from datetime import date


# Find the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Location of railway data
DATA_DIR = BASE_DIR / "data"


def calculate_priority():
    # Load maintenance tasks
    tasks_file = DATA_DIR / "maintenance_tasks.csv"
    tasks = pd.read_csv(tasks_file)

    # Load asset information
    assets_file = DATA_DIR / "assets.csv"
    assets = pd.read_csv(assets_file)

    # Combine maintenance tasks with asset information
    data = tasks.merge(
        assets[["asset_id", "criticality"]],
        on="asset_id",
        how="left"
    )

    # Convert severity into numerical score
    severity_scores = {
        "Critical": 40,
        "High": 30,
        "Medium": 20,
        "Low": 10
    }

    data["severity_score"] = data["severity"].map(severity_scores)

    # Convert due date to date format
    data["due_date"] = pd.to_datetime(data["due_date"]).dt.date

    # Today's date
    today = date(2026,10,5)

    # Calculate days remaining until maintenance is due
    data["days_until_due"] = (
        data["due_date"] - today
    ).apply(lambda x: x.days)

    # Calculate urgency score
    def calculate_urgency(days):
        if days < 0:
            return 40       # Already overdue
        elif days == 0:
            return 35       # Due today
        elif days <= 2:
            return 25       # Due within 2 days
        elif days <= 5:
            return 15       # Due within 5 days
        else:
            return 5        # More than 5 days away

    data["urgency_score"] = data["days_until_due"].apply(
        calculate_urgency
    )

    # Calculate final priority score
    data["priority_score"] = (
        data["severity_score"]
        + (data["criticality"] * 10)
        + data["urgency_score"]
    )

    # Sort highest priority first
    data = data.sort_values(
        by="priority_score",
        ascending=False
    )

    return data


if __name__ == "__main__":
    result = calculate_priority()

    print("\nAI MAINTENANCE PRIORITY RESULTS")
    print("=" * 70)

    print(
        result[
            [
                "task_id",
                "asset_id",
                "department",
                "severity",
                "due_date",
                "days_until_due",
                "criticality",
                "urgency_score",
                "priority_score"
            ]
        ].to_string(index=False)
    )