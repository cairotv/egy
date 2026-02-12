import requests
from supabase import create_client
import os

# إعدادات الربط (سنجلبها من إعدادات GitHub الآمنة)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_movies(pages=5): # يمكنك زيادة عدد الصفحات لجلب آلاف الأفلام
    for page in range(1, pages + 1):
        url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=ar-SA&page={page}"
        response = requests.get(url).json()
        
        for movie in response.get('results', []):
            movie_id = movie['id']
            
            # جلب تفاصيل إضافية (الممثلين والتريلر)
            detail_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=ar-SA&append_to_response=videos,credits"
            details = requests.get(detail_url).json()
            
            # تجهيز البيانات الاحترافية
            cast = [{"name": c["name"], "image": f"https://image.tmdb.org/t/p/w200{c['profile_path']}"} 
                    for c in details.get('credits', {}).get('cast', [])[:10] if c.get('profile_path')]
            
            trailer = next((f"https://www.youtube.com/watch?v={v['key']}" 
                           for v in details.get('videos', {}).get('results', []) 
                           if v['site'] == 'YouTube' and v['type'] == 'Trailer'), None)

            # تجهيز السجل للحفظ في Supabase
            movie_data = {
                "tmdb_id": movie_id,
                "title": movie['title'],
                "slug": movie['title'].lower().replace(" ", "-") + f"-{movie_id}",
                "description": movie['overview'],
                "poster_path": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}",
                "backdrop_path": f"https://image.tmdb.org/t/p/original{movie['backdrop_path']}",
                "release_date": movie['release_date'],
                "vote_average": movie['vote_average'],
                "trailer_url": trailer,
                "cast_data": cast,
                "category_name": "أفلام أجنبية"
            }

            # حفظ أو تحديث البيانات في قاعدة البيانات
            supabase.table("movies").upsert(movie_data, on_conflict="tmdb_id").execute()
            print(f"تمت إضافة/تحديث: {movie['title']}")

if __name__ == "__main__":
    get_movies(pages=20) # هنا يمكنك تحديد عدد الصفحات (كل صفحة 20 فيلم)
