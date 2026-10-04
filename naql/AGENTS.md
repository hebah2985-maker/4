# AGENTS.md — دستور مشروع نقل (Naql)

هذا الملف ملزم لأي نموذج ذكاء اصطناعي أو مطوّر يعمل على المشروع. اقرأه كاملاً قبل كتابة أي سطر.

## ترتيب المرجعية عند التعارض
1. `docs/requirements.md` — ما الذي يُبنى.
2. هذا الملف — كيف يُبنى.
3. `docs/decisions/` — سجل القرارات (ADR): استثناءات موثقة.
4. التعليقات داخل الكود — مرجع أضعف.

## الدستور (قواعد لا تُكسر)
- **C1**: لا يُعرض أي اقتباس للمستخدم دون فحص وجود آلي في نص المصدر (`verify_quote_exists`).
- **C2**: المطابقة والفروق والصفحات حتمية (Deterministic). يُمنع استخدام LLM في حكم `EXACT/MINOR_DIFF/ALTERED/NOT_FOUND`.
- **C3**: LLM يُستدعى فقط عبر `LLMClient` وفي موضعين: `qa.py` و`claims.py`.
- **C4**: الامتناع يُفضَّل على التخمين عند ضعف الدليل (`ABSTAINED` / `NOT_FOUND`).
- **C5**: لا فتوى ولا ترجيح ولا حكم على صحة معنى ديني. تُرفض بلطف عبر `safety.py`.
- **C6**: لا يُعدَّل النص الأصلي للمصدر أبداً. التعيين على نسخة مؤقتة مع خريطة مواضع.
- **C7**: لا ميزة خارج المتطلبات دون رقم متطلب مرتبط (FR-xx / M# / S#).
- **C8**: لغة الواجهة غير اتهامية: «وُجدت كلمة مختلفة» لا «حرّفت النص».
- **C9**: لا يُسجَّل نص المستخدم في السجلات ولا يُرسَل لخدمة خارجية عبر غير `LLMClient`.
- **C10**: لا أسرار في الكود — متغيرات بيئة فقط.

## التقنيات
- Python ≥ 3.11، Ruff (100 عمود)، mypy strict على `naql_core/`، pytest.
- `sqlite3` المدمج (ممنوع ORM). واجهة Streamlit. `Makefile`: setup/run/test/lint/eval.
- ممنوع: Docker كشرط تشغيل، قواعد متجهات خارجية، أوامر بوابة، LangChain/LlamaIndex إلا بـ ADR.

## بنية الملفات
```
naql/
├─ AGENTS.md / README.md / pyproject.toml / Makefile / .env.example
├─ docs/ (requirements.md, STATUS.md, decisions/)
├─ app/ (main.py, pages/, components/, state.py, strings_ar.py)
├─ naql_core/ (config, thresholds, models, errors, db, schema.sql,
│              ingest, normalize, match, index, retrieve, llm, qa, claims, safety)
├─ prompts/ (qa_answer.v1.md, claim_support.v1.md)
├─ eval/ (gold_set.csv, run_eval.py, results/)
├─ tests/unit + tests/fixtures
└─ data/ (خارج git)
```

## قواعد البنية
- S1: اتجاه الاعتماد `app → naql_core` فقط؛ ممنوع استيراد streamlit في `naql_core`.
- S2: `models/errors/config/thresholds` لا تستورد شيئاً من الحزمة؛ `match` يستورد `models/normalize`؛ ممنوع الاعتماد الدائري.
- S3: ملف واحد = مسؤولية واحدة. يُقسم الملف إذا تجاوز 400 سطر.
- S4: ممنوع `utils.py`/`helpers.py`/`common.py`.
- S5: أي ملف جديد خارج هذه البنية يحتاج سبباً موثقاً في `STATUS.md`.
- S6: `__init__.py` يصدّر الواجهة العامة فقط بـ `__all__`.
- S7: كل نصوص الواجهة العربية في `app/strings_ar.py` فقط.

## التسمية
- snake_case للملفات والمتغيرات والدوال؛ PascalCase للأصناف وEnum وdataclass؛ UPPER_SNAKE_CASE للثوابت؛ `_` بادئة للخاص.
- N5: `pdf_page` (ترتيب الملف) و`printed_page` (ترقيم الطبعة) — ممنوع `page` المبهم.
- N6: قيم الأحكام ثابتة: Verdict(EXACT/MINOR_DIFF/ALTERED/SEMANTIC_ONLY/NOT_FOUND/UNRELIABLE_OCR)، PageVerdict(PAGE_OK/PAGE_WRONG/PAGE_UNKNOWN)، ClaimVerdict(SUPPORTED/PARTIAL/EXCEEDS_TEXT/NOT_PROVEN_IN_SOURCE/CONTRADICTED)، QaStatus(ANSWERED/ABSTAINED/REFUSED)، TextSource(TEXT_LAYER/OCR).
- N7: لا ترجمة أسماء الكود للعربية ولا حروف عربية في المعرّفات.

## أسلوب الكود
- CS1: كل ملف يبدأ بـ `from __future__ import annotations`. CS2: type hints إلزامية في `naql_core/`.
- CS4: مسارات بـ `pathlib.Path`، فتح ملفات بـ `encoding="utf-8"`، نصوص بـ f-strings.
- CS5: لا أرقام سحرية — الثوابت والعتبات في `thresholds.py` فقط.
- CS6: لا `print()` للتصحيح — استخدم `logging`.
- CS9: TODO بصيغة `# TODO(FR-xx): ...` فقط.
- E1: استثناءات مخصصة ترث `NaqlError` في `errors.py`. E2: ممنوع `except:`/‎`except Exception` إلا عند نقطة دخول الواجهة.
- E4: فشل LLM أو تحقق مخرجاته → إعادة محاولة واحدة → `ABSTAINED`.
- L1/L2: logging قياسي؛ ممنوع تسجيل نصوص الاقتباسات/الأسئلة/المصدر.
- F1: الدالة تفعل شيئاً واحداً، ≤ 40 سطراً هدف، 60 حد أقصى، ≤ 3 مستويات تداخل.
- F2: > 3 معاملات موضعية → keyword-only أو dataclass. F3: ممنوع افتراضيات قابلة للتعديل.
- F4: دوال `normalize.py` و`match.py` نقية. F5: الإدخال/الإخراج محصور في ingest/db/index/llm.
- F6: مخرجات كيانات مسماة (`@dataclass(frozen=True)`). F8: لا حالة عامة.

## منطق حساس
- K1: `normalize_for_match(text) -> NormalizedText` تعيد النص المعيّن وخريطة مواضع للأصل.
- K2: يُبنى للمصدر نص متصل واحد مع جدول مواضع صفحات لدعم اقتباس يعبر صفحتين.
- K3: كل عتبة في `thresholds.py` بتعليق قيمتها المعيارية وتاريخها؛ تغييرها يستلزم `make eval`.
- K4: كل مخرج LLM يمر بالتحقق بالمخطط ثم `verify_quote_exists` لكل مقتبس ثم عرض مقتضب.
- K5: الموجّهات في `prompts/` فقط بإصدارات؛ تعديل موجّه = ملف إصدار جديد.

## قاعدة البيانات
- D1: المخطط في `schema.sql` + جدول `schema_version`؛ التغيير بملفات ترحيل مرقمة في `migrations/`.
- D2: استعلامات بمعاملات مربوطة `?` دائماً.
- D3: الوصول لـ SQLite عبر دوال مسماة في `db.py`/`index.py` فقط.
- D5: `delete_document` تمسح كل الجداول والملفات المرتبطة في عملية واحدة، ولها اختبار.

## الاختبارات والتقييم
- T1: اسم الاختبار `test_<behavior>_<condition>`. T2: بنية `tests/unit/` تعكس `naql_core/`.
- T4: الاختبارات لا تتصل بالشبكة ولا تستخدم LLM حقيقياً — `FakeLLMClient`.
- T6: لا يُحذف اختبار فاشل؛ يُصلَح الكود أو يُعاد النظر في الاختبار بسبب موثق.

## التسليم بين النماذج
- عند البدء: اقرأ بالترتيب AGENTS.md → docs/requirements.md → docs/STATUS.md → docs/decisions/، وشغّل `make test` و`make lint`.
- عند الإنهاء: `make lint && make test` ناجحان (و`make eval` عند مس المنطق الحساس)، حدّث STATUS.md، ووثّق أي انحراف.
- ملف `project_progress` في الجذر: يوثّق (1) المنجز (2) الجاري (3) المتبقي، ويُحدَّث باستمرار.
