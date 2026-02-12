import requests
from supabase import create_client
import os
import time

# إعدادات الاتصال
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# دالة تنظيف النصوص للروابط
def create_slug(title, id):
    clean = "".join(c if c.isalnum() or c.isspace() else "" for c in title)
    return f"{clean.replace(' ', '-').lower()}-{id}"

# 1. محرك الأفلام
def process_movie(tmdb_id):
    print(f"🎬 معالجة الفيلم: {tmdb_id}")
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}&language=ar-SA&append_to_response=credits,videos"
    data = requests.get(url).json()
    
    # إدخال الفيلم
    movie_data = {
        "tmdb_id": data['id'],
        "slug": create_slug(data['title'], data['id']),
        "title": data['title'],
        "overview": data.get('overview'),
        "poster_path": f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else None,
        "backdrop_path": f"https://image.tmdb.org/t/p/original{data.get('backdrop_path')}" if data.get('backdrop_path') else None,
        "release_date": data.get('release_date'),
        "vote_average": data.get('vote_average')
    }
    res = supabase.table("movies").upsert(movie_data, on_conflict="tmdb_id").execute()
    
    if res.data:
        m_id = res.data[0]['id']
        
        # إضافة السيرفر (تلقائي)
        trailer = next((v['key'] for v in data.get('videos', {}).get('results', []) if v['site'] == 'YouTube'), None)
        if trailer:
            supabase.table("servers").insert({
                "movie_id": m_id,
                "server_name": "Fast Server",
                "quality": "1080p",
                "embed_url": f"https://www.youtube.com/embed/{trailer}",
                "type": "movie"
            }).execute()

        # إضافة الممثلين (Loop)
        for cast in data.get('credits', {}).get('cast', [])[:5]:
            # 1. ضيف الممثل في جدول People
            p_res = supabase.table("people").upsert({
                "tmdb_id": cast['id'],
                "name": cast['name'],
                "profile_path": f"https://image.tmdb.org/t/p/w200{cast.get('profile_path')}" if cast.get('profile_path') else None
            }, on_conflict="tmdb_id").execute()
            
            # 2. اربطه بالفيلم في جدول cast_crew
            if p_res.data:
                supabase.table("cast_crew").insert({
                    "movie_id": m_id,
                    "person_id": p_res.data[0]['id'],
                    "character_name": cast['character'],
                    "job": "Actor"
                }).execute()

# 2. محرك المسلسلات (المعقد)
def process_series(tmdb_id):
    print(f"📺 معالجة المسلسل: {tmdb_id}")
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_API_KEY}&language=ar-SA"
    data = requests.get(url).json()
    
    series_data = {
        "tmdb_id": data['id'],
        "slug": create_slug(data['name'], data['id']),
        "title": data['name'],
        "overview": data.get('overview'),
        "poster_path": f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else None,
        "backdrop_path": f"https://image.tmdb.org/t/p/original{data.get('backdrop_path')}" if data.get('backdrop_path') else None,
        "vote_average": data.get('vote_average')
    }
    res = supabase.table("series").upsert(series_data, on_conflict="tmdb_id").execute()
    
    if res.data:
        s_uuid = res.data[0]['id']
        # جلب المواسم
        for season in data.get('seasons', []):
            if season['season_number'] == 0: continue
            
            sn_res = supabase.table("seasons").insert({
                "series_id": s_uuid,
                "season_number": season['season_number'],
                "name": season['name'],
                "episode_count": season['episode_count']
            }).execute()
            
            if sn_res.data:
                season_uuid = sn_res.data[0]['id']
                # جلب الحلقات
                ep_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season['season_number']}?api_key={TMDB_API_KEY}&language=ar-SA"
                ep_data = requests.get(ep_url).json()
                
                episodes = []
                for ep in ep_data.get('episodes', []):
                    episodes.append({
                        "series_id": s_uuid,
                        "season_id": season_uuid,
                        "episode_number": ep['episode_number'],
                        "name": ep['name'],
                        "overview": ep.get('overview'),
                        "still_path": f"https://image.tmdb.org/t/p/original{ep.get('still_path')}" if ep.get('still_path') else None
                    })
                if episodes:
                    supabase.table("episodes").insert(episodes).execute()

# التشغيل الرئيسي
def run():
    # جلب التريند
    trend = requests.get(f"https://api.themoviedb.org/3/trending/all/day?api_key={TMDB_API_KEY}&language=ar-SA").json()
    for item in trend['results']:
        try:
            if item['media_type'] == 'movie':
                process_movie(item['id'])
            elif item['media_type'] == 'tv':
                process_series(item['id'])
        except Exception as e:
            print(f"Error: {e}")
            
if __name__ == "__main__":
    run()
