# Status
Last updated: 2026-10-04 (v0.2 session 1: FR-50..53 + deployment files)

## Summary (5 lines max)
اكتمل البناء الأولي الكامل للـ MVP: استخراج PDF (نصي/OCR)، تعيين عربي بخريطة
مواضع، مطابقة حتمية (EXACT/MINOR_DIFF/ALTERED/SEMANTIC_ONLY/NOT_FOUND/
UNRELIABLE_OCR)، حكم صفحات، فروق كلمات، سؤال وجواب مع امتناع، حارس فتوى،
واجهة Streamlit عربية RTL بثلاث شاشات، حذف كامل للبيانات.
44 اختبار وحدة ناجح، ruff نظيف، eval يعمل (3/3 على حالات مرجعية أولية).

## Done
- [FR-01..06, M1, M9] ingest.py: PyMuPDF + إعادة بناء RTL من صناديق الكلمات + Tesseract OCR + تقسيم chunks + تقدّم وتحذير جودة (tests: test_db.py)
- [FR-04, M2] إزاحة ترقيم الطبعة وإعادة حساب printed_page (test_db.py::test_set_page_offset_recomputes_printed_pages)
- [§17.1, K1, C6] normalize.py: تعيين عربي كامل + خريطة مواضع للأصل (test_normalize.py، 10 اختبارات)
- [FR-10..16, FR-18, M3..M5, C1, C2] match.py: بحث تام عبر صفحتين (K2) + مطابقة تقريبية + فروق كلمات + حكم صفحة (test_match.py، 14 اختباراً)
- [FR-20, §16.2, §16.3] index.py + retrieve.py: FTS5 + embeddings محلية (ADR-0001) + RRF + عتبة امتناع (test_db.py)
- [FR-21..26, C3..C5, E4] qa.py + llm.py + safety.py: سؤال وجواب، فحص آلي لكل مقتبس مولّد، امتناع، رفض فتوى، FakeLLMClient (test_qa.py، 6 اختبارات)
- [FR-30..33, S1] claims.py: حكم دعم الاستنتاج مع تحقق حرفي للعبارات (test_claims.py، 3 اختبارات)
- [M10, M11, FR-40..42, UX-01..10] app/: ثلاث شاشات + render_* أربعة + state.py + strings_ar.py + RTL CSS + حذف كامل (D5)
- [T5] eval/run_eval.py + gold_set.csv (هيكل + 3 حالات مرجعية) → eval: 3/3 (100%)
- ADR-0001: embeddings محلية n-gram بدل نموذج خارجي

## Done in v0.2 (session 1)
- [FR-50] عزل الجلسات: data/sessions/<uuid>/ + مفتاح تخزين مؤقت يحوي المسار + تنظيف الجلسات الخاملة (tests/unit/test_session_isolation.py)
- [FR-51] نسبة التطابق في بطاقة الحكم
- [FR-52] رفع PNG/JPG (يمر على نفس خط OCR؛ جُرّب فعليًا مع Tesseract العربي)
- [FR-53] شريط الإفصاح + صفحة الخصوصية (pages/4_privacy.py)
- جاهزية النشر: requirements.txt, packages.txt, LICENSE, .gitignore (يمنع PDF والصور وdata)، sys.path في app/main.py
- الاختبارات: 46 ناجحًا

## Next Tasks (ordered) — v0.2
1. [FR-56] تفعيل LLM عبر Secrets (يحتاج مفتاح مزوّد — D2)
2. [FR-54, FR-55] مستويات المحتوى (أ–د) والإحالة QaStatus.REFERRED وقاعدة الأحاديث
3. [FR-57] Gold Set (40 حالة) + مقارنة Ctrl+F مقابل نقل
4. اختبار OCR على صفحة كتاب حقيقي، ومعايرة العتبات
5. أخطاء mypy الـ16
6. docs/sources_register.md

## Next Tasks (old list, kept for reference)
1. [§20.2] تعبئة Gold Set الحقيقي (40–60 حالة) بعد اختيار كتب الاختبار — يحتاج قرار الفريق
2. [K3] معايرة العتبات على Gold Set وإلحاق نتائج eval/results/
3. [TC-14/15] اختبار مسار OCR على PDF مصوّر حقيقي (يتطلب tesseract-ara على جهاز التشغيل)
4. [S2] إدخال عناصر تحقق دفعة واحدة وتقرير مجمّع
5. [S3] Highlight كلمات على صورة الصفحة (يحتاج إحداثيات OCR)
6. [S4, FR-43] تصدير تقرير Markdown
7. تشغيل mypy naql_core عند توفر الشبكة (انظر الانحرافات)

## Open Questions (NEEDS_CLARIFICATION)
- كل الأسئلة المفتوحة في docs/requirements.md §Open Questions قائمة كما هي؛
  أبرزها: نموذجا LLM وEmbeddings المعتمدان، وعتبات الأحكام النهائية.

## Deviations from AGENTS.md
- mypy لم يُشغَّل في هذه الجلسة بسبب انقطاع الشبكة عن PyPI (تثبيت الحزمة
  تعذّر بعد محاولات متكررة)؛ ruff + 44 اختباراً + فحص التصريف ناجحة، ويُستكمل
  mypy في أول جلسة تتوفر فيها الشبكة.
- embeddings محلية حتمية (n-gram hashing) بدل نموذج دلالي — موثقة في ADR-0001.
