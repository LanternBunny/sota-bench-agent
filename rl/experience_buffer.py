import json
import os

BUFFER_PATH = "outputs/experience_buffer.json"


class ExperienceBuffer:
    def __init__(self, max_size: int = 50):
        self.max_size = max_size
        self.buffer: list[dict] = []
        self._load()

    def _load(self):
        if os.path.exists(BUFFER_PATH):
            try:
                with open(BUFFER_PATH, "r", encoding="utf-8") as f:
                    self.buffer = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.buffer = []

    def _save(self):
        os.makedirs(os.path.dirname(BUFFER_PATH), exist_ok=True)
        with open(BUFFER_PATH, "w", encoding="utf-8") as f:
            json.dump(self.buffer, f, ensure_ascii=False, indent=2)

    def add(self, trajectory: dict, reward: float):
        self.buffer.append({"trajectory": trajectory, "reward": reward})
        self.buffer.sort(key=lambda x: x["reward"], reverse=True)
        self.buffer = self.buffer[:self.max_size]
        self._save()

    def sample_best(self, k: int = 3) -> list[dict]:
        return self.buffer[:k]

    def get_few_shot_prompt(self, k: int = 2) -> str:
        best = self.sample_best(k)
        if not best:
            return ""

        examples = []
        for ex in best:
            t = ex["trajectory"]
            examples.append(
                f"- 主题: {t.get('topic', '?')}, "
                f"查询策略: {t.get('queries', [])}, "
                f"论文数: {t.get('paper_count', 0)}, "
                f"奖励: {ex['reward']:.2f}"
            )
        return "参考以下成功案例：\n" + "\n".join(examples)


experience_buffer = ExperienceBuffer()
