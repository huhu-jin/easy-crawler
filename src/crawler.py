"""爬虫服务模块"""
import re
import tempfile
import os
from datetime import datetime
import time
from typing import List, Optional, Tuple
from urllib.parse import urljoin
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from bs4 import BeautifulSoup
import html2text
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


class CrawlerService:
    """网页爬虫服务"""
    
    def __init__(self):
        """初始化爬虫服务"""
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.body_width = 0  # 不自动换行
    
    def is_today(self, date_text: str, target_date=None) -> bool:
        """
        判断日期文本是否匹配目标日期
        
        Args:
            date_text: 日期文本
            target_date: 目标日期（date 对象），不传则使用今天
        
        Returns:
            是否匹配
        """
        today = target_date if target_date is not None else datetime.now().date()
        
        # 英文月份名称映射
        month_names = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        def parse_ymd(m):
            return int(m.group(1)), int(m.group(2)), int(m.group(3))
        
        def parse_mdy(m):
            return int(m.group(3)), int(m.group(1)), int(m.group(2))
        
        def parse_en(m):
            return int(m.group(3)), month_names[m.group(1).lower()], int(m.group(2))
        
        # (正则, 解析函数, re.flags)
        date_patterns = [
            (r'(\d{4})-(\d{1,2})-(\d{1,2})', parse_ymd, 0),                         # 2026-02-16
            (r'(\d{4})/(\d{1,2})/(\d{1,2})', parse_ymd, 0),                         # 2026/02/16
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', parse_mdy, 0),                         # 02/16/2026
            (r'(\d{4})年(\d{1,2})月(\d{1,2})日', parse_ymd, 0),                       # 2026年02月16日
            (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', parse_en, re.IGNORECASE),  # January 14, 2026
        ]
        
        for pattern, parser, flags in date_patterns:
            match = re.search(pattern, date_text, flags)
            if match:
                try:
                    year, month, day = parser(match)
                    date_obj = datetime(year, month, day).date()
                    return date_obj == today
                except (ValueError, KeyError):
                    continue
        
        # 检查相对日期（仅当 target_date 为今天时生效）
        if today == datetime.now().date():
            if 'today' in date_text.lower() or '今天' in date_text or '今日' in date_text:
                return True
        
        return False
    
    def extract_links_from_list(self, html_content: str, list_selector: str = None,
                                list_date_selector: str = None,
                                target_date=None) -> List[Tuple[str, str]]:
        """
        从 HTML 中提取 ul > li 结构中的链接
        
        Args:
            html_content: HTML 内容
            list_selector: CSS 选择器，用于定位列表区域，默认为所有 ul
            list_date_selector: CSS 选择器，用于在 li 内定位日期元素；不传则取整个 li 文本
            target_date: 目标日期（date 对象），不传则使用今天
        
        Returns:
            (链接URL, 链接文本) 的列表
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        # 根据选择器查找列表区域
        if list_selector:
            containers = soup.select(list_selector)
        else:
            containers = soup.find_all('ul')
        
        for container in containers:
            # 如果选择器选中的不是 ul，在其中查找 ul
            if container.name == 'ul':
                uls = [container]
            else:
                uls = container.find_all('ul')
                if not uls:
                    # 容器本身可能直接包含 li
                    uls = [container]
            
            for ul in uls:
                for li in ul.find_all('li'):
                    # 获取用于日期判断的文本
                    if list_date_selector:
                        date_el = li.select_one(list_date_selector)
                        date_text = date_el.get_text() if date_el else ''
                    else:
                        date_text = li.get_text()

                    if not self.is_today(date_text, target_date):
                        continue
                    
                    # 提取链接
                    link = li.find('a')
                    if link and link.get('href'):
                        url = link.get('href')
                        text = link.get_text(strip=True)
                        links.append((url, text))
        
        return links
    
    def crawl_page(self, url, timeout=30000):
        """
        使用 Playwright 爬取页面内容
        
        Args:
            url: 目标 URL
            timeout: 超时时间（毫秒）
        
        Returns:
            页面 HTML 内容，失败返回 None
        """
        target_url = str(url)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                context.set_default_navigation_timeout(timeout)
                context.set_default_timeout(timeout)
                page = context.new_page()
                page.goto(target_url)
                
                # 等待页面加载
                page.wait_for_load_state('networkidle')
                
                # 获取页面内容
                content = page.content()
                browser.close()
                
                return content
        except PlaywrightTimeoutError:
            print(f"页面加载超时: {url}")
            return None
        except Exception as e:
            print(f"爬取页面失败 {url}: {e}")
            return None
    
    def convert_to_markdown(self, html_content: str, content_selector: str = None) -> str:
        """
        将 HTML 转换为 Markdown
        
        Args:
            html_content: HTML 内容
            content_selector: CSS 选择器，用于定位正文区域，默认为整个页面
        
        Returns:
            Markdown 内容
        """
        if content_selector:
            soup = BeautifulSoup(html_content, 'html.parser')
            content_elements = soup.select(content_selector)
            if content_elements:
                # 拼接所有匹配元素的 HTML
                html_content = '\n'.join(str(el) for el in content_elements)
        
        return self.html_converter.handle(html_content)
    
    def extract_title(self, html_content: str) -> str:
        """
        从 HTML 中提取标题
        
        Args:
            html_content: HTML 内容
        
        Returns:
            页面标题
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 尝试获取 title 标签
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        # 尝试获取 h1 标签
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text(strip=True)
        
        return "未命名页面"
    
    def download_and_convert_pdf(self, pdf_url: str) -> Optional[str]:
        """
        下载 PDF 并转换为 Markdown

        Args:
            pdf_url: PDF 文件的完整 URL

        Returns:
            Markdown 字符串，失败时返回 None
        """
        import pymupdf4llm

        print(f"  正在下载 PDF: {pdf_url}")
        try:
            resp = requests.get(pdf_url, timeout=60, verify=False, allow_redirects=True)
            resp.raise_for_status()
            final_url = resp.url
            if final_url != pdf_url:
                print(f"  重定向到: {final_url}")
        except Exception as e:
            print(f"  PDF 下载失败: {e}")
            return None

        # 写入临时文件
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        try:
            with os.fdopen(tmp_fd, 'wb') as f:
                f.write(resp.content)
            markdown = pymupdf4llm.to_markdown(tmp_path)
            print(f"  PDF 转换完成，共 {len(markdown)} 字符")
            return markdown
        except Exception as e:
            print(f"  PDF 转换失败: {e}")
            return None
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def check_and_crawl(self, url: str, desc: str, list_selector: str = None,
                        content_selector: str = None,
                        pdf_selector: str = None,
                        list_date_selector: str = None,
                        target_date=None):
        """
        检查 URL 并爬取今天更新的内容（生成器，每爬完一个即 yield）

        Args:
            url: 列表页 URL
            desc: 描述
            list_selector: CSS 选择器，用于定位列表区域
            content_selector: CSS 选择器，用于定位详情页正文区域
            pdf_selector: CSS 选择器，用于定位详情页中的 PDF 链接
            list_date_selector: CSS 选择器，用于定位列表项中的日期元素
            target_date: 目标日期（date 对象），不传则使用今天

        Yields:
            (标题, Markdown内容, 原始URL) 元组
        """
        print(f"正在检查: {desc} - {url}")
        if list_selector:
            print(f"  列表选择器: {list_selector}")
        if list_date_selector:
            print(f"  日期选择器: {list_date_selector}")
        if content_selector:
            print(f"  内容选择器: {content_selector}")
        if pdf_selector:
            print(f"  PDF 选择器: {pdf_selector}")

        if target_date:
            print(f"  目标日期: {target_date}")

        # 爬取列表页
        list_html = self.crawl_page(url)
        if not list_html:
            print(f"无法获取列表页: {url}")
            return

        # 提取今天的链接
        links = self.extract_links_from_list(list_html, list_selector, list_date_selector, target_date)
        if not links:
            print(f"未找到今天的更新: {url}")
            return

        print(f"找到 {len(links)} 个今天的更新")

        for link_url, link_text in links:
            time.sleep(5)  # sleep 5 seconds
            # 处理相对路径
            if link_url.startswith('/'):
                link_url = urljoin(url, link_url)

            print(f"正在爬取: {link_text} - {link_url}")

            # 爬取详情页
            detail_html = self.crawl_page(link_url)
            if not detail_html:
                print(f"无法获取详情页: {link_url}")
                continue

            markdown = None

            # 若配置了 pdf_selector，尝试提取 PDF 链接并转换
            if pdf_selector:
                soup = BeautifulSoup(detail_html, 'html.parser')
                pdf_el = soup.select_one(pdf_selector)
                if pdf_el and pdf_el.get('href'):
                    pdf_href = pdf_el['href']
                    pdf_url_full = pdf_href if pdf_href.startswith('http') else urljoin(link_url, pdf_href)
                    print(f"  检测到 PDF 链接: {pdf_url_full}")
                    markdown = self.download_and_convert_pdf(pdf_url_full)
                    if markdown:
                        print(f"  使用 PDF 内容")
                    else:
                        print(f"  PDF 处理失败，回退到 HTML 内容")

            # 无 PDF 或 PDF 处理失败时，转换 HTML
            if markdown is None:
                markdown = self.convert_to_markdown(detail_html, content_selector)

            yield link_text, markdown, link_url
