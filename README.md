# catalog — "API" dữ liệu tĩnh của Mobile App Studio

JSON tĩnh phục vụ qua GitHub Pages, cập nhật **hằng tuần bằng GitHub Actions** (không dùng máy của xưởng, không dùng
Claude). Hiện có một bộ dữ liệu: **thư viện dịch vụ của app Subnest** (A001-subnest).
Quyết định gốc: ADR `apps/A001-subnest/docs/adr/0002-remote-catalog-github-pages.md` (repo app, private).

## Địa chỉ

| URL | Dùng cho |
|---|---|
| `https://phamphuongphuongnd.github.io/catalog/subnest/v1/meta.json` | Kiểm tra nhanh có bản mới không (`version`, `sha256`) |
| `https://phamphuongphuongnd.github.io/catalog/subnest/v1/services.min.json` | **App tải file này** (không có `note`) |
| `https://phamphuongphuongnd.github.io/catalog/subnest/v1/services.json` | Bản đầy đủ, dễ đọc, có `note` cho người bảo trì |
| `https://phamphuongphuongnd.github.io/catalog/schema/subnest-v4.schema.json` | JSON Schema |

Cách app nên tải: tối đa 1 lần/ngày → `meta.json`; nếu `version` > bản đang có → tải `services.min.json`, so
`sha256` với `meta.files["services.min.json"].sha256`, parse, kiểm `schemaVersion == 4` → lưu cache. Lỗi bất kỳ →
dùng bản đã cache hoặc bản đóng gói trong app. Đổi schema phá vỡ tương thích sẽ đăng ở đường dẫn mới (`subnest/v2/`),
`v1/` giữ nguyên cho app cũ.

## Schema v4 (Subnest)

Tương thích đọc với v3: mọi trường v3 giữ nguyên tên/kiểu, trừ `Price.approx` được thay bằng `verifiedAt/source/method`.
**Rút gọn 2026-11-06** (ADR 0002 › Sửa đổi): chỉ hai vùng **US** (giá dùng chung cho mọi người, app quy đổi "≈") và
**VN** (giá VND cho dịch vụ bán ở VN, chỉ dùng khi máy ở VN); thêm `storeNames` tuỳ chọn cho bộ quét ảnh.

### Gốc

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `schemaVersion` | `4` | Phiên bản schema. |
| `version` | int ≥ 1 | Phiên bản **dữ liệu**, tăng mỗi lần dữ liệu đổi; nối tiếp v1–v3 đóng gói (bản đầu từ xa = 4). App dùng bản có `version` lớn nhất hợp lệ. |
| `updatedAt` | `YYYY-MM-DD` | Ngày đổi dữ liệu gần nhất. |
| `staleAfterDays` | `90` | Giá có `verifiedAt` cũ hơn số ngày này, hoặc không có `verifiedAt`, là **giá ước tính** (app hiện "≈"). |
| `regions` | object | `{"US":"USD","VN":"VND"}` (cố định). |
| `services` | Service[] | Theo thứ tự danh mục. |

### Service

| Trường | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---|---|
| `id` | slug `^[a-z0-9]+(-[a-z0-9]+)*$` | ✔ | Khoá ổn định, duy nhất, **không bao giờ đổi/xoá/tái sử dụng**. |
| `name` | string | ✔ | Tên hiển thị. |
| `category` | enum | ✔ | `video, music, ai, storage, software, gaming, reading, health, education, telecom, other`. |
| `color` | `#RRGGBB` | ✔ | Nền tile monogram. |
| `monogram` | 1–2 ký tự | ✔ | Chữ trên tile. Cặp (`color`, `monogram`) không trùng. |
| `market` | `global` \| `vn` | ✔ | **Catalog section**: `global` = mục *Chung* (ai cũng thấy); `vn` = mục *Việt Nam* (chỉ hiện khi máy ở VN; có thể chỉ có giá VN). |
| `logoDomain` | host | ✔ | **Mới.** Tên miền cho logo.dev, vd `netflix.com` → `https://img.logo.dev/netflix.com?token=pk_…`. |
| `aliases` | string[] chữ thường | ✔ | Từ khoá tìm kiếm (gồm tiếng Việt không dấu). |
| `storeNames` | string[] | | **Mới (tuỳ chọn).** Tên dịch vụ/gói đúng như hiện trên trang "Gói thuê bao" của Google Play và "Subscriptions" của App Store (vd `"YouTube Premium"`, `"ChatGPT Plus"`, `"Max"`) — bộ quét ảnh khớp theo thứ tự `storeNames` → `name` → `aliases`. Hiện là tên ước lượng, chưa đối chiếu ảnh chụp thật. |
| `cancelUrl`, `manageUrl` | https URL \| null | ✔ | Trang huỷ / quản lý gói. |
| `plans` | Plan[] ≥ 1 | ✔ | Gói đầu là gói mặc định. |
| `note` | string | | Ghi chú nguồn cho người bảo trì. **Không có trong `services.min.json`.** |

### Plan

| Trường | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---|---|
| `id` | slug | ✔ | Duy nhất trong service; không bao giờ xoá. |
| `name` | string | ✔ | Tên gói hiện hành của nhà cung cấp. |
| `status` | `active` \| `closed_to_new` \| `discontinued` | ✔ | **Mới.** `closed_to_new` = người cũ vẫn dùng, không bán mới (ẩn khỏi danh sách chọn, vẫn đọc được id); `discontinued` = ngừng hẳn. App gặp giá trị lạ → coi như `active`. |
| `renamedFrom` | string | | **Mới.** Tên cũ nếu hãng đổi tên gói (id giữ nguyên), vd Evernote `Starter` ← `Personal`. |
| `cycle` | `{unit, count}` | ✔ | `unit` ∈ `day, week, month, year`; `count` ≥ 1. |
| `members` | int ≥ 2 | | Số người tối đa của gói chia sẻ. |
| `prices` | `{REGION: Price}` | ✔ | Giá theo vùng. **Thiếu vùng = không có số liệu**, không phải miễn phí. Gói `active` có ≥ 1 giá. |

### Price

| Trường | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---|---|
| `currency` | ISO 4217 | ✔ | **Luôn bằng tiền tệ của vùng** (validator bắt). |
| `amount` | number > 0 | ✔ | Đơn vị chính (`74000` = 74.000đ, `12.99` = $12.99). VND nguyên; tối đa 2 số lẻ. |
| `verifiedAt` | `YYYY-MM-DD` | đi cùng `source` | Ngày giá được xác minh lần cuối. |
| `source` | https URL | đi cùng `verifiedAt` | Trang đã đọc giá. Giá chuyển từ v3 trỏ về `docs/sources-v3.md#<id>` (ghi chú nguồn đợt tra tay). |
| `method` | `aristocles` \| `vn-parser` \| `manual` | ✔ | Cách lấy giá: API Aristocles · bộ đọc trang VN · người bảo trì nhập tay. |

**Reference price / Giá tham khảo** (thay cho `approx` v3) = không có `verifiedAt` **hoặc** `today − verifiedAt > staleAfterDays`.
App vẫn điền sẵn nhưng hiện chip "Giá tham khảo".

### Ví dụ

```json
{
  "id": "evernote", "name": "Evernote", "category": "software", "color": "#00A82D", "monogram": "Ev",
  "market": "global", "logoDomain": "evernote.com", "aliases": ["evernote", "ghi chu"],
  "cancelUrl": "https://www.evernote.com/Settings.action", "manageUrl": "https://www.evernote.com/Settings.action",
  "plans": [{
    "id": "personal", "name": "Starter", "status": "active", "renamedFrom": "Personal",
    "cycle": {"unit": "month", "count": 1},
    "prices": {"US": {"currency": "USD", "amount": 14.99, "verifiedAt": "2026-11-05",
                      "source": "https://github.com/phamphuongphuongnd/catalog/blob/main/docs/sources-v3.md#evernote",
                      "method": "manual"}}
  }]
}
```

## Nguồn dữ liệu

| Nguồn | Vùng | Trạng thái |
|---|---|---|
| Bản v3 tra tay (2026-11-04/05, WebSearch + trình duyệt) | VN, US | Dữ liệu nền; 247/284 giá có `verifiedAt` 2026-11-05 |
| Bộ đọc trang VN (`tools/vn_parsers/`) | VN | **Chạy hằng tuần** — 7 trang: Netflix VN, Spotify VN, VNPT Internet, VinaPhone BIG90/BIG120, MobiFone TK135, Monkey Junior, FPT Internet |
| Đợt C1 (2026-11-06): +401 dịch vụ toàn cầu, WebSearch giới hạn trang hãng | US | 151 dịch vụ có ≥ 1 giá US `verifiedAt`; phần còn lại là giá tham khảo, `note` ghi "ước lượng" |
| API Aristocles | US | **Không dùng** — xem dưới |
| Nhập tay (PR) | mọi vùng | Sửa `subnest/v1/services.json`, `method: "manual"`, PR được validator kiểm |

Các trang VN không đọc tự động được và lý do: `UNREADABLE` trong `tools/vn_parsers/services.py`
(FPT Play, TV360, VieON, Galaxy Play, Zing MP3, Viettel… đa số là ứng dụng JS hoặc cần đăng nhập; YouTube chọn vùng
theo IP mà runner GitHub đặt ở Mỹ). Lưu ý: runner ở Mỹ — trang nào chặn IP nước ngoài sẽ hiện trong mục "Lỗi đọc" của
báo cáo tuần.

### Aristocles — kết luận điều khoản (tra 2026-11-06)

- Trang: `https://www.aristocles.com.au/products/dataapi`, tài liệu `https://api.aristocles.com.au/docs` (OpenAPI 2.1.0).
  Aristocles Pty Ltd (Úc), sản phẩm của một nhà phát triển cá nhân.
- **Điều khoản:** không có điều khoản riêng cho API. Trang `aristocles.com.au/terms` (02/2025) chỉ áp dụng cho website và
  cấm sao chép/phân phối nội dung khi chưa có văn bản cho phép; OpenAPI không khai `termsOfService`/`license`. FAQ chỉ
  nói được dùng "cho dự án thương mại" ở các gói trả phí — **không nói gì về việc lưu và đăng lại dữ liệu công khai**
  (repo này public, ai cũng tải được).
- **Giới hạn:** Free 100 lượt/ngày; Pro $9/tháng 10.000 lượt/ngày; Enterprise $49/tháng không giới hạn. Đăng ký bằng
  email, khoá dạng `ar_live_…`, gửi qua header `X-API-Key`.
- **Vùng:** "chủ yếu AUD"; tham số `country` nhận AU, US, UK, CA, NZ — catalog chỉ cần **US**. ~50+ dịch vụ.
- **Kết luận (giữ sau khi rút còn US, 2026-11-06): KHÔNG DÙNG** vì quyền đăng lại công khai không rõ → mọi giá US là
  `method: "manual"`. Không có script `fetch_aristocles.py`;
  workflow ghi "bỏ qua" mỗi tuần. Muốn bật: xin phép bằng văn bản (email `hello@aristocles.com.au`) cho việc đăng lại
  giá trong một catalog công khai có ghi nguồn → xem `docs/KEYS.md`.

Hệ quả: giá US cập nhật tay (PR) theo `staleAfterDays`; bộ đọc tự động chỉ chạy cho VN.

## Quy trình hằng tuần (`.github/workflows/weekly.yml`)

Thứ Hai 02:00 UTC (hoặc chạy tay: Actions → weekly-update → Run workflow):

1. `python tools/update.py` — chạy bộ đọc VN (lỗi một trang → giữ giá cũ, ghi vào báo cáo, không dừng lượt);
   ghi giá đọc được kèm `verifiedAt` = hôm nay, `source` = URL trang, `method: "vn-parser"`.
2. Validator so với bản đang đăng. Lỗi cấu trúc → **không đăng**, job đỏ (GitHub gửi email chủ repo).
   Cảnh báo (giá đổi > 50 %, mất một giá, đổi status) → **vẫn đăng** (luật "luôn tự đăng") và ghi vào báo cáo.
3. Dữ liệu đổi → `version` + 1, ghi `services.json`, `services.min.json`, `meta.json`.
4. Ghi `reports/YYYY-MM-DD.md` (giá đổi, đọc lại khớp, lỗi đọc, cảnh báo) → commit + push lên `main` → Pages tự đăng.

Repo public → phút Actions miễn phí. Không cần secret nào.

## Công cụ (Python 3.10+, chỉ thư viện chuẩn)

```bash
python tools/validate.py                                    # kiểm subnest/v1/services.json, exit 0 = OK
python tools/validate.py new.json --published old.json      # + luật không xoá id, cảnh báo giá đổi > 50 %
python tools/update.py --dry-run                            # chạy bộ đọc, in báo cáo, không ghi file
python tools/migrate_v3.py <v3/services.json>               # một lần: v3 (app) -> v4 (đã chạy 2026-11-06)
python tools/import_batch.py batch.txt [--dry-run]           # thêm dịch vụ / storeNames / giá US đã xác minh từ file gọn
python tools/export_app_asset.py ../apps/A001-subnest/assets/catalog   # bản đóng gói cho app (không note) + validator
```

Sửa tay: sửa `subnest/v1/services.json` (đặt `method: "manual"`, `verifiedAt`, `source`), rồi chạy
`python -c "import sys; sys.path.insert(0,'tools'); import common; d=common.load(); d['version']+=1; d['updatedAt']=common.today(); common.write_outputs(d)"`
và `python tools/validate.py`. **Không xoá service/plan** — đổi `status`. PR vào `main` được workflow validate.

Thêm bộ đọc VN: một hàm `@reader` trong `tools/vn_parsers/services.py`, mẫu regex neo vào tên gói, trả
`Reading(service_id, plan_id, amount, url)`; chạy `python tools/update.py --dry-run` để thử.

## Thư mục

```
subnest/v1/   services.json · services.min.json · meta.json     (được Pages phục vụ)
schema/       subnest-v4.schema.json
tools/        common.py · validate.py · update.py · migrate_v3.py · import_batch.py · export_app_asset.py · vn_parsers/
reports/      báo cáo mỗi lượt cập nhật
docs/         KEYS.md (khoá/bí mật — người dùng tự làm) · sources-v3.md (ghi chú nguồn v3)
```

Tên dịch vụ và logo thuộc chủ sở hữu tương ứng; dữ liệu giá chỉ để tham khảo.
