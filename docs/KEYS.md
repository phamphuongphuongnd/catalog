# Khoá & bí mật của repo `catalog` — người dùng tự làm

Luật xưởng: Claude **không** tự đăng ký tài khoản, tạo khoá hay đặt GitHub secret. File này là hướng dẫn để bạn tự làm.

## Hiện tại: KHÔNG cần khoá nào

Workflow hằng tuần chỉ đọc trang giá công khai ở Việt Nam → không cần secret. Aristocles đang **không dùng** vì
chưa rõ quyền đăng lại dữ liệu (README › Aristocles).

## Khi muốn bật Aristocles (chỉ giá US — catalog đã rút còn US + VN từ 2026-11-06)

Chỉ làm khi đã có **văn bản cho phép** đăng lại dữ liệu.

1. **Xin phép** — gửi email tới `hello@aristocles.com.au`, ví dụ:
   > Hi, I run a small subscription-tracker app (Subnest). I'd like to fetch your Subscription Pricing API weekly
   > and republish US prices for the ~50 services you cover (our catalog lists 500+) in a public JSON file on GitHub Pages
   > (github.com/phamphuongphuongnd/catalog), with attribution and a link to Aristocles. Is that allowed on the
   > Free or Pro tier? Thanks.
   Lưu email trả lời (chụp hoặc chuyển tiếp) — đó là căn cứ.
2. **Đăng ký lấy khoá** (miễn phí, 100 lượt/ngày — đủ: chỉ cần vùng US, endpoint `/v1/prices/export?country=US`
   = 1 lượt/tuần):
   ```bash
   curl -X POST https://api.aristocles.com.au/v1/auth/register -H "Content-Type: application/json" -d "{\"email\": \"EMAIL_CUA_BAN\", \"name\": \"TEN_CUA_BAN\"}"
   ```
   Kết quả có `api_key` dạng `ar_live_…`. **Không dán khoá vào chat, notes hay commit.** Lưu vào trình quản lý mật khẩu.
3. **Đặt GitHub secret** (gõ khoá qua stdin, không lưu vào lịch sử shell):
   ```bash
   gh secret set ARISTOCLES_API_KEY -R phamphuongphuongnd/catalog
   ```
   Lệnh sẽ hỏi `? Paste your secret` → dán khoá → Enter. Kiểm tra: `gh secret list -R phamphuongphuongnd/catalog`.
4. **Báo phiên điều phối** "đã có phép + đã đặt ARISTOCLES_API_KEY". Phiên sau sẽ viết `tools/fetch_aristocles.py`
   (đọc khoá từ biến môi trường `ARISTOCLES_API_KEY`, `method: "aristocles"`) và bước workflow chỉ chạy khi secret có.

Thu hồi khoá: `curl -X DELETE https://api.aristocles.com.au/v1/auth/keys/<prefix> -H "X-API-Key: <khoá>"` rồi
`gh secret delete ARISTOCLES_API_KEY -R phamphuongphuongnd/catalog`.

## logo.dev (dùng trong app, không phải repo này)

Khoá publishable `pk_…` của logo.dev do bạn tạo tại https://www.logo.dev (đăng ký → Dashboard → API keys). Khoá này
nằm trong app (được thiết kế để công khai), cấu hình ở repo app — xem ADR 0002. Free tier dùng thương mại phải ghi
nguồn "Logos provided by Logo.dev".
