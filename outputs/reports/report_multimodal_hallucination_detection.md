# Multimodal Hallucination Detection Research Report

---

## 1. Representative Papers Table
| Title | Year | Method | Dataset | Code URL | Contribution |
|-------|------|--------|---------|----------|--------------|
| A Survey of Multimodal Hallucination Evaluation and Detection | 2025 | Taxonomy of hallucination (faithfulness/factuality) | MHaluBench | unknown | Comprehensive review of benchmarks and detection methods for I2T/T2I tasks |
| ViBe: A Text-to-Video Benchmark for Evaluating Hallucination in LMMs | 2025 | Ensemble classifier (TimeSFormer + CNN) | ViBe (3,782 videos) | unknown | Large-scale T2V benchmark identifying 5 hallucination types |
| Hallucination-Aware Multimodal Benchmark for Gastrointestinal Image Analysis | 2025 | Hallucination-aware finetuning | Kvasir-v2 images | unknown | Evaluates VLMs on hallucination detection/correction in medical imaging |
| Responsible AI challenge @ ICME 25 | 2025 | Multi-label classification | Synthetic + real-world data | unknown | Focuses on hallucinated captions in image-text systems |
| PhD: ChatGPT-Prompted Visual Hallucination Evaluation Dataset | 2025 | Visual Hallucination Evaluation (VHE) | PhD dataset | unknown | Large-scale dataset for assessing MLLM hallucination susceptibility |
| Unified Hallucination Detection for MLLMs | 2024 | UNIHD framework | MHaluBench | unknown | Unified framework using auxiliary tools for robust detection |
| Hallo3D: Multi-Modal Hallucination Detection and Optimization | 2024 | Viewpoint optimization | Unknown | unknown | Versatile 3D framework optimization for hallucination detection |
| Multi-Modal Hallucination Control by Visual Information Grounding | 2024 | Diversity-promoting objective | Microsoft COCO | unknown | Controls hallucinations via response diversity in conversation models |
| Systematic Literature Review on Hallucination Detection Methods | 2026 | LLM-as-a-judge + KG techniques | Unknown | unknown | Classifies detection strategies by hallucination type and technical approach |

---

## 2. Benchmark Comparison Table
| Benchmark Name | Modality | Size | Annotation Type | Key Features |
|---------------|----------|------|-----------------|--------------|
| MHaluBench | I2T/T2I | Unknown | Faithfulness/Factuality | Unified evaluation across generation tasks |
| ViBe | Text-to-Video | 3,782 videos | Human-labeled | Covers 5 hallucination types in T2V generation |
| Kvasir-v2 | Medical Imaging | Unknown | Expert-annotated | Focus on clinical text-image alignment |
| PhD Dataset | Visual-Language | Large-scale | ChatGPT-prompted | Measures MLLM susceptibility to visual hallucinations |

---

## 3. SOTA Trends Summary
1. **Unification Trend**: Emergence of unified frameworks (e.g., UNIHD) that handle multiple modalities and hallucination types simultaneously
2. **Domain Specialization**: Increasing focus on vertical domains (medical, 3D, video) with customized benchmarks
3. **Tool-Augmented Detection**: Growing use of auxiliary tools (KGs, validators) rather than pure end-to-end models
4. **Human-AI Collaboration**: Hybrid annotation approaches combining human expertise with AI generation (e.g., PhD dataset)
5. **Prevention over Detection**: Shift towards hallucination control mechanisms (e.g., diversity objectives) alongside detection

---

## 4. Method Classification
**Technical Approaches**:
1. **Taxonomy-Driven Methods**: Classification by hallucination type (faithfulness/factuality)
2. **Tool-Augmented Validation**: Leveraging external knowledge bases/validators (UNIHD, LLM-as-judge)
3. **Finetuning-Based**: Domain-specific adaptation (medical imaging finetuning)
4. **Ensemble Techniques**: Multi-model combinations (TimeSFormer + CNN in ViBe)
5. **Diversity Optimization**: Controlling generation diversity to reduce hallucinations

**Modality Coverage**:
- Image-Text (I2T/T2I)
- Text-Video (T2V)
- 3D-Vision
- Medical Multimodal

---

## 5. Research Suggestions
1. **Cross-Modal Hallucination Propagation**: Investigate how hallucinations propagate between modalities in chained generation tasks (e.g., text→image→video)
2. **Real-Time Detection Frameworks**: Develop lightweight hallucination detection systems for edge deployment in AR/VR applications
3. **Causal Analysis of Hallucinations**: Systematic study of root causes (training data biases, architecture limitations) using explainable AI techniques

---

## 附录：Agent 运行统计

- 搜索轮次：3
- 提取论文数：9
- 反思奖励分数：[0.7488888888888889, 0.8, 0.77, 0.85, 0.7666666666666667, 0.75]
- 平均奖励：0.78
