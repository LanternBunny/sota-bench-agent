# Visual Instruction Tuning 调研报告

## 1. 代表性论文表格

| 论文标题 | 年份 | 方法 | 数据集 | 代码链接 | 论文下载链接 | 主要贡献 |
|---------|------|------|--------|----------|--------------|----------|
| Visual Instruction Tuning | 2023 | 使用语言模型生成多模态语言-图像指令数据 | LLaVA-Bench, ScienceQA | [Code](https://llava-vl.github.io) | [PDF](https://openreview.net/pdf?id=w0H2xGHlkw) | 首次使用语言模型生成多模态指令数据，并引入LLaVA模型 |
| Comparison Visual Instruction Tuning | 2025 | CaD-VI方法 | CaD-Inst, CaD-QA | [Code](https://github.com/haotian-liu/LLaVA) | [PDF](https://openreview.net/pdf?id=dhuQJseaBA) | 提出CaD-VI方法用于合成视觉指令数据 |
| Visual Instruction Bottleneck Tuning | 2024 | 视觉指令瓶颈调优 | LB-COCO, POPE | [Code](https://github.com/deeplearning-wisc/vittle) | [PDF](https://openreview.net/pdf/2d2a34f6abce7b8d79210e69e53006394b61f953.pdf) | 优化多模态LLM性能的瓶颈调优方法 |
| LLaVA Steering: Visual Instruction Tuning with 500x Fewer... | 2025 | 模态线性表示引导 | LLaVA-665K, VQAv2等 | [Code](https://github.com/bibisbar/LLaVA-Steering) | [PDF](https://aclanthology.org/2025.acl-long.739.pdf) | 减少可训练参数数量的引导方法 |
| Visual Instruction Tuning towards General-Purpose Multimodal Model: A Survey | 2023 | 系统性综述 | MiniGPT-4等 | 无 | [PDF](https://arxiv.org/pdf/2312.16602v1.pdf) | 视觉指令调优的系统性综述 |
| Inst-IT | 2024 | 实例级视觉提示指令调优 | Inst-IT Bench | 无 | [PDF](https://inst-it.github.io/) | 实例级理解的基准和数据集 |
| Pre-Instruction Data Selection for Visual Instruction Tuning | 2025 | 预指令数据选择 | Vision-Flan | 无 | [PDF](https://openaccess.thecvf.com/content/CVPR2025/papers/Safaei_Filter_Images_First_Generate_Instructions_Later_Pre-Instruction_Data_Selection_for_CVPR_2025_paper.pdf) | 减少数据生成成本的预选择方法 |

## 2. Benchmark 对比表

| Benchmark名称 | 提出年份 | 主要任务类型 | 包含数据集 | SOTA指标 |
|--------------|----------|--------------|------------|----------|
| LLaVA-Bench | 2023 | 通用视觉语言理解 | ScienceQA等 | 92.53% |
| CaD-QA | 2025 | 合成视觉指令评估 | CaD-Inst | 17.5% |
| Inst-IT Bench | 2024 | 实例级理解 | 自定义数据集 | 未公开 |
| MMPI-Bench | 2024 | 产品图像理解 | 商业数据集 | 未公开 |

## 3. SOTA 趋势总结

1. **数据生成范式革新**：2023年后主流方法转向语言模型生成多模态指令数据（如LLaVA系列），显著降低人工标注成本  
2. **轻量化技术兴起**：2025年出现参数高效方法（如LLaVA Steering减少500x参数），推动边缘端部署  
3. **垂直领域专业化**：2024年后出现产品图像（VIT-Pro）、医学视觉等专用benchmark，反映应用场景分化  
4. **评估维度扩展**：从准确率单一指标（ScienceQA 92.53%）发展为实例级理解（Inst-IT）、幻觉检测（POPE）等多维度评估  

## 4. 方法分类

### 4.1 数据生成方法
- **语言模型生成**（LLaVA系列）：利用LLM生成图像-文本对指令数据  
- **合成数据构建**（CaD-VI）：通过程序化管道自动生成视觉指令数据  
- **预筛选优化**（Pre-Instruction）：先过滤低质量图像再生成指令  

### 4.2 模型优化方法
- **瓶颈调优**（Visual Instruction Bottleneck）：聚焦关键模块参数更新  
- **参数高效调优**（LLaVA Steering）：通过线性表示引导减少训练参数  
- **实例级提示**（Inst-IT）：增强细粒度对象理解能力  

## 5. 选题建议

1. **动态指令生成**  
   现有方法多采用静态指令数据，可探索基于用户反馈实时调整指令生成的强化学习框架，结合Human-in-the-loop机制提升交互适应性  

2. **多模态幻觉检测**  
   针对视觉-语言对齐中的幻觉问题，设计专用评估指标和抑制算法，可结合扩散模型生成对抗样本进行鲁棒性测试  

3. **跨模态知识蒸馏**  
   将视觉指令模型的能力蒸馏到纯语言模型中，研究如何通过提示工程让LLM获得"视觉想象"能力，适用于低算力场景

---

## 附录：Agent 运行统计

- 搜索轮次：3
- 提取论文数：17
- 反思奖励分数：[0.6938461538461538, 0.6938461538461538, 0.6, 0.7083333333333334, 0.6938461538461538, 0.6938461538461538, 0.6, 0.7083333333333334, 0.5, 0.72, 0.6938461538461538, 0.6938461538461538, 0.6, 0.7083333333333334, 0.6938461538461538, 0.6938461538461538, 0.6, 0.7083333333333334, 0.5, 0.72, 0.4]
- 平均奖励：0.65
