import requests
from supabase import create_client
import os

# جلب المفاتيح من إعدادات GitHub الآمنة
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_global_movies(pages=25): # هنجيب 500 فيلم في المرة الواحدة
    for page in range(1, pages + 1):
        # طلب الأفلام الأكثر شهرة عالمياً باللغة العربية
        url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=ar-SA&page={page}"
        response = requests.get(url).json()
        
        for movie in response.get('results', []):
            m_id = movie['id']
            
            # جلب "التفاصيل العميقة" (الممثلين، التريلر، الصور الكبيرة)
            detail_url = f"https://api.themoviedb.org/3/movie/{m_id}?api_key={TMDB_API_KEY}&language=ar-SA&append_to_response=videos,credits"
            d = requests.get(detail_url).json()
            
            # استخراج بيانات الممثلين (أول 10 ممثلين بصورهم)
            cast = [{"name": c["name"], "image": f"https://image.tmdb.org/t/p/w200{c['profile_path']}"} 
                    for c in d.get('credits', {}).get('cast', [])[:10] if c.get('profile_path')]
            
            # استخراج رابط التريلر من يوتيوب
            trailer = next((f"https://www.youtube.com/embed/{v['key']}" 
                           for v in d.get('videos', {}).get('results', []) 
                           if v['site'] == 'YouTube' and v['type'] == 'Trailer'), None)

            # تجهيز بيانات الفيلم للشكل العالمي
            movie_entry = {
                "tmdb_id": m_id,
                "title": movie['title'],
                "slug": movie['title'].lower().replace(" ", "-") + f"-{m_id}", # رابط SEO احترافي
                "description": movie['overview'] or "لا يوجد وصف حالياً",
                "poster_path": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}",
                "backdrop_path": f"https://image.tmdb.org/t/p/original{movie['backdrop_path']}", # صورة الخلفية
                "release_date": movie['release_date'],
                "vote_average": movie['vote_average'],
                "trailer_url": trailer,
                "cast_data": cast, # بيانات الممثلين JSON
                "quality": "BlueRay 1080p", # جودة افتراضية عالية
                "category_name": "أفلام أجنبي"
            }

            # حفظ البيانات (تحديث لو موجودة أو إضافة لو جديدة)
            supabase.table("movies").upsert(movie_entry, on_conflict="tmdb_id").execute()
            print(f"🎬 تم ضخ الفيلم: {movie['title']}")

if __name__ == "__main__":
    get_global_movies()
