# Visual Instruction Tuning 调研报告

## 1. 代表性论文表格

| 论文标题 | 年份 | 方法 | 数据集 | 代码链接 | 论文下载链接 | 主要贡献 |
|---------|------|------|--------|----------|--------------|----------|
| Visual Instruction Tuning | 2023 | GPT-4生成多模态指令数据，视觉编码器+LLM端到端训练 | ScienceQA, LLaVA-Bench | [Code](https://llava-vl.github.io) | [PDF](https://openreview.net/pdf?id=w0H2xGHlkw) | 首次用纯语言GPT-4生成多模态指令数据，提出LLaVA模型 |
| Visual Instruction Tuning towards General-Purpose Multimodal Model: A Survey | 2023 | 系统综述视觉指令调优方法，按视觉任务和方法设计分类 | MiniGPT-4, Clotho-Detail, VGGSS-Instruction | 无 | [PDF](https://arxiv.org/pdf/2312.16602v1.pdf) | 首次系统梳理视觉指令调优领域，提出分类框架 |
| From Factors to Methods: A Comprehensive Survey on Visual Instruction Tuning Data Selection | 2024 | 基于因子的数据分析框架，特征/预测/梯度/混合四类数据选择方法 | LLaVA-1.5, SVIT-Mix, Cambrian-7M, Vision-Flan | 无 | [PDF](https://openreview.net/pdf?id=JVrTvE3QEi) | 首次统一视觉指令数据选择评估标准 |
| Visual Instruction Tuning with Polite Flamingo | 2024 | U形多阶段调优管道，多轮增强响应礼貌性 | 37个数据集整合（见附录） | 无 | [PDF](https://ojs.aaai.org/index.php/AAAI/article/view/29727/31249) | 构建基于响应改写的大规模指令数据集 |
| Inst-IT | 2024 | 显式视觉提示指令调优，GPT-4o辅助实例标注 | Inst-IT Bench | 无 | [PDF](https://inst-it.github.io/) | 首个含显式实例级视觉提示的指令数据集 |
| Comparison Visual Instruction Tuning | 2025 | CaD-VI两阶段数据收集，自改进增强差异发现 | CaD-Inst, CaD-QA | 无 | [PDF](https://openaccess.thecvf.com/content/CVPR2025W/MAR/papers/Lin_Comparison_Visual_Instruction_Tuning_CVPRW_2025_paper.pdf) | 提出图像共性与差异分析框架 |

## 2. Benchmark 对比表

| Benchmark名称 | 年份 | 数据类型 | 规模 | 评估维度 | 相关论文 |
|--------------|------|----------|------|----------|----------|
| LLaVA-Bench | 2023 | 多模态QA | 未明确 | 视觉推理能力 | Visual Instruction Tuning (2023) |
| Inst-IT Bench | 2024 | 实例级标注 | 未明确 | 空间-时间实例理解 | Inst-IT (2024) |
| CaD-Inst/CaD-QA | 2025 | 图像对比对 | 349K+7.5K | 差异分析能力 | Comparison Visual Instruction Tuning (2025) |

## 3. SOTA 趋势总结

1. **数据生成范式革新**：从人工标注转向LLM生成（如GPT-4生成多模态指令数据），2023年LLaVA达到92.53% SOTA准确率  
2. **评估维度扩展**：从基础视觉QA发展到实例级理解（Inst-IT）和差异分析（CaD-VI），2024-2025年新Benchmark涌现  
3. **调优目标多元化**：从性能优化转向礼貌性增强（Polite Flamingo）、个性化对话（PVIT）等用户体验维度  

## 4. 方法分类

1. **数据生成型**  
   - GPT-4辅助生成（LLaVA）  
   - 响应改写增强（Polite Flamingo）  
   - 实例级提示标注（Inst-IT）  

2. **架构设计型**  
   - 视觉编码器+LLM端到端训练（LLaVA）  
   - U形多阶段调优管道（Polite Flamingo）  

3. **评估框架型**  
   - 基于因子的数据选择（Factors to Methods Survey）  
   - 图像对比分析框架（CaD-VI）  

## 5. 选题建议

1. **动态视觉指令调优**  
   - 研究视频流场景下的实时指令跟随机制，结合GPT-4o的时序理解能力  

2. **多模态指令数据质量评估**  
   - 构建量化评估指标库，解决当前LLM生成数据的可信度验证问题  

3. **节能型轻量调优**  
   - 探索参数高效调优方法（如LoRA适配器）在视觉-语言联合模型中的应用

---

## 附录：Agent 运行统计

- 搜索轮次：3
- 提取论文数：9
- 反思奖励分数：[0.7254545454545455, 0.7254545454545455, 0.6, 0.6883333333333334, 0.7254545454545455, 0.7254545454545455, 0.6, 0.6883333333333334, 0.5, 0.7355555555555555, 0.7254545454545455, 0.7254545454545455, 0.6, 0.6883333333333334, 0.7254545454545455, 0.7254545454545455, 0.6, 0.6883333333333334, 0.5, 0.7355555555555555, 0.4]
- 平均奖励：0.66
