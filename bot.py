import os
import requests
from supabase import create_client, Client

# --- إعدادات الاتصال ---
SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']
TMDB_API_KEY = os.environ['TMDB_API_KEY']

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_trailer(movie_id):
    """جلب التريلر"""
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={TMDB_API_KEY}"
        response = requests.get(url).json()
        for video in response.get('results', []):
            if video['site'] == 'YouTube' and video['type'] == 'Trailer':
                return f"https://www.youtube.com/embed/{video['key']}"
    except:
        return ""
    return ""

def fix_broken_movies():
    """🩺 وظيفة الطبيب: البحث عن الأفلام المعطلة وإصلاحها"""
    print("\n🩺 جاري فحص الموقع بحثاً عن صور مفقودة أو بيانات ناقصة...")
    
    # 1. هات كل الأفلام اللي معندهاش صورة أو الرابط بتاعها قصير زيادة
    # (Supabase مش بتدعم فلترة معقدة أوي هنا، فبنجيب الكل ونفلتر بالكود)
    response = supabase.table('movies').select("*").execute()
    
    fixed_count = 0
    for movie in response.data:
        # الشرط: لو حقل الصورة فاضي أو مفيش فيه رابط حقيقي
        if not movie['poster_url'] or len(movie['poster_url']) < 10:
            print(f"⚠️ تم اكتشاف فيلم معطوب: {movie['title_en']} - جاري الإصلاح...")
            
            # البحث عنه في TMDB
            search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie['title_en']}"
            search_res = requests.get(search_url).json()
            
            if search_res.get('results'):
                fresh_data = search_res['results'][0] # خد أول نتيجة
                
                # تحديث البيانات في قاعدة البيانات
                update_data = {
                    "poster_url": f"https://image.tmdb.org/t/p/w500{fresh_data['poster_path']}",
                    "imdb_rating": fresh_data['vote_average'],
                    "year": int(fresh_data['release_date'].split('-')[0]) if fresh_data.get('release_date') else 2024,
                    "video_url": get_trailer(fresh_data['id']) or movie['video_url'] # حدث التريلر كمان لو لقينا جديد
                }
                
                supabase.table('movies').update(update_data).eq('id', movie['id']).execute()
                print(f"✅ تم إصلاح: {movie['title_en']}")
                fixed_count += 1
            else:
                print(f"❌ فشل العثور على بيانات لـ: {movie['title_en']}")

    if fixed_count == 0:
        print("✨ النظام سليم! لا توجد أفلام تحتاج لإصلاح.")
    else:
        print(f"🔧 تمت عملية الصيانة: تم إصلاح {fixed_count} فيلم.")

def add_trending_movies():
    """🚀 وظيفة الجلب: إضافة الجديد"""
    print("🚀 بدء جلب أحدث الأفلام...")
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=ar-SA&page=1"
    response = requests.get(url).json()
    movies = response.get('results', [])

    count = 0
    for movie in movies:
        try:
            data = {
                "title_ar": movie['title'],
                "title_en": movie['original_title'],
                "year": int(movie['release_date'].split('-')[0]) if movie.get('release_date') else 2024,
                "imdb_rating": movie['vote_average'],
                "poster_url": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}",
                "video_url": get_trailer(movie['id']),
                "quality": "1080p"
            }
            supabase.table('movies').insert(data).execute()
            print(f"✅ تمت إضافة: {movie['title']}")
            count += 1
        except Exception:
            pass # تخطي التكرار بصمت

    print(f"🎉 تمت إضافة {count} فيلم جديد.")

if __name__ == "__main__":
    # تشغيل الإضافة أولاً
    add_trending_movies()
    # ثم تشغيل الصيانة
    fix_broken_movies()
