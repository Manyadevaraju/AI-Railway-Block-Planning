import pandas as pd
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

sys.path.append(str(BASE_DIR))

from ai_engine.priority_engine import calculate_priority


def load_data():
    tasks = pd.read_csv(DATA_DIR / "maintenance_tasks.csv")
    assets = pd.read_csv(DATA_DIR / "assets.csv")
    blocks = pd.read_csv(DATA_DIR / "block_windows.csv")
    trains = pd.read_csv(DATA_DIR / "trains.csv")

    return tasks, assets, blocks, trains


def prepare_tasks(tasks, assets):
    tasks = tasks.merge(
        assets[["asset_id", "location", "criticality"]],
        on="asset_id",
        how="left"
    )

    tasks = tasks.rename(
        columns={"location": "zone"}
    )

    return tasks


def find_possible_blocks(task, blocks):
    simulation_date = pd.to_datetime("2026-10-05").date()
    task_due_date = pd.to_datetime(task["due_date"]).date()

    blocks = blocks.copy()
    blocks["date"] = pd.to_datetime(blocks["date"]).dt.date

    possible_blocks = blocks[
        (blocks["zone"] == task["zone"]) &
        (blocks["duration_minutes"] >= task["duration_minutes"]) &
        (blocks["status"] == "Available") &
        (blocks["date"] >= simulation_date) &
        (blocks["date"] <= task_due_date)
    ]

    return possible_blocks


def check_train_conflict(block, trains):
    for _, train in trains.iterrows():

        if train["zone"] != block["zone"]:
            continue

        if (
            block["start_time"] < train["departure_time"]
            and block["end_time"] > train["arrival_time"]
        ):
            return True

    return False
def select_best_blocks(options):
    if options.empty:
        return options

    selected_rows = []

    for block_id, block_group in options.groupby("block_id"):

        block_capacity = block_group["block_duration"].iloc[0]

        # Try every possible combination of tasks for this block.
        best_group = None
        best_score = float("-inf")
        best_duration = 0

        task_rows = list(block_group.iterrows())

        from itertools import combinations

        for r in range(1, len(task_rows) + 1):

            for combination in combinations(task_rows, r):

                combination_rows = [row for _, row in combination]

                total_duration = sum(
                    row["duration_minutes"]
                    for row in combination_rows
                )
                total_priority = sum(
                    row["priority_score"]
                    for row in combination_rows
                )
                utilization_bonus = (total_duration / block_capacity) * 20 
                optimization_score = (
    total_priority + utilization_bonus
    )
                if total_duration <= block_capacity:
                    if (
        optimization_score > best_score
        or (
            optimization_score == best_score
            and total_duration > best_duration
        )
    ):
                        best_group = combination_rows
                        best_score = optimization_score
                        best_duration = total_duration

        if best_group:
            selected_rows.extend(best_group)

    if not selected_rows:
        return pd.DataFrame(columns=options.columns)

    return pd.DataFrame(selected_rows)
def create_block_options(tasks, blocks, trains):
    options = []

    for _, task in tasks.iterrows():

        possible_blocks = find_possible_blocks(task, blocks)

        for _, block in possible_blocks.iterrows():

            train_conflict = check_train_conflict(block, trains)

            if train_conflict:
                continue

            options.append({
                "task_id": task["task_id"],
                "asset_id": task["asset_id"],
                "department": task["department"],
                "zone": task["zone"],
                "duration_minutes": task["duration_minutes"],
                "priority_score": task.get("priority_score", 0),
                "block_id": block["block_id"],
                "block_date": block["date"],
                "block_start": block["start_time"],
                "block_end": block["end_time"],
                "block_duration": block["duration_minutes"],
                "train_conflict": train_conflict
            })

    return pd.DataFrame(options)


def calculate_planning_metrics(tasks, selected_blocks):
    total_tasks = len(tasks)

    scheduled_tasks = len(selected_blocks)

    unscheduled_tasks = total_tasks - scheduled_tasks

    blocks_used = (
        selected_blocks["block_id"].nunique()
        if not selected_blocks.empty
        else 0
    )

    total_scheduled_minutes = (
        selected_blocks["duration_minutes"].sum()
        if not selected_blocks.empty
        else 0
    )

    total_block_capacity = (
        selected_blocks.drop_duplicates("block_id")["block_duration"].sum()
        if not selected_blocks.empty
        else 0
    )

    if total_block_capacity > 0:
        utilization = (
            total_scheduled_minutes / total_block_capacity
        ) * 100
    else:
        utilization = 0

    return {
        "total_tasks": total_tasks,
        "scheduled_tasks": scheduled_tasks,
        "unscheduled_tasks": unscheduled_tasks,
        "blocks_used": blocks_used,
        "scheduled_minutes": total_scheduled_minutes,
        "block_capacity_minutes": total_block_capacity,
        "block_utilization_percent": round(utilization, 2)
    }


def generate_task_status(tasks, options, selected_blocks):
    status_rows = []

    selected_task_ids = (
        set(selected_blocks["task_id"])
        if not selected_blocks.empty
        else set()
    )

    option_task_ids = (
        set(options["task_id"])
        if not options.empty
        else set()
    )

    for _, task in tasks.iterrows():

        task_id = task["task_id"]

        if task_id in selected_task_ids:
            status = "Scheduled"
            reason = "Selected by block planning engine"

        elif task_id not in option_task_ids:
            status = "Unscheduled"
            reason = "No compatible block available"

        else:
            status = "Unscheduled"
            reason = "Block capacity used by selected task"

        status_rows.append({
            "task_id": task_id,
            "asset_id": task["asset_id"],
            "priority_score": task["priority_score"],
            "status": status,
            "reason": reason
        })

    return pd.DataFrame(status_rows)


if __name__ == "__main__":

    tasks, assets, blocks, trains = load_data()

    priority_data = calculate_priority()

    tasks = tasks.merge(
        priority_data[["task_id", "priority_score"]],
        on="task_id",
        how="left"
    )

    tasks = prepare_tasks(tasks, assets)

    options = create_block_options(
        tasks,
        blocks,
        trains
    )

    selected_blocks = select_best_blocks(options)

    print("\nPOSSIBLE BLOCK OPTIONS")
    print("=" * 80)

    if options.empty:
        print("No compatible block options found.")
    else:
        print(options.to_string(index=False))

    print("\nRECOMMENDED BLOCK PLAN")
    print("=" * 80)

    if selected_blocks.empty:
        print("No tasks could be scheduled.")
    else:
        print(selected_blocks.to_string(index=False))

    task_status = generate_task_status(
        tasks,
        options,
        selected_blocks
    )

    print("\nTASK SCHEDULING STATUS")
    print("=" * 80)

    print(task_status.to_string(index=False))

    metrics = calculate_planning_metrics(
        tasks,
        selected_blocks
    )

    print("\nPLANNING METRICS")
    print("=" * 80)

    for key, value in metrics.items():
        print(f"{key}: {value}")