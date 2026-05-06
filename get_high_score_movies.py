"""
茶杯狐高评分电影爬虫（修正版）
从分类页面筛选评分>=9.0 的电影
URL 格式：https://cbh7.cc/vod/页码/39/0/0/0/0/0/0
详情页：https://cbh7.cc/v/1395861/39
"""
import requests
from bs4 import BeautifulSoup
import pymysql
import re
import time
import random

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'dailymove',
    'charset': 'utf8mb4'
}

# 基础 URL
BASE_URL = 'https://cbh7.cc'

def get_movie_list(page=1, min_score=9.0):
    """从分类页面获取电影列表"""
    # 正确的 URL 格式
    url = f"{BASE_URL}/vod/{page}/39/0/0/0/0/0/0"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    print(f"正在访问第 {page} 页：{url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        high_score_movies = []
        
        # 查找所有电影链接（格式：/v/数字/数字）
        links = soup.find_all('a', href=re.compile(r'/v/\d+/\d+'))
        
        print(f"  找到 {len(links)} 个电影链接")
        
        for link in links:
            href = link.get('href')
            title = link.get('title', link.get_text(strip=True))
            
            if not title or len(title) < 2:
                continue
            
            # 过滤冗余信息：更新至 HD/高清/HD 国语/HD 中字等不是电影名
            redundant_keywords = ['更新至', 'HD 国语', 'HD 中字', 'HD 英语', '高清', 'HD', '蓝光', '4K', '1080P', '720P', '预告片', '预告', 'TEASER', 'TRAILER']
            is_redundant = any(keyword in title.upper() for keyword in redundant_keywords)
            if is_redundant:
                continue
            
            # 清理标题中的冗余信息
            title = re.sub(r'\s*\(.*?\)', '', title)  # 移除括号内容
            title = re.sub(r'\s*【.*?】', '', title)  # 移除【】内容
            title = title.strip()
            
            if len(title) < 2:
                continue
            
            # 构建详情页 URL
            detail_url = href if href.startswith('http') else f"{BASE_URL}{href}"
            
            # 尝试从链接文本中提取评分（如果有）
            score_text = link.get_text(strip=True)
            score_match = re.search(r'(\d+\.?\d*)', score_text)
            score = float(score_match.group(1)) if score_match else 0.0
            
            # 如果链接中没有评分，需要访问详情页获取
            if score > 0 and score >= min_score:
                high_score_movies.append({
                    'title': title,
                    'score': score,
                    'detail_url': detail_url
                })
                print(f"  [找到] {title} - 评分：{score}")
            elif score == 0:
                # 先保存，稍后访问详情页获取评分
                high_score_movies.append({
                    'title': title,
                    'score': 0,  # 待获取
                    'detail_url': detail_url
                })
                print(f"  [待确认] {title}")
        
        print(f"第 {page} 页共找到 {len(high_score_movies)} 个候选\n")
        return high_score_movies
        
    except Exception as e:
        print(f"  [ERROR] 第 {page} 页访问失败：{e}")
        return []


def get_movie_detail(detail_url):
    """从详情页获取电影详细信息和评分"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    try:
        response = requests.get(detail_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        info = {
            'year': '2024',
            'tag': '剧情',
            'desc': '',
            'director': '未知',
            'actor': '未知',
            'video_url': detail_url,
            'score': 0.0,
        }
        
        # 查找评分
        score_elem = soup.find('span', class_='score text-red')
        if score_elem:
            score_text = score_elem.get_text(strip=True)
            score_match = re.search(r'(\d+\.?\d*)', score_text)
            if score_match:
                info['score'] = float(score_match.group(1))
                print(f"    [评分] {info['score']}")
        
        # 查找标题
        title_elem = soup.find('h1', class_='title')
        if title_elem:
            title = title_elem.get_text(strip=True)
            # 清理标题
            title = re.sub(r'\s*\(.*?\)', '', title)
            title = re.sub(r'\s*【.*?】', '', title)
            title = title.strip()
            print(f"    [标题] {title}")
        
        # 查找详情信息 - 从 p.desc 中查找
        desc_p = soup.find('p', class_='desc')
        if desc_p:
            desc_info = desc_p.find('span', class_='desc_info')
            if desc_info:
                info['desc'] = desc_info.get_text(strip=True)[:500]
        
        # 查找主演和导演 - 从 p.data cur_tit 中查找
        # 查找所有包含主演和导演的 p 标签
        p_tags = soup.find_all('p', class_='data')
        
        for p in p_tags:
            p_text = p.get_text()
            
            # 查找类型/标签
            if '类型' in p_text:
                # 尝试从 a 标签中提取类型
                a_tags = p.find_all('a')
                if a_tags:
                    tags = [a.get_text(strip=True) for a in a_tags if a.get_text(strip=True)]
                    if tags:
                        info['tag'] = '、'.join(tags)
                        print(f"    [类型] {info['tag']}")
            
            # 查找主演
            if '主演' in p_text:
                spans = p.find_all('span')
                actors = []
                for span in spans:
                    span_text = span.get_text(strip=True)
                    if span_text and span_text not in ['主演：', '主演:']:
                        actors.append(span_text)
                if actors:
                    info['actor'] = '、'.join(actors[:10])  # 最多保存 10 个主演
                    print(f"    [主演] {info['actor']}")
            
            # 查找导演
            if '导演' in p_text:
                spans = p.find_all('span')
                directors = []
                for span in spans:
                    span_text = span.get_text(strip=True)
                    if span_text and span_text not in ['导演：', '导演:']:
                        directors.append(span_text)
                if directors:
                    info['director'] = '、'.join(directors)
                    print(f"    [导演] {info['director']}")
        
        # 尝试从页面文本中提取年份
        all_text = soup.get_text()
        year_match = re.search(r'(19|20)\d{2}', all_text)
        if year_match:
            info['year'] = year_match.group(0)
        
        # 获取播放链接 - 从 div.play-btn 或 ul.myci-content__playlist
        play_div = soup.find('div', class_='play-btn')
        if play_div:
            play_link = play_div.find('a', href=True)
            if play_link:
                play_url = play_link.get('href')
                if play_url:
                    if not play_url.startswith('http'):
                        play_url = f"{BASE_URL}{play_url}"
                    info['video_url'] = play_url
                    print(f"    [播放链接] {play_url}")
        
        # 如果没有找到播放链接，尝试从播放列表找
        if info['video_url'] == detail_url:
            playlist = soup.find('ul', class_='myci-content__playlist')
            if playlist:
                first_link = playlist.find('a', href=True)
                if first_link:
                    play_url = first_link.get('href')
                    if play_url and not play_url.startswith('http'):
                        play_url = f"{BASE_URL}{play_url}"
                        info['video_url'] = play_url
        
        return info
        
    except Exception as e:
        print(f"    [ERROR] 获取详情失败：{e}")
        return {
            'year': '2024',
            'tag': '剧情',
            'desc': '',
            'director': '未知',
            'actor': '未知',
            'video_url': detail_url,
            'score': 7.0,
        }


def update_database(movies, clean_first=True, max_movies=20, min_score=9.0, max_score=10.0):
    """更新数据库"""
    print("\n" + "=" * 80)
    print("正在更新数据库...")
    print("=" * 80)
    
    connection = pymysql.connect(**DB_CONFIG)
    cursor = connection.cursor()
    
    try:
        # 清空旧数据
        if clean_first:
            print("\n⚠️  正在清空旧数据...")
            cursor.execute('DELETE FROM movies')
            start_id = 1
        else:
            cursor.execute('SELECT MAX(id) FROM movies')
            result = cursor.fetchone()
            start_id = (result[0] or 0) + 1
        
        # 过滤和添加数据
        valid_movies = []
        seen_urls = set()  # 用于去重
        print("\n正在获取电影详情和评分...")
        print(f"筛选条件：评分 {min_score}-{max_score}，最多保存 {max_movies} 部\n")
        
        for i, movie in enumerate(movies, 1):
            # 去重检查：检查 URL 是否已存在
            if movie['detail_url'] in seen_urls:
                print(f"  [跳过] {movie['title']} - URL 重复")
                continue
            seen_urls.add(movie['detail_url'])
            
            if movie['score'] == 0:  # 需要获取评分
                detail_info = get_movie_detail(movie['detail_url'])
                movie['score'] = detail_info['score']
                movie['detail'] = detail_info
                time.sleep(0.5)  # 避免请求太快
            
            # 严格验证评分在 9.0-10.0 之间
            if min_score <= movie['score'] <= max_score:
                valid_movies.append(movie)
                print(f"  [OK] {movie['title']} (评分：{movie['score']})")
                
                # 如果已经达到最大数量，停止
                if len(valid_movies) >= max_movies:
                    print(f"\n[INFO] 已达到最大保存数量（{max_movies} 部），停止筛选")
                    break
        
        print(f"\n筛选后剩余 {len(valid_movies)} 部评分在 {min_score}-{max_score} 之间的电影\n")
        
        # 插入数据库
        for i, movie in enumerate(valid_movies, start_id):
            detail_info = movie.get('detail', {})
            
            cursor.execute('''
                INSERT INTO movies 
                (id, title, year, tag, score, `desc`, bg, director, actor, video_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                i,
                movie['title'],
                detail_info.get('year', '2024'),
                detail_info.get('tag', '剧情'),
                movie['score'],
                detail_info.get('desc', f'高评分电影 #{i}'),
                f"https://picsum.photos/seed/movie{i}/1920/1080",
                detail_info.get('director', '未知'),
                detail_info.get('actor', '未知'),
                detail_info.get('video_url', movie['detail_url'])
            ))
        
        connection.commit()
        print(f"\n[OK] 成功添加 {len(valid_movies)} 部高评分电影！")
        
    except Exception as e:
        connection.rollback()
        print(f"\n[ERROR] 错误：{e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cursor.close()
        connection.close()


if __name__ == '__main__':
    print("=" * 80)
    print("茶杯狐高评分电影爬虫（评分 9.0-10.0）")
    print("=" * 80)
    print()
    
    all_movies = []
    
    # 扫描前 200 页（因为要严格筛选，所以多扫描一些）
    max_pages = 100
    min_score = 9.0
    max_score = 10.0
    max_movies = 20  # 最多保存 20 部
    
    print(f"计划扫描 {max_pages} 页，筛选评分 {min_score}-{max_score} 的电影")
    print(f"最多保存 {max_movies} 部电影\n")
    
    for page in range(1, max_pages + 1):
        movies = get_movie_list(page, min_score)
        all_movies.extend(movies)
        
        # 随机延迟
        time.sleep(random.uniform(1, 2))
        
        # 每 10 页休息一下
        if page % 10 == 0:
            print(f"\n[INFO] 已扫描 {page} 页，休息 5 秒...\n")
            time.sleep(5)
        
        # 如果候选电影已经足够多，可以提前停止
        if len(all_movies) >= max_movies * 3:
            print(f"\n[INFO] 已找到足够的候选电影（{len(all_movies)} 部），停止扫描\n")
            break
    
    print("\n" + "=" * 80)
    print(f"共找到 {len(all_movies)} 个候选电影（需要进一步筛选）")
    print("=" * 80)
    
    if all_movies:
        choice = input("\n是否更新到数据库？(y/n): ").strip().lower()
        if choice == 'y':
            update_database(all_movies, clean_first=True, max_movies=max_movies, min_score=min_score, max_score=max_score)
            
            print("\n" + "=" * 80)
            print("完成！")
            print("=" * 80)
            print("\n提示：")
            print("1. 刷新网页查看新电影")
            print("2. 访问 http://localhost:8000 查看效果")
        else:
            print("\n[INFO] 已取消更新")
    else:
        print("\n[ERROR] 未找到电影")
