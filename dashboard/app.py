import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# --------------------------------------------------
# PROJECT PATH
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

sys.path.append(str(BASE_DIR))

from ai_engine.priority_engine import calculate_priority

from block_planner.block_planner import (
    load_data,
    prepare_tasks,
    create_block_options,
    select_best_blocks,
    generate_task_status,
    calculate_planning_metrics
)

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="AI Railway Block Planner",
    page_icon="🚆",
    layout="wide"
)

# --------------------------------------------------
# TITLE
# --------------------------------------------------

st.title("🚆 AI Railway Block Planner")

st.caption(
    "AI-powered automatic block planning to maximize asset availability"
)

st.divider()

# --------------------------------------------------
# LOAD DATA AND RUN AI PLANNER
# --------------------------------------------------

try:

    # Load railway data
    tasks, assets, blocks, trains = load_data()

    # Calculate AI priority scores
    priority_data = calculate_priority()

    # Add priority score to maintenance tasks
    tasks = tasks.merge(
        priority_data[["task_id", "priority_score"]],
        on="task_id",
        how="left"
    )

    # Add asset location and criticality
    tasks = prepare_tasks(
        tasks,
        assets
    )

    # Find compatible task-block combinations
    options = create_block_options(
        tasks,
        blocks,
        trains
    )

    # Select best task combination for each block
    selected_blocks = select_best_blocks(
        options
    )

    # Generate scheduling status
    task_status = generate_task_status(
        tasks,
        options,
        selected_blocks
    )

    # Calculate planning metrics
    metrics = calculate_planning_metrics(
        tasks,
        selected_blocks
    )

except Exception as e:

    st.error(
        "Unable to load the AI planning engine."
    )

    st.exception(e)

    st.stop()


# ==================================================
# KPI CARDS
# ==================================================

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Total Maintenance Tasks",
        metrics["total_tasks"]
    )

with col2:

    st.metric(
        "Scheduled Tasks",
        metrics["scheduled_tasks"]
    )

with col3:

    st.metric(
        "Blocks Used",
        metrics["blocks_used"]
    )

with col4:

    st.metric(
        "Block Utilization",
        f'{metrics["block_utilization_percent"]}%'
    )

st.divider()


# ==================================================
# AI DECISION SUMMARY
# ==================================================

st.subheader("🤖 AI Decision")

if not selected_blocks.empty:

    best = selected_blocks.iloc[0]

    st.success(
        f"AI selected Task {best['task_id']} "
        f"({best['asset_id']}) for Block "
        f"{best['block_id']} in {best['zone']} "
        f"from {best['block_start']} "
        f"to {best['block_end']}."
    )

    decision_col1, decision_col2, decision_col3 = st.columns(3)

    with decision_col1:

        st.metric(
            "Selected Task Priority",
            int(best["priority_score"])
        )

    with decision_col2:

        st.metric(
            "Maintenance Duration",
            f"{int(best['duration_minutes'])} min"
        )

    with decision_col3:

        st.metric(
            "Available Block",
            f"{int(best['block_duration'])} min"
        )

else:

    st.warning(
        "No feasible maintenance block was found."
    )


st.divider()


# ==================================================
# HOW AI MADE THE DECISION
# ==================================================

st.subheader(
    "⚙️ How the AI Made the Decision"
)

flow1, flow2, flow3, flow4 = st.columns(4)

with flow1:

    st.markdown("### 1️⃣ Priority")

    st.write(
        "Ranks maintenance tasks using "
        "severity, asset criticality and urgency."
    )

with flow2:

    st.markdown("### 2️⃣ Block Match")

    st.write(
        "Finds blocks matching the task "
        "zone, duration and due date."
    )

with flow3:

    st.markdown("### 3️⃣ Safety Check")

    st.write(
        "Rejects blocks that conflict "
        "with scheduled train movements."
    )

with flow4:

    st.markdown("### 4️⃣ Optimization")

    st.write(
        "Selects the highest-value task "
        "combination within block capacity."
    )

st.info(
    "AI recommendation: prioritize high-urgency "
    "maintenance, avoid train conflicts, respect "
    "block capacity, and maximize maintenance value "
    "within available blocks."
)
if not selected_blocks.empty:
    selected_task_id = selected_blocks.iloc[0]["task_id"]

    selected_priority = priority_data[
        priority_data["task_id"] == selected_task_id
    ].iloc[0]

    st.subheader("🔍 Why AI Selected This Task")

    reason_col1, reason_col2, reason_col3 = st.columns(3)

    with reason_col1:
        st.metric(
            "Severity",
            selected_priority["severity"]
        )

    with reason_col2:
        st.metric(
            "Asset Criticality",
            int(selected_priority["criticality"])
        )

    with reason_col3:
        st.metric(
            "Days Until Due",
            int(selected_priority["days_until_due"])
        )

    st.caption(
        f"Task {selected_task_id} received an AI priority score of "
        f"{int(selected_priority['priority_score'])} based on "
        "maintenance severity, asset criticality and deadline urgency."
    )

st.divider()


# ==================================================
# RECOMMENDED BLOCK PLAN
# ==================================================

st.subheader(
    "🧠 AI Recommended Block Plan"
)

if selected_blocks.empty:

    st.warning(
        "No maintenance tasks could be scheduled."
    )

else:

    display_blocks = selected_blocks[
        [
            "task_id",
            "asset_id",
            "department",
            "zone",
            "duration_minutes",
            "priority_score",
            "block_id",
            "block_date",
            "block_start",
            "block_end"
        ]
    ].copy()

    display_blocks.columns = [
        "Task",
        "Asset",
        "Department",
        "Zone",
        "Duration (min)",
        "AI Priority",
        "Block",
        "Date",
        "Start",
        "End"
    ]

    st.dataframe(
        display_blocks,
        width="stretch",
        hide_index=True
    )

st.divider()


# ==================================================
# MAINTENANCE TASK STATUS
# ==================================================

st.subheader(
    "📋 Maintenance Task Status"
)

status_display = task_status[
    [
        "task_id",
        "asset_id",
        "priority_score",
        "status",
        "reason"
    ]
].copy()

status_display.columns = [
    "Task",
    "Asset",
    "AI Priority",
    "Status",
    "Planning Explanation"
]

st.dataframe(
    status_display,
    width="stretch",
    hide_index=True
)

st.divider()


# ==================================================
# AI PRIORITY RANKING
# ==================================================

st.subheader(
    "🤖 AI Maintenance Priority Ranking"
)


# --------------------------------------------------
# PRIORITY SCORE CHART
# --------------------------------------------------

chart_data = priority_data[
    [
        "task_id",
        "priority_score"
    ]
].copy()

chart_data = chart_data.set_index(
    "task_id"
)

st.bar_chart(
    chart_data,
    y="priority_score",
    width="stretch"
)


# --------------------------------------------------
# PRIORITY TABLE
# --------------------------------------------------

priority_display = priority_data[
    [
        "task_id",
        "asset_id",
        "department",
        "severity",
        "due_date",
        "days_until_due",
        "criticality",
        "priority_score"
    ]
].copy()

priority_display.columns = [
    "Task",
    "Asset",
    "Department",
    "Severity",
    "Due Date",
    "Days Until Due",
    "Asset Criticality",
    "AI Priority Score"
]

st.dataframe(
    priority_display,
    width="stretch",
    hide_index=True
)

st.divider()


# ==================================================
# PLANNING SUMMARY
# ==================================================

st.subheader(
    "📊 Planning Summary"
)

summary_col1, summary_col2 = st.columns(2)


# --------------------------------------------------
# MAINTENANCE OVERVIEW
# --------------------------------------------------

with summary_col1:

    st.write(
        "**Maintenance Overview**"
    )

    st.write(
        f"Total tasks: "
        f"**{metrics['total_tasks']}**"
    )

    st.write(
        f"Scheduled: "
        f"**{metrics['scheduled_tasks']}**"
    )

    st.write(
        f"Unscheduled: "
        f"**{metrics['unscheduled_tasks']}**"
    )


# --------------------------------------------------
# BLOCK UTILIZATION
# --------------------------------------------------

with summary_col2:

    st.write(
        "**Block Utilization**"
    )

    st.write(
        f"Scheduled maintenance time: "
        f"**{metrics['scheduled_minutes']} minutes**"
    )

    st.write(
        f"Total available block capacity: "
        f"**{metrics['block_capacity_minutes']} minutes**"
    )
    st.write(
    f"Block utilization: "
    f"**{metrics['block_utilization_percent']}%**"
)

    st.progress(
        min(
            metrics["block_utilization_percent"] / 100,
            1.0
        )
    )


st.divider()


# ==================================================
# FOOTER
# ==================================================

st.caption(
    "AI Railway Block Planning System • Hackathon MVP"
)