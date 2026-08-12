# AI Shorts Factory

أداة أوتوماتيك لإنتاج ونشر فيديوهات شورتس على يوتيوب — نيتش قصص نفسية/سلوكية قصيرة بالإنجليزي.

## الإعداد (مرة وحدة)

1. **ارفع هالمجلد على GitHub** كـ repository **عام (Public)** — مهم لتجنب أي طلب بطاقة من GitHub Actions.
2. **جهّز المفاتيح:**
   - `GEMINI_API_KEY`: من https://aistudio.google.com/apikey
   - `PEXELS_API_KEY`: من https://www.pexels.com/api/
   - `YOUTUBE_CREDENTIALS`: بيانات OAuth بصيغة JSON بعد ربط قناتك (عبر Google Cloud Console → فعّل YouTube Data API v3 → أنشئ OAuth Client → استخدم أداة مساعدة مرة وحدة لتوليد التوكن)
3. **حط المفاتيح كـ Secrets:**
   Repository → Settings → Secrets and variables → Actions → New repository secret (لكل مفتاح من الثلاثة فوق)
4. **جرّب يدوياً أول مرة** قبل ما تعتمد على الجدولة:
   ```bash
   pip install -r requirements.txt
   python main.py --count 1
