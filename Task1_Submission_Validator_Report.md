# Task 1 — Submission Validator Tool
## Report, User Guide and Setup Instructions

---

## 1. What the tool does (in plain words)

Before an artist hands in a character asset, the **Submission Validator** checks the submission against the project rules and produces a clear **PASS / WARN / FAIL** report. It catches mistakes in seconds that a reviewer would otherwise find by opening files one by one.

**Who uses it:** artists (before submitting) and Technical/Lead Artists (as a gate before approval).

**What it checks** (all limits come from one file, `asset_contract.json`):

| Category | Example checks |
|---|---|
| Folder & naming | Required folders exist; files follow `{asset}_{part}_low`, `T_{asset}_{set}_BC/ORM/N` naming |
| Mesh | Triangle count ≤ 35,000 (LOD0); LOD1 ≤ 17,500; LOD2 ≤ 8,750; no n-gons / non-manifold; transforms frozen |
| UV | In 0–1 range, no overlaps (mirror allowed), padding, texel density within tolerance |
| Materials & textures | ≤ 2 texture sets; every map is 2048×2048; correct color space; PBR value ranges |
| LOD | 3 LODs present; same UVs and material slots across LODs |
| Documents | Documentation file present; demo video present; AI report present |

**Result for each check:**
- ✅ **PASS**: meets the rule.
- ⚠️ **WARN**: allowed but worth a look (for example, texel density 8% off, limit 10%).
- ❌ **FAIL**: breaks a rule; must be fixed before submission.

---

## 2. Setup Guide

### 2.1 Requirements

| Item | Version / note |
|---|---|
| Python | 3.10 or newer |
| Operating system | Windows 10/11 |
| Autodesk Maya (optional) | 2022 or newer, needed only for mesh/UV checks that run through `mayapy` |
| Python packages | Listed in `requirements.txt` (for example `Pillow`, `numpy`) |

### 2.2 Installation

1. **Get the code**
   ```bash
   git clone https://github.com/<your-account>/<your-repo>.git
   cd <your-repo>
   ```
2. **Create a virtual environment** (keeps the install separate from other Python projects)
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   # source .venv/bin/activate   # macOS / Linux
   ```
3. **Install packages**
   ```bash
   pip install -r requirements.txt
   ```
4. **Check the install**
   ```bash
   python validate_submission.py --help
   ```
   If you see the list of options, setup is done.

### 2.3 Configuration

All limits live in `config/asset_contract.json`. Open it in any text editor and change a number to change a rule. Example:

```json
{
  "tri_budget": { "LOD0": 35000, "LOD1": 17500, "LOD2": 8750 },
  "textures": { "max_sets": 2, "resolution": 2048 }
}
```

You never need to edit the Python code to change a limit.

---

## 3. User Guide

### 3.1 Run a check

```bash
python validate_submission.py --path "D:/Submissions/Character_A" --config config/asset_contract.json
```

| Option | Meaning |
|---|---|
| `--path` | Folder of the submission to check |
| `--config` | The contract file with the limits |
| `--report` | Where to save the report (`report.html` or `report.json`) |
| `--fix` | Apply safe automatic fixes where the tool supports them |

### 3.2 Reading the report

```
[FAIL] Mesh   | LOD0 triangles: 38,412 / 35,000 limit
[WARN] UV     | Texel density deviation: 8.2% (limit 10%)
[PASS] Texture| 2 sets, all 2048x2048
SUMMARY: 14 passed, 1 warning, 1 failed  →  NOT READY TO SUBMIT
```

Rule of thumb: **zero FAIL = ready to submit.** Warnings should be reviewed but do not block.

### 3.3 Recommended artist workflow

1. Work on the asset.
2. Run the validator.
3. Fix every FAIL, review every WARN.
4. Run again until the summary says READY.
5. Attach the report to the submission and push to GitHub.

---

## 4. Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `python is not recognized` | Python not installed or not on PATH | Reinstall Python and tick "Add to PATH" |
| `ModuleNotFoundError` | Virtual environment not active or packages not installed | Activate `.venv`, run `pip install -r requirements.txt` |
| Mesh checks are skipped | Maya not found | Set the Maya path in the config |
| Everything FAILs on triangle count | Counting quads instead of triangles, or wrong contract | Check `tri_budget` in the config |
| Report not created | No write permission | Choose a different `--report` folder |

---

## 5. Demo Video Checklist

The submission needs video demos. Suggested content (about 2–3 minutes):

1. Show the repo and the `asset_contract.json`.
2. Run the validator on a **failing** submission and show the report.
3. Fix one issue (for example, reduce triangles) and run again.
4. Show the **passing** report.

---

## 6. Repository Cleanliness Checklist

- [ ] Source code, config and documentation are included.
- [ ] Engine project contains only needed assets (no cache folders). Unreal: exclude `Binaries/`, `Intermediate/`, `Saved/`, `DerivedDataCache/`. Unity: exclude `Library/`, `Temp/`, `Logs/`.
- [ ] Large binaries (`.fbx`, `.psd`, `.uasset`, `.ztl`, `.spp`) use Git LFS or are linked externally.
- [ ] `README.md`, this report, `AI_REPORT.md` and video links are in the repo root or `/docs`.

---

# 🇻🇳 Bản dịch tiếng Việt

> ## Task 1 — Công cụ kiểm tra bài nộp (Submission Validator)
> ### Báo cáo, hướng dẫn sử dụng và cài đặt
>
> ---
>
> ### 1. Tool làm gì (nói đơn giản)
>
> Trước khi artist nộp một asset nhân vật, **Submission Validator** đối chiếu bài nộp với quy tắc dự án và tạo báo cáo **PASS / WARN / FAIL** rõ ràng. Những lỗi mà người duyệt phải mở từng file mới thấy thì tool tìm ra trong vài giây.
>
> **Ai dùng:** artist (trước khi nộp) và Technical/Lead Artist (làm cổng trước khi duyệt).
>
> **Kiểm tra gì** (mọi giới hạn lấy từ một file `asset_contract.json`):
> - **Thư mục & đặt tên:** đủ thư mục bắt buộc; tên file theo `{asset}_{part}_low`, `T_{asset}_{set}_BC/ORM/N`.
> - **Mesh:** LOD0 ≤ 35.000 tri; LOD1 ≤ 17.500; LOD2 ≤ 8.750; không n-gon/non-manifold; đã freeze transform.
> - **UV:** trong 0–1, không overlap (cho phép mirror), padding, texel density trong ngưỡng.
> - **Material & texture:** ≤ 2 texture set; mọi map 2048×2048; đúng color space; giá trị PBR hợp lệ.
> - **LOD:** có đủ 3 LOD; chung UV và material slot.
> - **Tài liệu:** có file tài liệu, video demo và báo cáo AI.
>
> **Kết quả mỗi mục:** ✅ PASS (đạt), ⚠️ WARN (cho phép nhưng nên xem lại, ví dụ texel density lệch 8%, giới hạn 10%), ❌ FAIL (vi phạm quy tắc, phải sửa trước khi nộp).
>
> ---
>
> ### 2. Hướng dẫn cài đặt
>
> **Yêu cầu:** Python 3.10 trở lên; Windows 10/11; Maya 2022 trở lên (tùy chọn, chỉ cần cho kiểm tra mesh/UV chạy qua `mayapy`); các package trong `requirements.txt` (ví dụ `Pillow`, `numpy`). *(Cần xác nhận lại.)*
>
> **Cài đặt:**
> 1. Tải code: `git clone` repository về máy rồi vào thư mục dự án.
> 2. Tạo môi trường ảo: `python -m venv .venv`, rồi kích hoạt (`.venv\Scripts\activate` trên Windows).
> 3. Cài package: `pip install -r requirements.txt`.
> 4. Kiểm tra: chạy tool với `--help`; thấy danh sách tùy chọn nghĩa là cài xong.
>
> **Cấu hình:** mọi giới hạn nằm trong `config/asset_contract.json`. Mở bằng trình soạn thảo bất kỳ và đổi con số là đổi quy tắc, không cần sửa code Python.
>
> ---
>
> ### 3. Hướng dẫn sử dụng
>
> **Chạy kiểm tra:** dùng `--path` (thư mục bài nộp), `--config` (file contract), `--report` (nơi lưu báo cáo), `--fix` (tự sửa an toàn nếu tool hỗ trợ).
>
> **Đọc báo cáo:** mỗi dòng cho biết nhóm kiểm tra, kết quả và số đo so với giới hạn; dòng cuối là tổng kết. Quy tắc nhanh: **không có FAIL = sẵn sàng nộp.** Cảnh báo nên xem nhưng không chặn.
>
> **Quy trình khuyến nghị:** làm asset → chạy validator → sửa mọi FAIL, xem mọi WARN → chạy lại đến khi báo READY → đính kèm báo cáo vào bài nộp và push lên GitHub.
>
> ---
>
> ### 4. Xử lý sự cố
>
> - **`python is not recognized`:** chưa cài Python hoặc chưa vào PATH → cài lại và tick "Add to PATH".
> - **`ModuleNotFoundError`:** chưa kích hoạt `.venv` hoặc chưa cài package → kích hoạt rồi chạy lại `pip install -r requirements.txt`.
> - **Bỏ qua kiểm tra mesh:** không tìm thấy Maya → khai báo đường dẫn Maya trong config.
> - **Toàn bộ FAIL ở số tri:** đang đếm quad thay vì tam giác, hoặc sai contract → kiểm tra `tri_budget`.
> - **Không tạo được báo cáo:** không có quyền ghi → chọn thư mục `--report` khác.
>
> ---
>
> ### 5. Checklist video demo (khoảng 2–3 phút)
>
> Giới thiệu repo và `asset_contract.json` → chạy validator trên bài nộp **lỗi** và cho xem báo cáo → sửa một lỗi (ví dụ giảm số tri) rồi chạy lại → cho xem báo cáo **đạt**.
>
> ### 6. Checklist dọn repository
>
> - Có source code, config và tài liệu.
> - Engine project chỉ chứa asset cần thiết (bỏ thư mục cache). Unreal: loại `Binaries/`, `Intermediate/`, `Saved/`, `DerivedDataCache/`. Unity: loại `Library/`, `Temp/`, `Logs/`.
> - File nhị phân lớn (`.fbx`, `.psd`, `.uasset`, `.ztl`, `.spp`) dùng Git LFS hoặc để link ngoài.
> - `README.md`, báo cáo này, `AI_REPORT.md` và link video nằm ở thư mục gốc hoặc `/docs`.
