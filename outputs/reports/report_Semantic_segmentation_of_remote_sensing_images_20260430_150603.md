# Semantic Segmentation of Remote Sensing Images: Research Survey Report

## 1. Representative Papers

| Title | Year | Method | Dataset | Code URL | Contribution |
|-------|------|--------|---------|----------|--------------|
| Deep-Learning-Based Semantic Segmentation of Remote Sensing Images: A Survey | 2024 | DeepLabv3, DeepLabv3+, PSPN, UPerNet, SegNeXt | unknown | unknown | Comprehensive review of semantic segmentation methods, highlighting challenges and future directions |
| Semantic Segmentation of Remote Sensing Images | 2022 | U-Net ensemble | LandCover.ai, LoveDA, INRIA, UAVid, ISPRS Potsdam | unknown | Proposes ensemble approach achieving SOTA performance on multiple datasets |
| Accurate semantic segmentation of very high-resolution remote sensing images considering feature state sequences | 2025 | Spatial Interactive Attention (SIA), Channel Space Reconstruction (CSR) | unknown | unknown | Introduces mechanisms to refine fine-grained features and reduce computational consumption |
| Enhanced semantic segmentation in remote sensing images with ... | 2025 | DeepLab+IFIT | SpaceNet6 (SN6), AIR-MD-SAR-Map | unknown | Proposes framework for SAR image segmentation with high performance on fine-resolution datasets |
| AFNE-Net: Semantic Segmentation of Remote Sensing Images via Attention-Based Feature Fusion and Neighborhood Feature Enhancement | 2024 | Attention-based Feature Fusion (AF), Neighborhood Feature Enhancement (NE) | ISPRS Potsdam | unknown | Introduces AFNE-Net achieving SOTA performance on benchmarks |
| A Semantic Segmentation Method for Remote Sensing Images based on Deeplab v3 | 2022 | DeepLab v3, ASPP | ISPRS Vaihingen | unknown | Achieves high accuracy on ISPRS Vaihingen dataset |

## 2. Benchmark Datasets Comparison

| Dataset | Year | Resolution | Classes | Coverage | Sensor Type |
|---------|------|------------|---------|----------|-------------|
| ISPRS Potsdam | 2012 | 5cm | 6 | Urban | Aerial |
| ISPRS Vaihingen | 2012 | 9cm | 6 | Urban | Aerial |
| LandCover.ai | 2020 | 25-50cm | 5 | Rural/Urban | Aerial |
| SpaceNet6 (SN6) | 2020 | 0.5m | 7 | Urban | SAR |
| LoveDA | 2021 | 0.3m | 7 | Urban/Rural | Satellite |
| TorontoCity | 2017 | 5-15cm | 13 | Urban | Aerial |

## 3. SOTA Trends Summary

1. **Attention Mechanisms Dominance**: Recent works (2024-2025) increasingly incorporate attention mechanisms (SIA, CSR, AFNE) to enhance feature representation and capture long-range dependencies.

2. **Lightweight & Efficient Models**: Emerging focus on reducing computational complexity while maintaining accuracy (e.g., RS-Dseg, DeepLab+IFIT).

3. **Multimodal & SAR Integration**: Growing interest in SAR image segmentation and multimodal fusion approaches.

4. **Ensemble & Hybrid Approaches**: Combination of multiple architectures (U-Net ensemble) shows superior performance over single models.

5. **Fine-grained Feature Refinement**: Advanced techniques for handling very high-resolution imagery with complex spatial patterns.

## 4. Method Classification

**1. Encoder-Decoder Architectures**
- U-Net variants (U-Net, RUNet, SE-UNet)
- DeepLab family (v3, v3+, with ASPP)

**2. Attention-based Models**
- Spatial Interactive Attention (SIA)
- Channel Space Reconstruction (CSR)
- AFNE-Net (Attention-based Feature Fusion)

**3. Pyramid Pooling Networks**
- PSPNet (Pyramid Scene Parsing Network)
- UPerNet

**4. Lightweight Architectures**
- RS-Dseg
- SegNeXt

**5. Ensemble Methods**
- U-Net ensemble approaches

## 5. Research Directions Suggestions

1. **Cross-Modal Semantic Segmentation**:
   - Investigate fusion techniques for optical-SAR-LiDAR multimodal data
   - Develop domain adaptation methods for cross-sensor applications

2. **Edge-efficient Semantic Segmentation**:
   - Design ultra-lightweight models for real-time onboard processing
   - Explore neural architecture search for optimal edge deployment

3. **Explainable AI for Remote Sensing Segmentation**:
   - Develop interpretable attention mechanisms
   - Create visualization tools for segmentation decision processes
   - Investigate uncertainty quantification in segmentation outputs

---

## 附录：Agent 运行统计

- 搜索轮次：3
- 提取论文数：14
- 反思奖励分数：[0.66, 0.66, 0.7, 0.66, 0.66, 0.7, 0.64, 0.66, 0.66, 0.7, 0.66, 0.66, 0.7, 0.64, 0.6, 0.66, 0.66, 0.7, 0.66, 0.66, 0.7, 0.64, 0.66, 0.66, 0.7, 0.66, 0.66, 0.7, 0.64, 0.6, 0.64, 0.66, 0.66, 0.7, 0.66, 0.66, 0.7, 0.64, 0.66, 0.66, 0.7, 0.66, 0.66, 0.7, 0.64, 0.6, 0.66, 0.66, 0.7, 0.66, 0.66, 0.7, 0.64, 0.66, 0.66, 0.7, 0.66, 0.66, 0.7, 0.64, 0.6, 0.64, 0.5]
- 平均奖励：0.66
