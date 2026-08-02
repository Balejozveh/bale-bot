<<<<<<< HEAD
# bale-bot
بات بله — جمع‌آوری واریزی جزوه‌ها (مشترک با بات تلگرام)
=======
# بله بات — جمع‌آوری واریزی جزوه‌ها

همون بات تلگرام، ولی برای پیام‌رسان **بله**.

## امکانات
- انتخاب درس (حسابان ۳۸۰K / هندسه ۲۸۰K)
- مهلت واریز + مسدودسازی بعد از مهلت
- آپلود خودکار رسید به GitHub (ریپوی عمومی `jozvehtelegram/receipts`)
- ذخیره در Cloudflare D1 (مشترک با بات تلگرام)
- تایید/رد توسط ادمین

## متغیرهای محیطی (Railway Variables)
| نام | توضیح |
|---|---|
| `BOT_TOKEN` | توکن بات بله (از @BotFather بله) |
| `ADMIN_ID` | آیدی عددی ادمین |
| `CARD_NUMBER` | شماره کارت |
| `CARD_HOLDER` | نام صاحب کارت |
| `GH_TOKEN` | توکن گیت‌هاب (دسترسی به ریپوی receipts) |
| `GH_REPO` | `jozvehtelegram/receipts` |
| `CF_TOKEN` | توکن کلادفلر |
| `CF_ACCOUNT` | Account ID کلادفلر |
| `CF_DB` | D1 Database ID |

## نکته
دیتابیس D1 **مشترک** با بات تلگرام است — واریزی از هر دو پلتفرم در یک جدول ذخیره می‌شود و HTML هر دو را نمایش می‌دهد.
>>>>>>> 40215fe (feat: Bale bot — same payment flow, shared D1 + GitHub receipts)
