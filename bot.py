import os
import requests
import time
from supabase import create_client, Client

# --- إعدادات الاتصال ---
SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']
TMDB_API_KEY = os.environ['TMDB_API_KEY']

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_best_trailer(movie_id):
    """يجيب أجدد تريلر رسمي من TMDB"""
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={TMDB_API_KEY}"
        response = requests.get(url, timeout=5).json()
        results = response.get('results', [])
        
        # الأولوية للتريلر الرسمي من يوتيوب
        for video in results:
            if video['site'] == 'YouTube' and video['type'] == 'Trailer' and video['official']:
                return f"https://www.youtube.com/embed/{video['key']}"
        
        # لو مفيش رسمي، خد أي تريلر
        for video in results:
            if video['site'] == 'YouTube' and video['type'] == 'Trailer':
                return f"https://www.youtube.com/embed/{video['key']}"
    except:
        pass
    return ""

def refresh_all_movies():
    """🔄 التحديث الشامل: يمر على كل الأفلام ويجدد بياناتها"""
    print("\n🔄 جاري تحديث بيانات جميع الأفلام (التقييمات، التريلرات، الصور)...")
    
    # نجيب كل الأفلام اللي في الموقع
    # (ملاحظة: Supabase بتجيب 1000 صف كحد أقصى في الطلب الواحد، وده كافي للبداية)
    response = supabase.table('movies').select("*").execute()
    movies_list = response.data
    
    updated_count = 0
    
    for movie in movies_list:
        try:
            # نبحث عن الفيلم في TMDB بالاسم الإنجليزي عشان نجيب أحدث بيانات
            search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie['title_en']}"
            search_res = requests.get(search_url, timeout=5).json()
            
            if search_res.get('results'):
                fresh_data = search_res['results'][0]
                
                # نجهز البيانات الجديدة
                new_rating = fresh_data.get('vote_average', 0)
                new_poster = f"https://image.tmdb.org/t/p/w500{fresh_data.get('poster_path')}"
                new_trailer = get_best_trailer(fresh_data['id'])
                
                # تحديث قاعدة البيانات (Update)
                update_data = {
                    "imdb_rating": new_rating, # تحديث التقييم
                    "poster_url": new_poster,  # تحديث الصورة
                }
                
                # نحدث التريلر فقط لو لقينا واحد جديد، عشان منمسحش القديم لو شغال
                if new_trailer:
                    update_data["video_url"] = new_trailer

                supabase.table('movies').update(update_data).eq('id', movie['id']).execute()
                print(f"✨ تم تجديد: {movie['title_en']} (⭐ {new_rating})")
                updated_count += 1
                
        except Exception as e:
            print(f"⚠️ تخطي {movie.get('title_en', 'Unknown')}: {e}")
            
    print(f"✅ تمت عملية التحديث الشامل لـ {updated_count} فيلم.")

def add_trending_movies():
    """🚀 إضافة الأفلام الجديدة (التريند)"""
    print("\n🚀 جاري البحث عن أفلام جديدة للإضافة...")
    try:
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
                    "video_url": get_best_trailer(movie['id']),
                    "quality": "1080p"
                }
                supabase.table('movies').insert(data).execute()
                print(f"🆕 تم إضافة: {movie['title']}")
                count += 1
            except:
                pass 
        print(f"🎉 تمت إضافة {count} فيلم جديد.")
    except Exception as e:
        print(f"❌ خطأ في الإضافة: {e}")

if __name__ == "__main__":
    # 1. نضيف الجديد الأول
    add_trending_movies()
    
    # 2. نحدث القديم كله
    refresh_all_movies()
