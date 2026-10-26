# Task 2 — Engine Technical Support & Problem Solving
## Technical Pipeline & Quality Control Proposal

**Pipeline:** Maya (blockout, low-poly, LOD) → ZBrush (high-poly) → Substance Painter (bake/texture) → Unreal Engine 5

---

## 0. Approach in one page

A checklist alone only tells artists what is wrong *after* the work is done. This proposal is built on three ideas:

| Principle | What it means in practice |
|---|---|
| **Shift-left** | Checks run *while* the artist works (live HUD, heatmaps, LOD preview), not only at the end of a stage. Errors found early are cheaper. |
| **Measure, don't eyeball** | "Matches the reference" and "silhouette is preserved" become numbers (IoU score), so sign-off is objective. |
| **One source of truth** | A single `asset_contract.json` drives Maya, Substance Painter and Unreal. If the client changes a limit, we edit one file. |

### 0.1 Budgets derived from the brief

| Item | Limit | Note |
|---|---|---|
| LOD0 | ≤ 35,000 tris | 100% |
| LOD1 | ≤ 17,500 tris | 50% reduction from LOD0 |
| LOD2 | ≤ 8,750 tris | 75% reduction from LOD0 (assumption: both reductions are measured against LOD0) |
| Textures | ≤ 2 texture sets, 2048×2048 each | PBR Metallic/Roughness |
| LODs | Share UVs and materials | No per-LOD material or UV changes |

### 0.2 The Asset Contract (single source of truth)

```json
{
  "asset": "Character_A",
  "units": "cm",
  "forward_axis": "+Z",
  "tri_budget": { "LOD0": 35000, "LOD1": 17500, "LOD2": 8750 },
  "lod_reduction": { "LOD1": 0.50, "LOD2": 0.75 },
  "textures": { "max_sets": 2, "resolution": 2048, "workflow": "metal_rough", "packing": "ORM" },
  "texel_density": { "target_px_per_cm": 10.24, "tolerance": 0.10, "region_multipliers": { "face": 1.5 } },
  "uv": { "min_padding_px": 8, "allow_mirror_overlap": true },
  "normal_map": { "tangent_space": "MikkTSpace", "y_convention": "DirectX" },
  "pbr": { "albedo_srgb_range": [30, 240], "metallic_bimodal_min": 0.90, "roughness_saturation_max": 0.05 },
  "silhouette_iou": { "blockout_vs_reference": 0.90, "highpoly_vs_blockout": 0.95, "LOD1_vs_LOD0": 0.98, "LOD2_vs_LOD0": 0.95 },
  "skinning": { "max_influences": 4 },
  "naming": { "low": "{asset}_{part}_low", "high": "{asset}_{part}_high", "lod": "{asset}_LOD{n}" }
}
```

> Values such as `10.24 px/cm` and the IoU thresholds are proposed starting points. They should be tuned on the first pilot asset with the Lead Artist.

---

## 1. Quality Gates: sign-off checks per stage

Each stage has **5 critical checks**. `[A]` = checked automatically by a tool, `[M]` = manual review by the Technical Artist / Lead Artist. An asset cannot enter the next stage until every check is green.

### Stage 1 — Blockout (Maya)

| ID | Check | Pass criteria | How |
|---|---|---|---|
| B1 | **Silhouette matches 2D reference** | IoU ≥ 0.90 on front and side orthographic views | [A] Silhouette Judge + [M] Lead confirms |
| B2 | **Major forms are locked** | Head, torso, pelvis, limbs, hands, feet and key props exist as distinct volumes; head-to-body ratio and limb lengths within ±5% of the reference | [A] measured + [M] |
| B3 | **Scale, origin, transforms** | 1 unit = 1 cm, at origin, facing the project forward axis, transforms frozen, history deleted, naming follows the contract | [A] |
| B4 | **Joint-ready pose and volume** | A-pose or T-pose; enough volume at shoulders, elbows, hips, knees for joint placement | [M] |
| B5 | **Triangle forecast** | Extrapolated count fits 35k; budget split by priority (face and hands get more, hidden areas less) | [A] Budget HUD |

### Stage 2 — High-Poly (ZBrush)

| ID | Check | Pass criteria | How |
|---|---|---|---|
| H1 | **Clean surface** | No pinching, noise, stretched polygons or sculpt artifacts; forms read at the final viewing distance | [M] |
| H2 | **Bake-ready detail** | Hard edges and panel lines are crisp; depth is within the bake cage range (not too shallow, not so deep it breaks projection) | [M] + test bake |
| H3 | **Subtools organized and named** | Subtools split logically (body, armor, cloth, etc.) and named to match low-poly parts (`{part}_high`); PolyGroups assigned | [A] name check on export |
| H4 | **No geometry that breaks baking** | No unintended intersections, floating shells or inverted normals | [M] + import check in Maya |
| H5 | **Fidelity and export integrity** | Silhouette IoU ≥ 0.95 against the approved blockout; same scale and orientation as the low-poly; decimated if too heavy to bake | [A] + [M] |

### Stage 3 — Low-Poly (Maya)

| ID | Check | Pass criteria | How |
|---|---|---|---|
| L1 | **Triangle budget** | ≤ 35,000 triangles (counted as triangles, not quads) | [A] |
| L2 | **Deformation-friendly topology** | Edge loops follow muscle/joint flow; ≥ 3 loops at elbows, knees, shoulders; no poles on bending joints; test skin bends cleanly | [A] pole scan + [M] deform test |
| L3 | **Clean geometry** | No n-gons, non-manifold edges, lamina or zero-area faces, unmerged vertices; consistent normals | [A] |
| L4 | **UV quality and uniform texel density** | UVs in 0–1, no flips or overlaps (mirror excepted), padding ≥ 8 px at 2048, texel density within ±10% of target (face multiplier declared in the contract) | [A] |
| L5 | **Max two sets, bake-ready setup** | ≤ 2 materials/texture sets (e.g. `M_Body`, `M_Gear`); hard edges match UV seams; mesh names match the high-poly parts | [A] |

### Stage 4 — Texturing / Baking (Substance Painter)

| ID | Check | Pass criteria | How |
|---|---|---|---|
| T1 | **Bake accuracy** | Normal, AO, Curvature, Thickness maps free of ray misses, skewing and seams; ray-miss pixels < 0.5% | [A] bake scan + [M] |
| T2 | **Tangent-space consistency** | MikkTSpace; normal Y convention matches the engine (UE5 = DirectX, Unity = OpenGL) | [A] |
| T3 | **Resolution and set count** | ≤ 2 texture sets, each 2048×2048 | [A] |
| T4 | **PBR validity** | Albedo 30–240 sRGB for non-emissive surfaces; ≥ 90% of metallic pixels near 0 or 1; roughness saturated at 0 or 1 on < 5% of the surface | [A] PBR validator |
| T5 | **Export preset and color space** | Correct names (`T_{asset}_{set}_BC / ORM / N`), ORM packing, sRGB for color, Linear for data maps, edge padding on | [A] |

### Stage 5 — LOD & Engine Integration (Maya → UE5)

| ID | Check | Pass criteria | How |
|---|---|---|---|
| E1 | **Triangle targets** | LOD0 ≤ 35,000; LOD1 ≤ 17,500; LOD2 ≤ 8,750; actual counts logged | [A] |
| E2 | **Shared UVs and materials** | Identical UV shell layout and identical material slots in all LODs | [A] |
| E3 | **Silhouette preserved** | IoU vs LOD0 ≥ 0.98 (LOD1) and ≥ 0.95 (LOD2) from front, side and 3/4 views; no holes or collapsed fingers/face | [A] Silhouette Judge + [M] |
| E4 | **Skinning consistency** | Same skeleton on all LODs; no unweighted vertices; weights sum to 1; ≤ 4 influences per vertex | [A] |
| E5 | **Clean engine import** | No import warnings; correct scale/axis; sRGB off for ORM and normal; BC5 for normal; LOD screen-size thresholds set; exactly 2 material slots | [A] Engine Guardian |

---

## 2. Automation Tools

Four tools are proposed (three required, one bonus). All read the same `asset_contract.json`.

### Tool 1 — Budget HUD & Auto-QC

| Field | Description |
|---|---|
| **Target stage & application** | Stages 1 and 3 (and a pre-export gate for Stage 5). A Python + PySide2 panel inside **Maya** (`maya.cmds` / `OpenMaya`), running on demand and as a pre-export gate. |
| **Problem statement** | Artists count triangles, hunt n-gons, check UV overlap, compare texel density, verify names and transforms by hand. The work is repetitive, easy to skip, and every artist does it differently. Errors are discovered late, when fixing is expensive. |

**Functional description**
- **Live Budget HUD:** a bar in the viewport shows the current count against the contract (e.g. `31.2k / 35k`), turning green → yellow → red, with projected LOD1/LOD2 counts beside it.
- **Texel density heatmap:** shells are color-coded by deviation from the target density, so the artist sees problems while unwrapping.
- **One-click scan:** pass/warn/fail per check (tri count, n-gons, lamina/non-manifold, normals, UV range/overlap/flips/padding, texel density, material count ≤ 2, history/transforms, naming).
- **Click-to-select:** each failure is listed and selecting it highlights the exact faces/edges in the viewport.
- **Safe auto-fix:** freeze transforms, delete history, conform normals, merge vertices, rename to the convention.
- **Texel density normalizer:** measures every UV shell, scales to the target density (with per-region multipliers such as face ×1.5), repacks into the two sets with padding.
- **Report:** exports a JSON/HTML report that becomes part of the Asset Passport.

### Tool 2 — One-Click Bake Bridge

| Field | Description |
|---|---|
| **Target stage & application** | Stages 3 → 4. A Maya export script plus a **Substance Painter Python plugin**. |
| **Problem statement** | Exporting FBX, naming low/high pairs, and configuring bakes (resolution, tangent space, cage distance, output maps) by hand is error-prone. Wrong settings produce skewed or mismatched bakes, forcing rework. |

**Functional description**
- Runs Tool 1 first and **blocks the export** if the low-poly fails.
- Exports low-poly and high-poly FBX with the correct axis, scale and `_low` / `_high` suffixes.
- In Painter, creates the project from a template: 2 texture sets at 2048, MikkTSpace, the contract's normal Y convention, bake presets for Normal / AO / Curvature / Thickness / Position.
- Starts the bake and runs a **bake QA scan**: counts empty/black pixels and ray-miss regions in the maps and flags them with a percentage.
- Preloads the export preset (ORM packing, engine naming).

### Tool 3 — LOD Builder + Engine Guardian

| Field | Description |
|---|---|
| **Target stage & application** | Stages 4 → 5. A Python script in **Maya** (LOD creation) and an **Unreal Editor Utility** (Python / Editor Utility Widget) for post-import validation. |
| **Problem statement** | Hand-made LODs drift in UVs or materials and miss the 50% / 75% targets. Texture and PBR mistakes (wrong sRGB flag, wrong compression, extra material slots) are usually found late, inside the engine. |

**Functional description**
- **In Maya (LOD Builder):** generates LOD1 (−50%) and LOD2 (−75%) from LOD0, protecting UV borders, hard edges and silhouette-critical loops; keeps UV shells and material assignment; transfers skin weights; logs the real triangle counts; exports FBX with an LOD group.
- **In Unreal (Engine Guardian):** on import, applies the correct texture settings (sRGB off for data maps, BC5 for normal, mip settings), assigns the master material, verifies 2 material slots, checks per-LOD triangle counts, checks LOD screen-size thresholds, and verifies skeleton and skinning.
- Runs the PBR analysis on the imported textures and writes the final **Asset Passport**.

### Bonus Tool 4 — Silhouette Judge

| Field | Description |
|---|---|
| **Target stage & application** | Stages 1, 2 and 5. A Python tool (Maya for rendering, `numpy` for scoring); can also run headless in CI. |
| **Problem statement** | "Matches the reference" and "silhouette is preserved across LODs" are normally judged by eye, which leads to subjective debates and inconsistent sign-offs. |

**Functional description**
- Renders flat-color silhouettes from orthographic cameras (front, side, 3/4).
- Aligns to the reference mask by normalizing height and centering, then computes **IoU (intersection over union)**.
- Shows an overlay (green = match, red = surplus, blue = missing) so the artist knows *where* to correct.
- Compares LOD1/LOD2 against LOD0 using the same method. The score is written into the Asset Passport.

---

## 3. Asset Passport and Gate Flow

Every asset carries an auto-generated **Asset Passport** (`passport.json` + HTML view):

```json
{
  "asset": "Character_A",
  "version": "v012",
  "approved_by": "Lead Artist",
  "date": "YYYY-MM-DD",
  "tris": { "LOD0": 0, "LOD1": 0, "LOD2": 0 },
  "texture_sets": 2,
  "texel_density_deviation": 0.0,
  "silhouette_iou": { "blockout": 0.0, "LOD1": 0.0, "LOD2": 0.0 },
  "checks": { "passed": 0, "failed": 0, "waived": 0 }
}
```

**Optional CI-style enforcement:** a Perforce `change-submit` trigger (or Git pre-commit hook) runs the validators headless. A failing asset cannot be submitted; a passing asset receives its passport, and the next stage only accepts assets that have one.

```
Blockout ─[Tool 1 + Tool 4 + Lead]→ High-Poly ─[Tool 4 + name check]→ Low-Poly ─[Tool 1]→
Bake/Texture ─[Tool 2 + PBR check]→ LOD/Engine ─[Tool 3 + Tool 4 + Lead]→ Asset Passport ✔
```

---

## 4. Risks and Limitations (honest notes)

- IoU thresholds and texel density target are starting values and must be calibrated on a pilot asset.
- Automatic LOD reduction can damage fingers, face and thin props; a manual cleanup pass on LOD1/LOD2 may still be needed, and the tool flags where.
- Maintaining three tool integrations (Maya, Painter, Unreal) has a cost: API changes between versions need regression tests. The shared contract keeps this cost low.
- Tools reduce manual overhead; they do not replace the Lead Artist's judgment on style and form.

---

# 🇻🇳 Bản dịch tiếng Việt

> ## Task 2 — Hỗ trợ kỹ thuật Engine & Giải quyết vấn đề
> ### Đề xuất Quy trình Kỹ thuật & Kiểm soát Chất lượng
>
> **Pipeline:** Maya (blockout, low-poly, LOD) → ZBrush (high-poly) → Substance Painter (bake/texture) → Unreal Engine 5
>
> ---
>
> ### 0. Tóm tắt cách tiếp cận
>
> Checklist đơn thuần chỉ báo lỗi *sau khi* làm xong. Đề xuất này dựa trên ba ý tưởng:
> - **Shift-left (kiểm tra sớm):** kiểm tra chạy *trong lúc* artist làm (HUD thời gian thực, heatmap, xem trước LOD) thay vì chỉ cuối giai đoạn. Lỗi phát hiện sớm thì rẻ hơn.
> - **Đo lường thay vì nhìn bằng mắt:** "khớp reference" và "giữ silhouette" trở thành con số (điểm IoU), nên việc duyệt khách quan.
> - **Một nguồn sự thật:** một file `asset_contract.json` điều khiển Maya, Substance Painter và Unreal. Client đổi giới hạn thì chỉ sửa một file.
>
> **Giới hạn rút ra từ yêu cầu:** LOD0 ≤ 35.000 tris; LOD1 ≤ 17.500 (giảm 50%); LOD2 ≤ 8.750 (giảm 75%, giả định cả hai mức giảm tính từ LOD0); tối đa 2 texture set 2048×2048, PBR Metallic/Roughness; các LOD dùng chung UV và material.
>
> **Asset Contract:** file JSON ở trên ghi mọi giới hạn (tri, texture, texel density, tangent space, ngưỡng PBR, ngưỡng IoU, skinning, quy tắc đặt tên). Các giá trị như `10.24 px/cm` và ngưỡng IoU là điểm khởi đầu đề xuất, cần tinh chỉnh trên asset thử nghiệm cùng Lead Artist.
>
> ---
>
> ### 1. Cổng chất lượng: các mục nghiệm thu từng giai đoạn
>
> Mỗi giai đoạn có **5 kiểm tra quan trọng**. `[A]` = công cụ kiểm tra tự động, `[M]` = Technical Artist / Lead Artist duyệt thủ công. Asset chỉ được qua giai đoạn sau khi mọi mục đều đạt.
>
> **Giai đoạn 1 — Blockout (Maya)**
>
> | ID | Kiểm tra | Tiêu chí đạt |
> |---|---|---|
> | B1 | Silhouette khớp reference 2D | IoU ≥ 0,90 ở view trước và bên (ortho) [A+M] |
> | B2 | Khóa các khối chính | Đầu, thân, hông, tay chân, bàn tay/chân, props là các khối riêng; tỉ lệ đầu/thân và chiều dài chi lệch ≤ ±5% [A+M] |
> | B3 | Scale, gốc tọa độ, transform | 1 unit = 1 cm, tại gốc, đúng hướng trục dự án, đã freeze, xóa history, đặt tên theo contract [A] |
> | B4 | Pose và thể tích sẵn sàng cho joint | A-pose hoặc T-pose; đủ thể tích ở vai, khuỷu, hông, gối [M] |
> | B5 | Dự báo số tri | Ước lượng nằm trong 35k, phân bổ theo ưu tiên (mặt, tay nhiều hơn) [A] |
>
> **Giai đoạn 2 — High-Poly (ZBrush)**
>
> | ID | Kiểm tra | Tiêu chí đạt |
> |---|---|---|
> | H1 | Bề mặt sạch | Không pinch, noise, polygon giãn, artifact; hình khối đọc rõ ở khoảng cách xem thực tế [M] |
> | H2 | Chi tiết sẵn sàng bake | Cạnh cứng/đường panel sắc; độ sâu nằm trong tầm cage khi bake [M + bake thử] |
> | H3 | Subtool được tổ chức và đặt tên | Chia hợp lý, tên khớp phần low-poly (`{part}_high`), đã gán PolyGroup [A] |
> | H4 | Không có geometry làm hỏng bake | Không giao nhau ngoài ý muốn, không shell lơ lửng, không normal bị đảo [M] |
> | H5 | Trung thành và export đúng | IoU ≥ 0,95 so với blockout đã duyệt; cùng scale/hướng với low-poly; decimate nếu quá nặng [A+M] |
>
> **Giai đoạn 3 — Low-Poly (Maya)**
>
> | ID | Kiểm tra | Tiêu chí đạt |
> |---|---|---|
> | L1 | Ngân sách tri | ≤ 35.000 tam giác (đếm theo tam giác, không theo quad) [A] |
> | L2 | Topology cho deformation | Edge loop theo cơ/khớp; ≥ 3 loop ở khuỷu, gối, vai; không có pole ở khớp gập; test skin bẻ sạch [A+M] |
> | L3 | Geometry sạch | Không n-gon, non-manifold, lamina, face diện tích 0, vertex chưa merge; normal nhất quán [A] |
> | L4 | UV và texel density đồng đều | UV trong 0–1, không lật/overlap (trừ mirror), padding ≥ 8 px ở 2048, texel density lệch ≤ ±10% mục tiêu [A] |
> | L5 | Tối đa hai set, sẵn sàng bake | ≤ 2 material/texture set; hard edge khớp UV seam; tên mesh khớp phần high-poly [A] |
>
> **Giai đoạn 4 — Texturing / Baking (Substance Painter)**
>
> | ID | Kiểm tra | Tiêu chí đạt |
> |---|---|---|
> | T1 | Độ chính xác bake | Map Normal, AO, Curvature, Thickness không ray miss, skew, seam; pixel ray miss < 0,5% [A+M] |
> | T2 | Nhất quán tangent space | MikkTSpace; quy ước Y của normal khớp engine (UE5 = DirectX, Unity = OpenGL) [A] |
> | T3 | Độ phân giải và số set | ≤ 2 texture set, mỗi set 2048×2048 [A] |
> | T4 | PBR hợp lệ | Albedo 30–240 sRGB (vật không phát sáng); ≥ 90% pixel metallic gần 0 hoặc 1; roughness bão hòa 0/1 trên < 5% bề mặt [A] |
> | T5 | Preset export và color space | Đặt tên đúng, packing ORM, sRGB cho color, Linear cho data map, bật edge padding [A] |
>
> **Giai đoạn 5 — LOD & Tích hợp Engine (Maya → UE5)**
>
> | ID | Kiểm tra | Tiêu chí đạt |
> |---|---|---|
> | E1 | Mục tiêu số tri | LOD0 ≤ 35.000; LOD1 ≤ 17.500; LOD2 ≤ 8.750; ghi log số thực tế [A] |
> | E2 | Chung UV và material | Layout UV shell và material slot giống hệt nhau ở mọi LOD [A] |
> | E3 | Giữ silhouette | IoU so với LOD0 ≥ 0,98 (LOD1) và ≥ 0,95 (LOD2) ở view trước, bên, 3/4; không lỗ, không collapse ngón/mặt [A+M] |
> | E4 | Skinning nhất quán | Cùng skeleton; không vertex thiếu weight; tổng weight = 1; ≤ 4 influence/vertex [A] |
> | E5 | Import engine sạch | Không warning; đúng scale/axis; tắt sRGB cho ORM và normal; BC5 cho normal; đã đặt ngưỡng screen size LOD; đúng 2 material slot [A] |
>
> ---
>
> ### 2. Công cụ tự động hóa
>
> Đề xuất bốn công cụ (ba bắt buộc, một bonus), đều đọc cùng file `asset_contract.json`.
>
> **Công cụ 1 — Budget HUD & Auto-QC**
> - **Giai đoạn & ứng dụng:** Giai đoạn 1 và 3 (và cổng chặn trước export cho giai đoạn 5). Panel Python + PySide2 trong **Maya**, chạy thủ công hoặc làm cổng trước khi export.
> - **Vấn đề:** Artist đếm tri, tìm n-gon, kiểm tra UV overlap, so texel density, kiểm tra tên và transform bằng tay. Việc lặp lại, dễ sót, mỗi người làm một kiểu, lỗi phát hiện muộn nên sửa tốn kém.
> - **Chức năng:** HUD ngân sách thời gian thực (vd `31,2k / 35k`, đổi màu xanh → vàng → đỏ, kèm số tri dự kiến LOD1/LOD2); heatmap texel density theo màu cho từng shell; quét một lần bấm với pass/warn/fail cho từng mục; bấm vào lỗi để chọn đúng face/edge trong viewport; tự sửa an toàn (freeze, xóa history, đồng bộ normal, merge vertex, đổi tên); chuẩn hóa texel density (đo từng shell, scale về mật độ mục tiêu, hệ số riêng cho mặt ×1,5, pack lại vào hai set kèm padding); xuất báo cáo JSON/HTML cho Asset Passport.
>
> **Công cụ 2 — One-Click Bake Bridge**
> - **Giai đoạn & ứng dụng:** Giai đoạn 3 → 4. Script export trong Maya cùng **plugin Python cho Substance Painter**.
> - **Vấn đề:** Export FBX, đặt tên cặp low/high và cấu hình bake (độ phân giải, tangent space, cage distance, map đầu ra) bằng tay dễ sai, gây bake lệch và phải làm lại.
> - **Chức năng:** chạy Công cụ 1 trước và **chặn export** nếu low-poly không đạt; export low/high đúng axis, scale, hậu tố `_low`/`_high`; tạo project Painter theo template (2 set 2048, MikkTSpace, quy ước Y theo contract, preset bake Normal/AO/Curvature/Thickness/Position); tự bake rồi quét **QA bake** (đếm pixel đen/trống và vùng ray miss, báo theo phần trăm); nạp sẵn preset export (ORM, đặt tên theo engine).
>
> **Công cụ 3 — LOD Builder + Engine Guardian**
> - **Giai đoạn & ứng dụng:** Giai đoạn 4 → 5. Script Python trong **Maya** (tạo LOD) và **Unreal Editor Utility** (kiểm tra sau import).
> - **Vấn đề:** LOD làm tay dễ lệch UV/material và không đạt mục tiêu 50%/75%. Lỗi texture/PBR (sai cờ sRGB, sai kiểu nén, thừa material slot) thường chỉ bị phát hiện muộn trong engine.
> - **Chức năng:** *Trong Maya:* sinh LOD1 (−50%) và LOD2 (−75%) từ LOD0, bảo vệ biên UV, hard edge và loop quan trọng của silhouette; giữ UV/material; chuyển skin weight; ghi log số tri thật; export FBX kèm LOD group. *Trong Unreal:* khi import tự áp đúng setting texture (tắt sRGB cho data map, BC5 cho normal, mip), gán master material, xác nhận 2 material slot, kiểm tra số tri từng LOD, ngưỡng screen size và skeleton/skinning; chạy phân tích PBR và xuất **Asset Passport** cuối cùng.
>
> **Công cụ Bonus 4 — Silhouette Judge**
> - **Giai đoạn & ứng dụng:** Giai đoạn 1, 2 và 5. Tool Python (Maya render, `numpy` tính điểm), có thể chạy headless trong CI.
> - **Vấn đề:** "Khớp reference" và "giữ silhouette giữa các LOD" thường được đánh giá bằng mắt, dẫn đến tranh luận chủ quan và duyệt không nhất quán.
> - **Chức năng:** render silhouette màu phẳng từ camera ortho (trước, bên, 3/4); căn theo mask reference (chuẩn hóa chiều cao, căn giữa) rồi tính **IoU**; hiển thị overlay (xanh lá = khớp, đỏ = thừa, xanh dương = thiếu) để artist biết *chỗ nào* cần sửa; so LOD1/LOD2 với LOD0 bằng cùng phương pháp và ghi điểm vào Asset Passport.
>
> ---
>
> ### 3. Asset Passport và luồng cổng kiểm soát
>
> Mỗi asset đi kèm **Asset Passport** tự sinh (`passport.json` + bản xem HTML) ghi: tên asset, version, người duyệt, ngày, số tri từng LOD, số texture set, độ lệch texel density, điểm IoU và số kiểm tra đạt/trượt/được miễn.
>
> **Áp dụng kiểu CI (tùy chọn):** trigger `change-submit` của Perforce (hoặc Git pre-commit hook) chạy validator headless. Asset trượt sẽ không submit được; asset đạt nhận passport và giai đoạn sau chỉ nhận asset có passport.
>
> **Luồng:** Blockout → [Công cụ 1 + 4 + Lead] → High-Poly → [Công cụ 4 + kiểm tra tên] → Low-Poly → [Công cụ 1] → Bake/Texture → [Công cụ 2 + kiểm tra PBR] → LOD/Engine → [Công cụ 3 + 4 + Lead] → Asset Passport ✔
>
> ---
>
> ### 4. Rủi ro và hạn chế (nói thẳng)
>
> - Ngưỡng IoU và texel density mục tiêu chỉ là giá trị khởi đầu, cần hiệu chỉnh trên asset thử nghiệm.
> - Giảm LOD tự động có thể làm hỏng ngón tay, mặt, props mỏng; có thể vẫn cần dọn tay LOD1/LOD2, và tool sẽ đánh dấu những chỗ đó.
> - Duy trì ba tích hợp (Maya, Painter, Unreal) có chi phí: thay đổi API giữa các phiên bản cần regression test. Contract dùng chung giúp giữ chi phí này thấp.
> - Công cụ giảm việc thủ công, không thay thế đánh giá của Lead Artist về phong cách và hình khối.
