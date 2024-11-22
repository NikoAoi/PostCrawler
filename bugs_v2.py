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
import logging
import signal
from functools import partial
from collections import deque

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
        logging.error(f"请求错误: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"未知错误: {str(e)}")
        return []

def spinner_animation(stop_event, message):
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f'\r{spinner[i % len(spinner)]} {message}')
        sys.stdout.flush()
        i += 1
        time.sleep(0.1)

def download_html(url, output_file, timeout=30):
    """
    使用single-file下载HTML页面,设置超时时间
    """
    # 检查文件是否已存在
    if os.path.exists(output_file):
        logging.info(f"文件已存在,跳过下载: {output_file}")
        return True
        
    try:
        process = subprocess.Popen(['single-file', url, output_file, '--browser-headless', 'false', '--browser-start-minimized'])
        
        # 等待进程完成,使用传入的超时时间
        try:
            process.wait(timeout=timeout)
            if process.returncode == 0:
                logging.info(f"成功下载页面: {url} -> {output_file}")
                return True
            else:
                # 下载失败时检查并清理可能存在的文件
                if os.path.exists(output_file):
                    os.remove(output_file)
                    logging.info(f"清理下载失败的文件: {output_file}")
                logging.error(f"下载页面失败: {url}, 返回码: {process.returncode}")
                return False
        except subprocess.TimeoutExpired:
            # 超时后终止进程
            process.kill()
            # 检查并清理可能存在的文件
            if os.path.exists(output_file):
                os.remove(output_file)
                logging.info(f"清理超时下载的文件: {output_file}")
            timeout_msg = f"下载页面超时({timeout}s): {url}"
            logging.error(timeout_msg)
            print(f"\r{timeout_msg}")  # 打印到控制台
            return False
            
    except subprocess.CalledProcessError as e:
        # 检查并清理可能存在的文件
        if os.path.exists(output_file):
            os.remove(output_file)
            logging.info(f"清理错误下载的文件: {output_file}")
        logging.error(f"下载页面失败: {url}, 错误信息: {str(e)}")
        return False
    except Exception as e:
        # 检查并清理可能存在的文件
        if os.path.exists(output_file):
            os.remove(output_file)
            logging.info(f"清理异常下载的文件: {output_file}")
        logging.error(f"下载页面时发生未知错误: {url}, 错误信息: {str(e)}")
        return False

def process_links(initial_url, posts_limit=None, links_limit=None, timeout=30, output_dir=None):
    # 检查输出目录
    if output_dir:
        if not os.path.exists(output_dir):
            print(f"错误: 指定的输出目录 '{output_dir}' 不存在")
            sys.exit(1)
        base_dir = output_dir
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        base_dir = f"posts_{timestamp}"
        
    os.makedirs(base_dir, exist_ok=True)
    
    # 设置日志
    log_file = os.path.join(base_dir, 'crawler.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    
    # 创建失败队列
    failed_queue = deque()
    
    logging.info(f"开始爬取任务，初始URL: {initial_url}")
    
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
        logging.info(f"设置文章数量限制为: {posts_limit}")
    
    total_links = len(initial_links)
    logging.info(f"共找到 {total_links} 个导出任务")
    
    # 停止信息搜集动画并显示完成图标
    collecting_stop_event.set()
    collecting_thread.join()
    sys.stdout.write('\r' + ' ' * 50)  # 用空格覆盖上一行输出
    sys.stdout.write(f'\r✓ 信息搜集完毕，共有{total_links}个导出任务需要执行\n')
    sys.stdout.flush()
    
    success_count = 0
    failed_count = 0
    
    for idx, (url, text) in enumerate(initial_links, 1):
        # 为每个initial_link创建子目录
        safe_dirname = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).rstrip()
        sub_dir = os.path.join(base_dir, f"{idx:03d}_{safe_dirname}")
        
        # 检查子目录是否存在,不存在才创建
        if not os.path.exists(sub_dir):
            os.makedirs(sub_dir)
            logging.info(f"创建子目录: {sub_dir}")
        else:
            logging.info(f"子目录已存在: {sub_dir}")
        
        logging.info(f"开始处理第 {idx} 个任务: {text}")
        
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
                logging.info(f"已达到链接限制 {links_limit}，停止当前任务")
                break
                
            try:
                # 创建安全的文件名
                safe_filename = "".join(c for c in sub_text if c.isalnum() or c in (' ', '-', '_')).rstrip()
                output_file = os.path.join(sub_dir, f"{safe_filename}.html")
                
                if download_html(sub_url, output_file, timeout):
                    success_count += 1
                else:
                    failed_count += 1
                    # 将失败的下载任务添加到失败队列
                    failed_queue.append((sub_url, output_file, sub_text))
                    
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
                
            except Exception as e:
                failed_count += 1
                logging.error(f"处理页面时发生错误: {str(e)}")
                # 检查并清理可能存在的文件
                if os.path.exists(output_file):
                    os.remove(output_file)
                    logging.info(f"清理异常处理的文件: {output_file}")
                # 将失败的下载任务添加到失败队列
                failed_queue.append((sub_url, output_file, sub_text))
            
            delay = random.uniform(0.1, 0.3)
            time.sleep(delay)
        
        # 停止当前任务的动画线程
        task_stop_event.set()
        task_thread.join()
        
        # 清除当前行并显示完成消息
        sys.stdout.write('\r' + ' ' * 100)  # 用足够多的空格清除当前行
        sys.stdout.write(f'\r✓ 第 {idx} 个导出任务已完成\n')
        sys.stdout.flush()
        logging.info(f"完成第 {idx} 个导出任务")
    
    # 处理失败队列中的任务
    if failed_queue:
        print("\n开始重试失败的下载任务...")
        logging.info(f"开始重试 {len(failed_queue)} 个失败的下载任务")
        retry_failed = 0
        retry_success = 0
        
        while failed_queue:
            sub_url, output_file, sub_text = failed_queue.popleft()
            print(f"\r正在重试下载: {sub_text}")
            
            if download_html(sub_url, output_file, timeout):
                retry_success += 1
                success_count += 1
                failed_count -= 1
                logging.info(f"重试成功: {sub_text}")
            else:
                retry_failed += 1
                logging.error(f"重试失败: {sub_text}")
                print(f"重试失败: {sub_text}")
            
            time.sleep(random.uniform(0.1, 0.3))
        
        print(f"\n重试完成: 成功 {retry_success} 个, 失败 {retry_failed} 个")
        logging.info(f"重试完成: 成功 {retry_success} 个, 失败 {retry_failed} 个")
    
    # 显示最终导出结果
    final_message = f"所有导出任务完成，成功导出 {success_count} 个页面, 失败 {failed_count} 个"
    sys.stdout.write(f'\r✓ {final_message}\n')
    sys.stdout.flush()
    logging.info(final_message)

def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="要爬取的网站URL")
    parser.add_argument("--posts_limit", type=int, help="要爬取的文章数量限制", default=None)
    parser.add_argument("--links_limit", type=int, help="要爬取的链接数量限制", default=None)
    parser.add_argument("--timeout", type=int, help="下载页面的超时时间(秒)", default=30)
    parser.add_argument("--output_dir", help="指定下载文件的保存目录", default=None)
    
    args = parser.parse_args()
    
    process_links(args.url, args.posts_limit, args.links_limit, args.timeout, args.output_dir)

if __name__ == "__main__":
    main()