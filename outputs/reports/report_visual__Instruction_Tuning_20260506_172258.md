# Visual Instruction Tuning 调研报告

## 1. 代表性论文表格

| 论文标题 | 年份 | 方法 | 数据集 | 代码链接 | 论文下载链接 | 主要贡献 |
|---------|------|------|--------|----------|--------------|----------|
| Comparison Visual Instruction Tuning - OpenReview | 2024 | CaD-VI：收集合成视觉指令的两阶段方法 | CaD-Inst, CaD-QA | [GitHub](https://github.com/haotian-liu/LLaVA) | [PDF](https://openreview.net/pdf?id=dhuQJseaBA) | 提出CaD-VI方法和CaD-Inst数据集，提升LMMs在CaD推理能力17.5% |
| Visual Instruction Tuning | 2023 | 使用GPT-4生成多模态语言-图像指令跟随数据 | ScienceQA, LLaVA-Bench | [Website](https://llava-vl.github.io) | [PDF](https://proceedings.neurips.cc/paper_files/paper/2023/file/6dcf277ea32ce3288914faf369fe6de0-Paper-Conference.pdf) | 首次用GPT-4生成多模态指令数据，LLaVA在ScienceQA达92.53% SOTA |
| Vision-Language Instruction Tuning: A Review and Analysis | 2024 | 系统回顾VLIT设置和数据集 | LLaVA, BLIP-2等 | [GitHub](https://github.com/palchenli/VL-Instruction-Tuning) | [PDF](https://openreview.net/pdf?id=ul2tbUPtIQ) | 首次提供VLIT数据集多视角分类，识别高质量数据特征 |
| LLaVA Steering: Visual Instruction Tuning with 500x Fewer... | 2025 | MoReS：通过线性变换引导视觉表示 | LLaVA-665K等 | [GitHub](https://github.com/bibisbar/LLaV A-Steering) | [PDF](https://aclanthology.org/2025.acl-long.739.pdf) | 提出MoReS方法减少500倍可训练参数 |
| Osprey: Pixel Understanding with Visual Instruction Tuning | 2024 | 像素级理解的视觉指令微调 | Osprey-724K等 | [GitHub](https://github.com/CircleRadon/Osprey) | [PDF](https://openaccess.thecvf.com/content/CVPR2024/papers/Yuan_Osprey_Pixel_Understanding_with_Visual_Instruction_Tuning_CVPR_2024_paper.pdf) | 增强像素级理解能力 |
| Visual Instruction Tuning towards General-Purpose... | 2025 | 系统综述视觉指令微调方法 | 多领域数据集 | 无 | [PDF](https://arxiv.org/pdf/2312.16602v1.pdf) | 提供系统性综述填补研究空白 |

## 2. Benchmark对比表

| Benchmark名称 | 数据集规模 | 评估维度 | 当前SOTA模型 | SOTA指标 |
|--------------|------------|----------|--------------|----------|
| ScienceQA | 21K多模态选择题 | 多模态推理 | LLaVA (2023) | 92.53% |
| CaD-QA | 7.5K开放QA | 共性与差异推理 | CaD-VI (2024) | +17.5%提升 |
| LLaVA-Bench | 30图像生成90问题 | 开放域理解 | LLaVA (2023) | 未明确 |

## 3. SOTA趋势总结

1. **数据生成范式革新**：从GPT-4生成多模态指令数据（LLaVA）到两阶段合成方法（CaD-VI），数据质量成为性能突破关键  
2. **轻量化技术崛起**：MoReS等方法通过参数效率优化（500倍减少）推动边缘部署  
3. **细粒度理解发展**：像素级（Osprey）和领域专用（VIT-Pro）模型成为新方向  
4. **评估体系完善**：从单一QA向共性与差异推理（CaD-QA）等复杂评估维度扩展  
5. **跨模态对齐深化**：视觉表示引导（LLaVA Steering）和瓶颈调整（VITTLE）成为技术焦点  

## 4. 方法分类

### 4.1 数据生成方法
- **LLM辅助生成**：利用GPT-4生成语言-图像对齐数据（LLaVA）
- **两阶段合成**：先收集再精炼的CaD-VI方法
- **领域自适应**：电商专用数据生成（VIT-Pro）

### 4.2 模型优化方法
- **参数高效微调**：MoReS的子空间引导、VITTLE的瓶颈调整
- **多模态对齐**：视觉表示与语言模型的投影层优化
- **像素级建模**：Osprey的密集预测架构

### 4.3 评估方法论
- **开放域QA基准**：LLaVA-Bench的in-the-wild评估
- **专业能力测试**：CaD-QA的差异推理评估
- **多任务统一**：MMMU等综合基准

## 5. 选题建议

1. **动态视觉指令生成**  
   研究基于在线学习的指令数据迭代优化框架，解决当前静态数据集的分布偏移问题，可结合强化学习进行数据质量自动评估

2. **多模态指令压缩**  
   开发视觉-语言联合token压缩技术，针对长视觉指令场景（如视频理解）设计分层表示方法，平衡信息密度与计算效率

3. **因果推理增强**  
   在现有CaD推理基础上构建反事实视觉指令数据集，探索LMMs在视觉因果推理中的可解释性提升路径

---

## 附录：Agent 运行统计

- 搜索轮次：3
- 提取论文数：12
- 反思奖励分数：[0.6749999999999999, 0.6749999999999999, 0.6, 0.6706666666666667, 0.6749999999999999, 0.6749999999999999, 0.6, 0.6706666666666667, 0.5, 0.6907692307692308, 0.6749999999999999, 0.6749999999999999, 0.6, 0.6706666666666667, 0.6749999999999999, 0.6749999999999999, 0.6, 0.6706666666666667, 0.5, 0.6907692307692308, 0.4]
- 平均奖励：0.63
