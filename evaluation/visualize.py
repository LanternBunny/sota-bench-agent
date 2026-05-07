import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")


def plot_reward_curve(
    reward_scores: list[float],
    topic: str = "",
    save_path: str | None = None,
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 4))
    x = list(range(1, len(reward_scores) + 1))
    ax.plot(x, reward_scores, "o-", color="#4A90D9", linewidth=2, markersize=8)

    for i, v in enumerate(reward_scores):
        ax.annotate(f"{v:.3f}", (x[i], v), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=9)

    ax.set_xlabel("Iteration", fontsize=11)
    ax.set_ylabel("Reward Score", fontsize=11)
    ax.set_title(f"Reward Curve{f' — {topic}' if topic else ''}", fontsize=13)
    ax.set_xticks(x)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_experience_trend(
    history_path: str | None = None,
    save_path: str | None = None,
) -> plt.Figure:
    if history_path is None:
        history_path = os.path.join(OUTPUTS_DIR, "history.json")

    entries = []
    if os.path.exists(history_path):
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, IOError):
            entries = []

    entries = list(reversed(entries))

    fig, ax = plt.subplots(figsize=(8, 4))

    if not entries:
        ax.text(0.5, 0.5, "No history data", ha="center", va="center",
                fontsize=14, color="gray", transform=ax.transAxes)
        ax.set_title("Reward Trend Across Runs", fontsize=13)
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        return fig

    rewards = [e.get("avg_reward", 0) for e in entries]
    labels = [e.get("time", f"run-{i}") for i, e in enumerate(entries)]
    x = list(range(1, len(rewards) + 1))

    ax.plot(x, rewards, "s-", color="#50C878", linewidth=2, markersize=8)
    for i, v in enumerate(rewards):
        ax.annotate(f"{v:.3f}", (x[i], v), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Avg Reward", fontsize=11)
    ax.set_title("Reward Trend Across Runs (Experience Replay Effect)", fontsize=13)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


if __name__ == "__main__":
    os.makedirs(os.path.join(OUTPUTS_DIR, "figures"), exist_ok=True)

    fig1 = plot_reward_curve(
        [0.73, 0.78, 0.85],
        topic="multimodal hallucination detection",
        save_path=os.path.join(OUTPUTS_DIR, "figures", "reward_curve_demo.png"),
    )
    print(f"Saved reward_curve_demo.png")
    plt.close(fig1)

    fig2 = plot_experience_trend(
        save_path=os.path.join(OUTPUTS_DIR, "figures", "experience_trend.png"),
    )
    print(f"Saved experience_trend.png")
    plt.close(fig2)

    print("Done.")
