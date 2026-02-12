import asyncio
import aiohttp
import os
from supabase import create_client

# إعدادات البيئة
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# دالة ذكية لجلب البيانات بسرعة البرق (Concurrent Requests)
async def fetch_json(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            return await response.json()
        return None

# معالج الأفلام العملاق
async def process_movie(session, movie_id):
    # جلب (التفاصيل + الممثلين + الفيديوهات + الكلمات المفتاحية + المشابهة) في ضربة واحدة
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=ar-SA&append_to_response=credits,videos,keywords,similar"
    data = await fetch_json(session, url)
    
    if not data: return

    # استخراج السيرفرات (محاكاة ذكية)
    trailer = next((v['key'] for v in data.get('videos', {}).get('results', []) if v['site'] == 'YouTube'), None)
    
    # تحويل البيانات لهيكل ضخم
    movie_record = {
        "tmdb_id": data['id'],
        "imdb_id": data.get('imdb_id'),
        "slug": f"{data['title'].replace(' ', '-').lower()}-{data['id']}",
        "title": data['title'],
        "overview": data.get('overview'),
        "genres": [g['name'] for g in data.get('genres', [])], # تخزين التصنيفات كمصفوفة
        "rating": data.get('vote_average'),
        "poster": data.get('poster_path'),
        "backdrop": data.get('backdrop_path'),
        "cast": [{"name": c['name'], "role": c['character'], "img": c['profile_path']} for c in data.get('credits', {}).get('cast', [])[:10]],
        "keywords": [k['name'] for k in data.get('keywords', {}).get('keywords', [])],
        "servers": [
            {"name": "Fast Server 1", "quality": "1080p", "url": f"https://www.youtube.com/embed/{trailer}"} if trailer else None
        ]
    }

    # الإدخال الذكي (Upsert) - لو موجود حدثه، لو جديد ضيفه
    try:
        supabase.table("advanced_movies").upsert(movie_record, on_conflict="tmdb_id").execute()
        print(f"✅ Processed: {data['title']}")
    except Exception as e:
        print(f"❌ Error: {e}")

# المحرك الرئيسي (The Orchestra)
async def main():
    async with aiohttp.ClientSession() as session:
        # 1. جلب قائمة التريند
        trend_url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_API_KEY}&language=ar-SA"
        trending = await fetch_json(session, trend_url)
        
        if trending:
            tasks = []
            # 2. تجهيز المهام كلها مرة واحدة (Parallel Execution)
            for movie in trending['results']:
                tasks.append(process_movie(session, movie['id']))
            
            # 3. تنفيذ كل المهام في نفس اللحظة!
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
