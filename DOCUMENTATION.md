# 📚 دليل التوثيق الشامل لمشروع فرز السير الذاتية الآلي
# Automated Resume Screening - Complete Documentation & Technical Report

---

## 📑 فهرس المحتويات (Table of Contents)

1. [نظرة عامة على المشروع (Project Overview)](#1-نظرة-عامة-على-المشروع-project-overview)
2. [المشكلات التي تم حلها لرفع الدقة (Key Problem Solved)](#2-المشكلات-التي-تم-حلها-لرفع-الدقة-key-problems-solved)
3. [الهيكل المعماري والتقنيات (Architecture & Tech Stack)](#3-الهيكل-المعماري-والتقنيات-architecture--tech-stack)
4. [الخوارزمية والمعادلة الرياضية (Algorithm & Mathematical Formulation)](#4-الخوارزمية-والمعادلة-الرياضية-algorithm--mathematical-formulation)
5. [شرح ملفات المشروع (File Breakdown)](#5-شرح-ملفات-المشروع-file-breakdown)
6. [دليل التثبيت والتشغيل (Installation & Run Guide)](#6-دليل-التثبيت-والتشغيل-installation--run-guide)
7. [دليل استخدام واجهة الويب (Web UI User Manual)](#7-دليل-استخدام-واجهة-الويب-web-ui-user-manual)
8. [الاختبارات وضمان الجودة (Testing & Quality Assurance)](#8-الاختبارات-وضمان-الجودة-testing--quality-assurance)

---

## 1. نظرة عامة على المشروع (Project Overview)

مشروع **Automated Resume Screening** هو نظام ذكي مصمم لمساعدة فرق الموارد البشرية (HR) ومسؤولي التوظيف على تقييم وفرز السير الذاتية للمتقدمين للوظائف آلياً بدقة متناهية وسرعة فائقة. يقوم النظام بمقارنة متطلبات الوظيفة (Job Description) بمحتوى السير الذاتية (Resumes) واستخراج ترتيب دقيق للمرشحين بحسب نسبة التطابق الحقيقية.

### الأهداف الأساسية:
- **توفير الوقت:** فرز مئات السير الذاتية في ثوانٍ معدودة بدلاً من المراجعة اليدوية المرهقة.
- **العدالة والدقة:** التقييم بناءً على امتلاك المهارات الفعلية ومطابقة الخبرة دون تحيز.
- **الشفافية:** إظهار الأسباب الدقيقة لحصول المرشح على درجته (المهارات المتوفرة، المهارات الناقصة، والمهارات المنفية).

---

## 2. المشكلات التي تم حلها لرفع الدقة (Key Problems Solved)

في النماذج التقليدية القديمة المعتمدة على `TF-IDF + Cosine Similarity` البسيطة، ظهرت مشاكل خطيرة جعلت الدقة منخفضة والنتائج غير منطقية:

| المشكلة القديمة | أثرها السلبي | كيف تم حلها في هذا المشروع؟ |
|:---|:---|:---|
| **تخفيف النسبة (Length Dilution)** | السيرة الذاتية الطويلة ينخفض تقييمها إلى 20%-28% حتى لو كان المرشح يملك كل المهارات. | استخدام وزن أساسي بنسبة **80% لتغطية المهارات** مع معايرة تشابه السياق. |
| **عمى النفي (Negation Blindness)** | المرشح الذي يكتب "No Machine Learning" يحصل على درجات إيجابية لكلمتي Machine و Learning! | بناء **محرك اكتشاف النفي (Negation Detector)** يخصم 15%-45% من المرشح غير المؤهل. |
| **تعدد صيغ الكلمات (Morphological Variations)** | كلمة `pipelines` لا تتطابق مع `pipeline`، و `building` لا تتطابق مع `built`. | دمج **NLTK Porter Stemmer** لتوحيد الكلمات لجذورها اللغوية الأصلية. |
| **غياب المرادفات التقنية** | النظام لا يفهم أن `PostgreSQL` تعني `SQL` أو أن `PySpark` تعني `Spark`. | إضافة **قاموس مرادفات تقني واسع (Tech Taxonomy)** يغطي هندسة البيانات، السحابة، والويب. |

---

## 3. الهيكل المعماري والتقنيات (Architecture & Tech Stack)

```mermaid
flowchart LR
    subgraph Inputs [المدخلات]
        JD[الوصف الوظيفي]
        CV1[سيرة ذاتية PDF]
        CV2[سيرة ذاتية Word]
        CV3[سيرة ذاتية نصية]
    end

    subgraph Processing [محرك المعالجة]
        Ext[استخراج النصوص والمصطلحات]
        Stem[NLTK Porter Stemming]
        Tax[قاموس المرادفات التقنية]
        Neg[كاشف عبارات النفي]
        TFIDF[Sublinear TF-IDF]
    end

    subgraph Output [المخرجات والواجهة]
        Score[النسبة الإجمالية 0-100%]
        Breakdown[تفصيل المهارات: محققة / ناقصة / منفية]
        WebUI[لوحة تحكم تفاعلية Web Dashboard]
    end

    Inputs --> Processing
    Processing --> Output
```

### التقنيات المستخدمة:
- **Python 3.10+**: لغة البرمجة الأساسية.
- **Flask**: لتشغيل السيرفر المحلي وبناء واجهة الـ API.
- **NLTK (PorterStemmer)**: للمعالجة اللغوية وتوحيد الجذور.
- **Scikit-Learn**: لحساب متجهات TF-IDF والتشابه الجيبي (Cosine Similarity).
- **pypdf**: لقراءة واستخراج النصوص من ملفات الـ PDF.
- **python-docx**: لقراءة واستخراج النصوص من ملفات Word (.docx).
- **HTML5 / Modern Vanilla CSS / JavaScript**: لواجهة المستخدم العصرية التفاعلية.
- **Pytest**: لاختبار كفاءة ودقة النظام آلياً.

---

## 4. الخوارزمية والمعادلة الرياضية (Algorithm & Mathematical Formulation)

يتم احتساب النتيجة النهائية لكل مرشح بناءً على معادلة هجينة ذكية:

$$\text{Final Score} = \max\Big(0.0, \min\big(1.0, 0.80 \times S_{\text{skills}} + 0.20 \times S_{\text{context}} - \text{Penalty}\big)\Big)$$

### عناصر المعادلة:
1. **نسبة تطابق المهارات ($S_{\text{skills}}$ - بوزن 80%):**
   $$S_{\text{skills}} = \frac{\text{عدد المهارات التقنية المتطابقة}}{\text{إجمالي المهارات المطلوبة في الوظيفة}}$$
   تتم المقارنة باستخدام الجذور اللغوية (Stemmed Tokens) وقاموس المرادفات التقنية (Aliases).

2. **نسبة ملاءمة السياق ($S_{\text{context}}$ - بوزن 20%):**
   $$S_{\text{context}} = \min\left(1.0, \frac{\text{Cosine Similarity}}{0.35}\right)$$
   تمت معايرة المقام عند 0.35 لمنع هبوط النسب بسبب طول السيرة الذاتية واختلاف الكلمات العامة.

3. **خصم عبارات النفي ($\text{Penalty}$):**
   $$\text{Penalty} = \min\big(0.45, \text{عدد المهارات المنفية} \times 0.15\big)$$
   عندما يذكر المرشح عدم امتلاكه لمهارة مطلوبة (مثل `no experience in kafka`) يتم خصم نقاط منه مباشرة.

---

## 5. شرح ملفات المشروع (File Breakdown)

| الملف | الوظيفة والدور |
|:---|:---|
| [main.py](file:///c:/Users/mackk/Downloads/Automated_Resume_Screening-20261017T215226Z-1-001/Automated_Resume_Screening/main.py) | **المحرك الأساسي:** يحتوي على دوال استخراج المصطلحات، توحيد الجذور بـ Stemming، كشف النفي، وحساب درجات التقييم. |
| [app.py](file:///c:/Users/mackk/Downloads/Automated_Resume_Screening-20261017T215226Z-1-001/Automated_Resume_Screening/app.py) | **خادم الويب:** تطبيق Flask يدير نقاط الاتصال (`/api/screen`, `/api/presets`) ويدمج الملفات المرفوعة مع المحرك. |
| [resume_parser.py](file:///c:/Users/mackk/Downloads/Automated_Resume_Screening-20261017T215226Z-1-001/Automated_Resume_Screening/resume_parser.py) | **محلل ومستخرج الملفات:** يستخرج النصوص من ملفات PDF و Word و TXT، ويقوم بتصنيف الكلمات المتطابقة والناقصة والمنفية. |
| [interactive_test.py](file:///c:/Users/mackk/Downloads/Automated_Resume_Screening-20261017T215226Z-1-001/Automated_Resume_Screening/interactive_test.py) | **أداة سطر الأوامر (CLI):** تتيح تجربة النظام واختبار مجلدات كاملة من السير الذاتية مباشرة من التيرمينال. |
| [test_main.py](file:///c:/Users/mackk/Downloads/Automated_Resume_Screening-20261017T215226Z-1-001/Automated_Resume_Screening/test_main.py) | **ملف الاختبارات الآلية (Pytest):** يحتوي على 10 اختبارات شاملة تغطي كافة الحالات والحدود الرياضية. |
| `templates/index.html` | واجهة المستخدم الرئيسية (Dashboard UI). |
| `static/style.css` | تصميم الواجهة (Dark Mode عصري مع تأثيرات Glassmorphism وتجاوب كامل). |
| `static/app.js` | البرمجة التفاعلية للمتصفح، رفع الملفات، الرسوم المتحركة، واستدعاء الـ API. |
| `sample_resumes/` | مجلد يضم نماذج حقيقية لسير ذاتية بتنسيقات مختلفة (.txt, .docx). |

---

## 6. دليل التثبيت والتشغيل (Installation & Run Guide)

### الخطوة 1: تثبيت المتطلبات
افتح موجه الأوامر (Terminal / PowerShell) في مجلد المشروع ونفذ:
```bash
pip install -r requirements.txt
```

### الخطوة 2: تشغيل واجهة الويب (الطريقة المفضلة)
```bash
python app.py
```
ثم افتح الرابط في المتصفح:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

### الخطوة 3: تشغيل الأداة عبر التيرمينال (CLI)
```bash
python interactive_test.py
```

### الخطوة 4: تشغيل السكربت البسيط
```bash
python main.py
```

---

## 7. دليل استخدام واجهة الويب (Web UI User Manual)

1. **القوالب السريعة (Quick Presets):**
   - اضغط على **"Data Engineer"** أو **"Python & ML"** أو **"Frontend React"** لتعبئة الوظيفة والمرشحين تلقائياً لتجربة فورية بنقرة واحدة.
2. **المساعد والتفاعل الصوتي (AI Voice Screener & Assistant):**
   - **تسجيل الصوت الحي:** اضغط على زر **"🎙️ Start Voice Recording"** وتحدث عبر الميكروفون بالأمر أو متطلبات الوظيفة أو اسأل عن أفضل مرشح، ثم اضغط إنهاء وإرسال.
   - **الرد الصوتي المتبادل:** يقوم النظام فوراً بتحويل صوتك إلى نص وفهم المطلوب، فرز المرشحين، ثم **الرد عليك بتسجيل صوتي فوري (Voice Response)** يقدم لك ملخصاً شاملاً لأفضل مرشح ونسبته وأبرز مهاراته!
   - **تسجيل الصوت الحي في الشات (Chat Voice Note Recording):** يمكنك تسجيل ريكورد صوتي كامل ومباشر داخل شات الذكاء الاصطناعي (Ollama AI Recruiter) عبر زر الميكروفون المطور، مع ظهور شريط تسجيل تفاعلي ومؤقت حي وأمواج صوتية حمراء، وتفريغ فوري للنص عبر خادم الصوت وإرساله تلقائياً.
   - **الدليل الصوتي الشامل (Voice Tutorial & System Walkthrough):** دليل صوتي تفاعلي باللغتين العربية والإنجليزية يشرح خطوات النظام، مع كاش ذكي مزدوج (In-Memory Server & Client Caching) يمنع التكرار نهائياً ويسرّع الاستجابة في أجزاء من الثانية مع أزرار تشغيل وإيقاف تام (Stop) وإعادة تشغيل ومنع التكرار التلقائي.
   - **مشغل الصوت المدمج:** يحتوي الرد على مشغل صوتي تفاعلي مع أمواج صوتية متحركة (Soundwave Animation)، أزرار تشغيل/إيقاف مؤقت، وإعادة تشغيل (Replay)، وخيار التشغيل التلقائي (Auto-play).
   - **رفع ملف صوتي:** يمكنك رفع تسجيل صوتي مسجل مسبقاً (.wav, .mp3, .ogg, .m4a).
   - **الإملاء الصوتي المباشر:** أزرار ميكروفون مصغرة على خانة متطلبات الوظيفة وبطاقات المرشحين لكتابة السير ذاتياً بالصوت.
   - **الاستماع لمراجعة الفائز:** زر **"🔊 Speak Review"** في شارة الفائز لقراءة تقييم المرشح الأول صوتياً.
3. **إدخال وظيفة مخصصة:**
   - اكتب متطلبات الوظيفة الخاصة بك في صندوق **"Job Description"** أو أملها بالصوت.
4. **إدخال المرشحين:**
   - **الخيار الأول (نصوص):** اكتب اسم المرشح والصق محتوى سيرته الذاتية أو أملها صوتياً.
   - **الخيار الثاني (رفع ملفات):** انتقل إلى تبويب **"Upload Files"** واسحب ملفات الـ PDF أو Word (.docx) أو Text (.txt) مباشرة.
5. **الفرز والنتائج:**
   - اضغط على الزر البنفسجي الكبير **"⚡ Screen & Rank Resumes"** أو اطلب ذلك صوتياً.
   - ستظهر لوحة النتائج فوراً مع شارة الفائز 🏆، أشرطة التقدم الملونة، والبطاقات التفصيلية لكل مهارة تم العثور عليها أو فقدانها.

---

## 8. الاختبارات وضمان الجودة (Testing & Quality Assurance)

تم تزويد المشروع بمجموعة اختبارات آلية محكمة تضمن عمل الخوارزميات ونظام المعالجة الصوتية دون أي أخطاء.

لتشغيل الاختبارات كاملة:
```bash
python -m pytest test_voice.py test_main.py -v
```

### ملخص الاختبارات التي يتم إجراؤها (26 اختباراً):

#### أولاً: اختبارات خوارزميات الفرز والذكاء الاصطناعي (`test_main.py`):
1. `test_default_dataset_ranking`: التحقق من تقييم وترتيب جميع المرشحين بدقة.
2. `test_ranking_is_sorted_descending`: التأكد من أن الترتيب تنازلي دائمًا (الأفضل أولاً).
3. `test_scores_are_within_valid_bounds`: التأكد من أن جميع النسب تقع حصراً بين 0% و 100%.
4. `test_perfect_match_score`: التحقق من أن السيرة الذاتية المتطابقة تماماً تأخذ 100%.
5. `test_stemming_variation_matching`: التأكد من نجاح مطابقة صيغ الجمع والمفرد وتصريفات الأفعال.
6. `test_data_engineering_domain`: التحقق من دقة التقييم لمهارات هندسة البيانات والسحابة.
7. `test_negation_penalty_applied`: التأكد من خصم النقاط للمرشح الذي ينفي امتلاكه للمهارة.
8. `test_relative_qualification_ranking`: التأكد من أن المرشح الأكثر كفاءة يسبق دائماً الأقل كفاءة.
9. `test_single_candidate`: التحقق من سلامة العمل عند وجود مرشح واحد فقط.
10. `test_display_results_runs_without_error`: التحقق من عمل دالة الطباعة ومخرجات الكونسول بسلاسة.

#### ثانياً: اختبارات نظام الصوت والتسجيل والرد الصوتي (`test_voice.py`):
11. `test_is_arabic_text_detection`: التأكد من الكشف الذكي عن اللغة العربية والإنجليزية في النصوص المنطوقة.
12. `test_generate_audio_speech_english`: التحقق من توليد تسجيل صوتي عالي الجودة بالإنجليزية بصيغة Base64.
13. `test_generate_audio_speech_arabic`: التحقق من توليد تسجيل صوتي باللغة العربية.
14. `test_generate_audio_speech_empty_text_fallback`: التحقق من المعالجة الآمنة للنصوص الفارغة بدون أي توقف.
15. `test_formulate_screening_speech_response`: التحقق من صياغة ملخص صوتي واضح ودقيق للمرشح الفائز ومهاراته.
16. `test_process_voice_command_screen_intent`: التحقق من إدراك نية الفرز عبر الصوت وإرجاع النتائج مصحوبة برد صوتي.
17. `test_process_voice_command_load_preset`: التحقق من استجابة النظام الصوتي لأمر تحميل القوالب الجاهزة.
18. `test_process_voice_command_update_job`: التحقق من قدرة النظام على إملاء وتحديث متطلبات الوظيفة صوتياً.
19. `test_transcribe_audio_file_safe_handling`: التحقق من أمان معالجة وقراءة ملفات الصوت بصيغة WAV ومعالجة الصمت.
20. `test_api_voice_speak_success`: فحص نقطة النهاية `/api/voice/speak` وتوليد الصوت بنجاح.
21. `test_api_voice_speak_missing_text`: التحقق من التحقق من صحة المدخلات وإرجاع كود 400 عند غياب النص.
22. `test_api_voice_interact_with_text_command`: فحص تكامل نقطة النهاية `/api/voice/interact` لفرز المرشحين صوتياً.
23. `test_api_voice_interact_with_audio_file_upload`: التحقق من قبول ومعالجة ملف صوتي مرفوع بتقنية `multipart/form-data`.
24. `test_api_voice_transcribe_missing_file`: التحقق من المعالجة السليمة للأخطاء في نقطة تفريغ الصوت.
25. `test_voice_tutorial_endpoint_and_caching`: التحقق من عمل نقطة تفريغ الدليل الصوتي وتفعيل الكاش السريع لمنع التكرار.
26. `test_api_voice_transcribe_with_audio_file`: التحقق من قبول واستقبال ملفات الريكورد الصوتي وتفريغها بنجاح.

**النتيجة النهائية:** نجاح **26 من أصل 26 اختباراً** بنسبة **100%**.

