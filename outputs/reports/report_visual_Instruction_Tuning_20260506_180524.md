# Visual Instruction Tuning 调研报告

## 1. 代表性论文表格

| 论文标题 | 年份 | 方法 | 数据集 | 代码链接 | 论文下载链接 | 主要贡献 |
|---------|------|------|--------|----------|--------------|----------|
| Visual Instruction Tuning | 2023 | GPT-4生成多模态指令数据 | LLaVA合成数据集 | [LLaVA](https://llava-vl.github.io) | [PDF](https://openreview.net/pdf?id=w0H2xGHlkw) | 首次实现纯语言模型生成视觉-语言指令数据 |
| Comparison Visual Instruction Tuning | 2025 | 图像差异感知指令调优 | CaD-QA Benchmark | 无 | [PDF](https://openaccess.thecvf.com/content/CVPR2025W/MAR/papers/Lin_Comparison_Visual_Instruction_Tuning_CVPRW_2025_paper.pdf) | 提升多模态模型图像差异识别能力 |
| Improved Baselines with Visual Instruction Tuning | 2024 | 视觉-语言连接器预训练 | 多任务评测基准 | 无 | [PDF](https://openaccess.thecvf.com/content/CVPR2024/papers/Liu_Improved_Baselines_with_Visual_Instruction_Tuning_CVPR_2024_paper.pdf) | 优化视觉指令调优的基础模型性能 |
| LLaVA Steering: Visual Instruction Tuning with 500x Fewer Parameters | 2025 | 模态线性表示导向(MoReS) | 多模态评测任务 | [LLaVA-Steering](https://github.com/bibisbar/LLaVA-Steering) | [PDF](https://aclanthology.org/2025.acl-long.739.pdf) | 通过表示空间控制实现高效视觉指令调优 |
| Osprey: Pixel Understanding with Visual Instruction Tuning | 2024 | 像素级指令调优 | 开放词汇识别等评测任务 | [Osprey](https://github.com/CircleRadon/Osprey) | [PDF](https://openaccess.thecvf.com/content/CVPR2024/papers/Yuan_Osprey_Pixel_Understanding_with_Visual_Instruction_Tuning_CVPR_2024_paper.pdf) | 实现多模态模型的像素级细粒度理解 |
| VisIT-Bench: A Benchmark for Vision-Language Instruction Following | 2023 | 多模态指令跟随评测框架 | VisIT-Bench | 无 | [PDF](https://proceedings.neurips.cc/paper_files/paper/2023/file/5503389dbe070cdae9b48086c4996a59-Paper-Datasets_and_Benchmarks.pdf) | 建立首个真实场景视觉指令跟随评测基准 |

## 2. Benchmark 对比表

| Benchmark名称 | 年份 | 评测维度 | 包含数据集 | 主要特点 |
|--------------|------|----------|------------|----------|
| VisIT-Bench | 2023 | 真实场景指令跟随 | VisIT-Bench | 首个面向实际应用场景的评测框架 |
| CaD-QA Benchmark | 2025 | 图像差异识别 | CaD-Inst, CaD-QA等 | 专注多模态模型对比分析能力 |
| LLaVA-Bench | 2023 | 多模态综合能力 | ScienceQA等 | 基于GPT-4生成指令的合成评测集 |

## 3. SOTA 趋势总结

1. **数据生成范式革新**：从人工标注转向LLM生成（如GPT-4生成LLaVA数据集），显著降低数据构建成本
2. **细粒度理解能力提升**：研究重点从整体图像理解转向像素级分析（如Osprey）和差异识别（如CaD-QA）
3. **效率优化成为焦点**：参数高效方法涌现（如MoReS实现500倍参数压缩）
4. **评测体系多元化**：从单一任务评测发展为真实场景综合评估（如VisIT-Bench）

## 4. 方法分类

1. **数据生成类**  
   - GPT-4合成指令（LLaVA）
   - 自主数据生成管道（PVIT）

2. **模型架构优化类**  
   - 视觉-语言连接器预训练（Improved Baselines）
   - 模态线性表示导向（MoReS）

3. **细粒度理解类**  
   - 像素级指令调优（Osprey）
   - 图像差异感知（Comparison Visual Instruction Tuning）

4. **评测框架类**  
   - 真实场景评测（VisIT-Bench）
   - 差异识别评测（CaD-QA）

## 5. 选题建议

1. **动态指令调优**  
   研究实时环境下的自适应视觉指令调优，结合强化学习实现交互式优化

2. **跨模态知识蒸馏**  
   探索视觉-语言模型向纯语言模型的知识迁移，提升单模态模型的视觉推理能力

3. **可信视觉指令系统**  
   开发具有可解释性和安全约束的视觉指令框架，包括幻觉检测和事实一致性验证

---

## 附录：Agent 运行统计

- 搜索轮次：3
- 提取论文数：12
- 反思奖励分数：[0.7085714285714285, 0.7085714285714285, 0.6, 0.7085714285714285, 0.7085714285714285, 0.7085714285714285, 0.6, 0.7085714285714285, 0.5, 0.7107692307692308, 0.7085714285714285, 0.7085714285714285, 0.6, 0.7085714285714285, 0.7085714285714285, 0.7085714285714285, 0.6, 0.7085714285714285, 0.5, 0.7107692307692308, 0.4]
- 平均奖励：0.65
