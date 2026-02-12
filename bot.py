import os
import requests
from supabase import create_client, Client

# --- إعدادات الأمان (بيسحب المفاتيح من الخزنة السرية) ---
SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']
TMDB_API_KEY = os.environ['TMDB_API_KEY']

# الاتصال بقاعدة البيانات
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_trailer(movie_id):
    """وظيفة لجلب رابط تريلر الفيلم من يوتيوب"""
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={TMDB_API_KEY}"
        response = requests.get(url).json()
        for video in response.get('results', []):
            # بندور على فيديو نوعه Trailer ومن يوتيوب
            if video['site'] == 'YouTube' and video['type'] == 'Trailer':
                return f"https://www.youtube.com/embed/{video['key']}"
    except:
        return "" # لو حصل خطأ رجع مكان فاضي
    return ""

def add_trending_movies():
    print("🚀 الروبوت بدأ العمل لجلب أحدث الأفلام...")
    
    # 1. الاتصال بـ TMDB لجلب الأفلام المشهورة حالياً (Popular)
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=ar-SA&page=1"
    response = requests.get(url).json()
    movies = response.get('results', [])

    count = 0
    for movie in movies:
        try:
            # 2. تجهيز بيانات الفيلم (الاسم، السنة، الصورة، التريلر)
            data = {
                "title_ar": movie['title'],
                "title_en": movie['original_title'],
                # بنحاول نجيب السنة من التاريخ، لو مفيش بنحط 2024
                "year": int(movie['release_date'].split('-')[0]) if movie.get('release_date') else 2024,
                "imdb_rating": movie['vote_average'],
                "poster_url": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}",
                "video_url": get_trailer(movie['id']),
                "quality": "1080p" # جودة افتراضية
            }

            # 3. محاولة إضافة الفيلم لقاعدة البيانات
            # (لو الفيلم موجود قبل كدة، قاعدة البيانات هترفض الإضافة، وده اللي إحنا عايزينه)
            supabase.table('movies').insert(data).execute()
            print(f"✅ تمت إضافة فيلم جديد: {movie['title']}")
            count += 1
            
        except Exception as e:
            # لو حصل خطأ (غالباً عشان الفيلم متكرر)، الروبوت هيكمل عادي
            print(f"⚠️ تخطي (الفيلم موجود أو حدث خطأ): {movie['title']}")

    print(f"\n🎉 المهمة انتهت! تمت إضافة {count} فيلم جديد للموقع.")

if __name__ == "__main__":
    add_trending_movies()
