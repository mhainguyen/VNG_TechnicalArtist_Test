# AI Usage Report (Task 1 & Task 2)

---

## 1. AI Tools & Models Used

| Tool | Model | Used for |
|---|---|---|
| Claude (claude.ai) | Claude Sonnet 5.5 | Task 2: structuring the pipeline/QC proposal, drafting checklists and tool specs, bilingual (EN/VI) writing |
| Claude (claude.ai) | Claude Sonnet 5.5 | Task 1: writing the report, user guide and setup instructions for `validate_submission.py` |

## 2. The Combined Workflow

1. **Understand the brief:** pasted the Task 2 brief into Claude and asked for a first full solution.
2. **Draft fast, refine later:** reviewed the first draft against the brief's exact requirements (5 stages, ≥ 5 checks each, ≥ 3 tools with stage/application, problem, function).
3. **Simplify:** asked Claude to merge overlapping checks and tools to reach a leaner proposal.
4. **Differentiate:** asked for less "by-the-book" ideas; chose the directions that were technically realistic (shift-left checks, single JSON contract, measurable silhouette scoring).
5. **Package:** produced the final bilingual (English + Vietnamese) document.
6. **Task 1:** used Claude to write the report, user guide and setup instructions for `validate_submission.py`, aligned with the Task 2 asset contract.
7. **Human review:** reviewed each draft, requested edits (removed intro lines and notes, clarified wording) and finalized the documents.

> **Verification note:** AI output was treated as a draft. API names, thresholds and engine settings must be checked against the official Maya, Substance Painter and Unreal documentation before being relied on.

## 3. Prompt Log & Refinement

### Example 1 — Initial solution (Task 2)

- **Prompt:** the full Task 2 brief pasted as-is, plus "help me solve this" (in Vietnamese).
- **Initial output:** a complete proposal with 6–7 checks per stage and 4 tools. Correct but long, and partly repetitive between stages.
- **Refinement:** the output was accurate to the brief but too heavy to present, so the next prompt targeted simplification.
- **Result:** a solid baseline covering all required parts.

### Example 2 — Simplification

- **Prompt:** "Can the process be consolidated to be simpler and more efficient?" (Vietnamese)
- **Initial output:** 5 checks per stage in a table and 3 tools (texel density merged into the QC tool; LOD generator and PBR validator merged into one tool).
- **Refinement:** the result met the minimum exactly, but it read like every other submission.
- **Result:** a lean structure that became the skeleton of the final report.

### Example 3 — Creativity with feasibility

- **Prompt:** "Is there a more creative way, not by the book?" (Vietnamese)
- **Initial output:** four directions: shift-left live checks, a single "Asset Contract" JSON, measurable silhouette scoring (IoU), and CI-style submit gates. Claude also warned that creative ideas must stay feasible and state which APIs they use.
- **Refinement:** selected shift-left + silhouette scoring + Asset Contract, and asked for the full report in English with a Vietnamese translation.
- **Result:** the final `Task2_Pipeline_QC_Proposal.md`.

## 4. Technical Decisions Made with AI

These are the concrete engineering decisions that came out of the discussion with the AI, with the reasoning behind each.

| # | Decision | Why | Trade-off / limitation |
|---|---|---|---|
| 1 | Read "50% / 75% reduction" as reductions from LOD0 → LOD1 ≤ 17,500 and LOD2 ≤ 8,750 tris | The brief does not say what the reduction is measured against; LOD0 is the only unambiguous baseline | Stated as an assumption in the report; easy to change in the contract |
| 2 | One `asset_contract.json` read by every tool (Maya, Painter, Unreal) | Avoids hard-coding 35k / 2 sets / 2048 in three places; a client change means one edit | All tools must share one small reader module |
| 3 | Score silhouettes with IoU from orthographic flat-color renders (height-normalized and centered) | Turns "matches the reference" into a number instead of a subjective review | Starting thresholds (0.90 / 0.95 / 0.98) need calibration; a silhouette does not capture interior form or depth, so Lead review is kept |
| 4 | Encode engine-specific texture rules in the checks | UE5 expects DirectX-style normals, Unity expects OpenGL; MikkTSpace must match; BC5 for normals; sRGB off for packed ORM | Settings must be revisited if the target engine changes |
| 5 | Shift-left tooling (live triangle HUD, texel-density heatmap) in addition to end-of-stage gates | Errors found while working are cheaper to fix than errors found at sign-off | More tool code to maintain than a checklist alone |
| 6 | LOD generation protects UV borders and hard edges | LODs must share UVs and materials; unprotected decimation shifts UV seams | Automatic reduction can still damage fingers, face and thin props, so the tool flags them for manual cleanup |
| 7 | Tools run in each application's own scripting layer: Maya (`maya.cmds` / OpenMaya), Substance Painter Python plugins, Unreal Python / Editor Utility | Keeps artists inside the tools they already use | Three integrations need regression tests when software versions change |

**Verification status:** the thresholds and API choices above are design proposals. They have not been tested inside Maya, Substance Painter or Unreal, and should be validated on a pilot asset before use.

---

# 🇻🇳 Bản dịch tiếng Việt

> ## Báo cáo sử dụng AI (Task 1 & Task 2)
>
> ### 1. Công cụ & model AI đã dùng
>
> - **Claude (claude.ai), model Claude Sonnet 5.5:** Task 2, dùng để dựng cấu trúc đề xuất pipeline/QC, soạn checklist và mô tả công cụ, viết song ngữ Anh–Việt.
> - **Claude (claude.ai), model Claude Sonnet 5.5:** Task 1, dùng để viết báo cáo, hướng dẫn sử dụng và hướng dẫn cài đặt cho `validate_submission.py`.
>
> ### 2. Workflow kết hợp AI
>
> 1. **Hiểu đề:** dán nguyên đề Task 2 vào Claude và nhờ đưa ra một lời giải đầy đủ đầu tiên.
> 2. **Làm nhanh bản nháp, tinh chỉnh sau:** đối chiếu bản nháp đầu với yêu cầu chính xác của đề (5 giai đoạn, mỗi giai đoạn ≥ 5 kiểm tra, ≥ 3 công cụ có nêu giai đoạn/ứng dụng, vấn đề, chức năng).
> 3. **Đơn giản hóa:** nhờ Claude gộp các kiểm tra và công cụ trùng nhau để có đề xuất gọn hơn.
> 4. **Tạo điểm khác biệt:** yêu cầu các ý tưởng bớt "theo sách vở"; chọn những hướng khả thi về kỹ thuật (kiểm tra shift-left, một file contract JSON duy nhất, chấm điểm silhouette bằng số).
> 5. **Hoàn thiện:** tạo tài liệu song ngữ (Anh + Việt) cuối cùng.
> 6. **Task 1:** dùng Claude viết báo cáo, hướng dẫn sử dụng và cài đặt cho `validate_submission.py`, thống nhất với asset contract của Task 2.
> 7. **Rà soát của con người:** xem lại từng bản nháp, yêu cầu chỉnh sửa (bỏ các dòng giới thiệu và ghi chú, làm rõ cách diễn đạt) rồi chốt tài liệu.
>
> **Lưu ý về kiểm chứng:** kết quả của AI được xem là bản nháp. Tên API, các ngưỡng và setting engine cần được đối chiếu với tài liệu chính thức của Maya, Substance Painter và Unreal trước khi dùng.
>
> ### 3. Nhật ký prompt & tinh chỉnh
>
> **Ví dụ 1 — Lời giải ban đầu (Task 2)**
> - **Prompt:** dán nguyên đề Task 2 kèm câu "giúp tôi giải quyết vấn đề này" (tiếng Việt).
> - **Kết quả ban đầu:** đề xuất đầy đủ với 6–7 kiểm tra mỗi giai đoạn và 4 công cụ. Đúng nhưng dài, và có phần lặp giữa các giai đoạn.
> - **Tinh chỉnh:** kết quả bám đúng đề nhưng quá nặng để trình bày, nên prompt tiếp theo nhắm vào việc đơn giản hóa.
> - **Kết quả:** một nền tảng vững, bao phủ mọi phần bắt buộc.
>
> **Ví dụ 2 — Đơn giản hóa**
> - **Prompt:** "Có thể gom quy trình đơn giản hơn và hiệu quả hơn không?" (tiếng Việt)
> - **Kết quả ban đầu:** 5 kiểm tra mỗi giai đoạn dạng bảng và 3 công cụ (texel density gộp vào tool QC; LOD generator và PBR validator gộp thành một tool).
> - **Tinh chỉnh:** kết quả đạt đúng mức tối thiểu nhưng giống mọi bài nộp khác.
> - **Kết quả:** cấu trúc gọn, trở thành bộ khung của báo cáo cuối.
>
> **Ví dụ 3 — Sáng tạo nhưng khả thi**
> - **Prompt:** "Có cách nào sáng tạo hơn không theo bài vở không?" (tiếng Việt)
> - **Kết quả ban đầu:** bốn hướng: kiểm tra shift-left theo thời gian thực, một file "Asset Contract" JSON, chấm điểm silhouette bằng số (IoU), và cổng chặn khi submit kiểu CI. Claude cũng lưu ý ý tưởng sáng tạo phải khả thi và nêu rõ dùng API nào.
> - **Tinh chỉnh:** chọn shift-left + chấm điểm silhouette + Asset Contract, và yêu cầu báo cáo đầy đủ bằng tiếng Anh kèm bản dịch tiếng Việt.
> - **Kết quả:** file `Task2_Pipeline_QC_Proposal.md` cuối cùng.
>
> ### 4. Các quyết định kỹ thuật đưa ra cùng AI
>
> Đây là những quyết định kỹ thuật cụ thể rút ra từ quá trình thảo luận với AI, kèm lý do.
>
> 1. **Hiểu "giảm 50% / 75%" là giảm so với LOD0** → LOD1 ≤ 17.500 và LOD2 ≤ 8.750 tri. Đề không nói rõ tính theo mốc nào, LOD0 là mốc duy nhất không mơ hồ. Đây được ghi là giả định trong báo cáo và dễ đổi trong contract.
> 2. **Một file `asset_contract.json` cho mọi tool (Maya, Painter, Unreal).** Tránh hard-code 35k / 2 set / 2048 ở ba nơi, client đổi yêu cầu chỉ sửa một chỗ. Đánh đổi: các tool phải dùng chung một module đọc contract nhỏ.
> 3. **Chấm silhouette bằng IoU từ render màu phẳng ở camera ortho** (chuẩn hóa chiều cao, căn giữa). Biến "khớp reference" thành con số thay vì đánh giá chủ quan. Hạn chế: ngưỡng khởi đầu (0,90 / 0,95 / 0,98) cần hiệu chỉnh; silhouette không phản ánh hình khối bên trong hay chiều sâu, nên vẫn giữ bước duyệt của Lead.
> 4. **Đưa quy tắc texture theo engine vào các kiểm tra.** UE5 dùng normal kiểu DirectX, Unity dùng OpenGL; MikkTSpace phải khớp; BC5 cho normal; tắt sRGB cho ORM. Cần xem lại nếu đổi engine đích.
> 5. **Công cụ kiểu shift-left** (HUD tri thời gian thực, heatmap texel density) bên cạnh các cổng cuối giai đoạn. Lỗi phát hiện lúc đang làm rẻ hơn lỗi phát hiện lúc duyệt. Đánh đổi: nhiều code cần bảo trì hơn một checklist đơn thuần.
> 6. **Tạo LOD có bảo vệ biên UV và hard edge.** Các LOD phải chung UV và material; giảm poly không bảo vệ sẽ làm lệch UV seam. Giảm tự động vẫn có thể làm hỏng ngón tay, mặt, props mỏng nên tool đánh dấu để dọn tay.
> 7. **Mỗi tool chạy trong lớp script của chính ứng dụng:** Maya (`maya.cmds` / OpenMaya), plugin Python của Substance Painter, Python / Editor Utility của Unreal. Artist không phải rời công cụ quen thuộc. Đánh đổi: ba tích hợp cần regression test khi đổi phiên bản phần mềm.
>
> **Tình trạng kiểm chứng:** các ngưỡng và lựa chọn API trên là đề xuất thiết kế, chưa được thử trong Maya, Substance Painter hay Unreal, và cần kiểm chứng trên một asset thử nghiệm trước khi dùng.
