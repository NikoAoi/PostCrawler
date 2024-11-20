import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import datetime
import random
import time
import json
import sys
import threading
import subprocess
from multiprocessing import Value

def extract_links(url):
    """
    Extract links from book-post class elements on the given URL
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        book_posts = soup.select('div.book-post li > a')
        
        links = []
        for link in book_posts:
            href = link.get('href')
            absolute_url = urljoin(url, href)
            text = link.get_text().strip()
            links.append((absolute_url, text))
            
        return links
            
    except requests.RequestException as e:
        return []
    except Exception as e:
        return []

def spinner_animation(stop_event, message):
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f'\r{spinner[i % len(spinner)]} {message}')
        sys.stdout.flush()
        i += 1
        time.sleep(0.1)

def download_html(url, output_file):
    """
    使用single-file下载HTML页面
    """
    try:
        subprocess.run(['single-file', url, output_file, '--browser-headless', 'false', '--browser-start-minimized'], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def process_links(initial_url, posts_limit=None, links_limit=None):
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    base_dir = f"posts_{timestamp}"
    os.makedirs(base_dir, exist_ok=True)
    
    # 创建停止事件和动画线程用于信息搜集阶段
    collecting_stop_event = threading.Event()
    collecting_thread = threading.Thread(
        target=spinner_animation,
        args=(collecting_stop_event, "正在搜集必要信息...")
    )
    collecting_thread.daemon = True
    collecting_thread.start()
    
    initial_links = extract_links(initial_url)
    
    if posts_limit is not None:
        initial_links = initial_links[:posts_limit]
    
    total_links = len(initial_links)
    
    # 停止信息搜集动画并显示完成图标
    collecting_stop_event.set()
    collecting_thread.join()
    sys.stdout.write('\r' + ' ' * 50)  # 用空格覆盖上一行输出
    sys.stdout.write('\r✓ 信息搜集完毕\n')
    sys.stdout.flush()
    
    success_count = 0
    failed_count = 0
    
    for idx, (url, text) in enumerate(initial_links, 1):
        # 为每个initial_link创建子目录
        safe_dirname = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).rstrip()
        sub_dir = os.path.join(base_dir, f"{idx:03d}_{safe_dirname}")
        os.makedirs(sub_dir, exist_ok=True)
        
        sub_links = extract_links(url)
        downloaded_count = 0  # 记录当前批次已下载的数量
        
        # 计算当前任务需要下载的总页面数
        total_pages = min(len(sub_links), links_limit) if links_limit else len(sub_links)
        
        # 创建当前任务的动画线程
        task_stop_event = threading.Event()
        task_thread = threading.Thread(
            target=spinner_animation,
            args=(task_stop_event, f"正在执行第 {idx} 个导出任务，共有 {total_pages} 个页面需要导出，当前已导出 {downloaded_count} 个")
        )
        task_thread.daemon = True
        task_thread.start()
        
        for sub_url, sub_text in sub_links:
            if links_limit and downloaded_count >= links_limit:
                break
                
            try:
                # 创建安全的文件名
                safe_filename = "".join(c for c in sub_text if c.isalnum() or c in (' ', '-', '_')).rstrip()
                output_file = os.path.join(sub_dir, f"{safe_filename}.html")
                
                if download_html(sub_url, output_file):
                    success_count += 1
                else:
                    failed_count += 1
                    
                downloaded_count += 1
                
                # 更新进度消息
                task_stop_event.set()
                task_thread.join()
                task_stop_event = threading.Event()
                task_thread = threading.Thread(
                    target=spinner_animation,
                    args=(task_stop_event, f"正在执行第 {idx} 个导出任务，共有 {total_pages} 个页面需要导出，当前已导出 {downloaded_count} 个")
                )
                task_thread.daemon = True
                task_thread.start()
                
            except:
                failed_count += 1
            
            delay = random.uniform(0.1, 0.3)
            time.sleep(delay)
        
        # 停止当前任务的动画线程
        task_stop_event.set()
        task_thread.join()
        
        # 清除当前行并显示完成消息
        sys.stdout.write('\r' + ' ' * 100)  # 用足够多的空格清除当前行
        sys.stdout.write(f'\r✓ 第 {idx} 个导出任务已完成\n')
        sys.stdout.flush()
    
    # 显示最终导出结果
    sys.stdout.write(f'\r✓ 所有导出任务完成，成功导出 {success_count} 个页面, 失败 {failed_count} 个\n')
    sys.stdout.flush()

def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="要爬取的网站URL")
    parser.add_argument("--posts_limit", type=int, help="要爬取的文章数量限制", default=None)
    parser.add_argument("--links_limit", type=int, help="要爬取的链接数量限制", default=None)
    
    args = parser.parse_args()
    
    process_links(args.url, args.posts_limit, args.links_limit)

if __name__ == "__main__":
    main()