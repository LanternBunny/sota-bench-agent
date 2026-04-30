import json
import os
import time
import shutil
import logging
from datetime import datetime

import config as cfg
from graph import compile_graph
from evaluation.metrics import compute_metrics
from rl.experience_buffer import BUFFER_PATH

logger = logging.getLogger("ablation")

ABLATION_CONFIGS = {
    "full": {
        "use_best_of_n": True,
        "max_loops": cfg.MAX_SEARCH_LOOPS,
        "clear_experience": False,
        "label": "完整系统",
    },
    "no_reflexion": {
        "use_best_of_n": True,
        "max_loops": 1,
        "clear_experience": False,
        "label": "去掉反思循环",
    },
    "no_best_of_n": {
        "use_best_of_n": False,
        "max_loops": cfg.MAX_SEARCH_LOOPS,
        "clear_experience": False,
        "label": "去掉 Best-of-N",
    },
    "no_experience": {
        "use_best_of_n": True,
        "max_loops": cfg.MAX_SEARCH_LOOPS,
        "clear_experience": True,
        "label": "去掉经验回放",
    },
}

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "ablation_results.json")


def run_single(topic: str, config_name: str) -> dict:
    ac = ABLATION_CONFIGS[config_name]
    logger.info(f"[{config_name}] 开始: {topic}")

    original_max = cfg.MAX_SEARCH_LOOPS
    backup_path = None

    try:
        cfg.MAX_SEARCH_LOOPS = ac["max_loops"]

        if ac["clear_experience"] and os.path.exists(BUFFER_PATH):
            backup_path = BUFFER_PATH + ".bak"
            shutil.copy2(BUFFER_PATH, backup_path)
            with open(BUFFER_PATH, "w") as f:
                json.dump([], f)

        app = compile_graph(use_best_of_n=ac["use_best_of_n"])
        thread_id = f"ablation-{config_name}-{int(time.time())}"
        result = app.invoke(
            {"topic": topic, "loop_count": 0},
            {"configurable": {"thread_id": thread_id}},
        )

        metrics = compute_metrics(result)
        metrics["topic"] = topic
        metrics["config"] = config_name
        logger.info(f"[{config_name}] 完成: avg_reward={metrics['avg_reward']}, papers={metrics['paper_count']}")
        return metrics

    finally:
        cfg.MAX_SEARCH_LOOPS = original_max
        if backup_path and os.path.exists(backup_path):
            shutil.move(backup_path, BUFFER_PATH)


def run_ablation(
    topics: list[str],
    configs: list[str] | None = None,
    output_path: str | None = None,
) -> dict:
    if configs is None:
        configs = list(ABLATION_CONFIGS.keys())
    if output_path is None:
        output_path = RESULTS_PATH

    results = {c: [] for c in configs}

    for topic in topics:
        for config_name in configs:
            try:
                metrics = run_single(topic, config_name)
                results[config_name].append(metrics)
            except Exception as e:
                logger.error(f"[{config_name}] {topic} 失败: {e}")
                results[config_name].append({
                    "topic": topic,
                    "config": config_name,
                    "error": str(e),
                })

    output = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "topics": topics,
        "results": results,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(f"消融实验结果已保存: {output_path}")

    return output


def load_ablation_results(path: str | None = None) -> dict | None:
    path = path or RESULTS_PATH
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    topics = sys.argv[1:] if len(sys.argv) > 1 else ["multimodal hallucination detection"]
    print(f"运行消融实验，主题: {topics}")
    output = run_ablation(topics)
    print(f"\n实验完成，结果保存至: {RESULTS_PATH}")

    for config_name, runs in output["results"].items():
        label = ABLATION_CONFIGS[config_name]["label"]
        valid = [r for r in runs if "error" not in r]
        if valid:
            avg = sum(r["avg_reward"] for r in valid) / len(valid)
            print(f"  {label} ({config_name}): avg_reward={avg:.3f}")
        else:
            print(f"  {label} ({config_name}): 全部失败")
