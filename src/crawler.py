"""爬虫服务模块"""
import json
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

        self.proxy_auth_key = os.getenv("CRAWLER_PROXY_AUTH_KEY", "520PGXI4").strip()
        self.proxy_password = os.getenv("CRAWLER_PROXY_PASSWORD", "10007E6BFDE183B").strip()
        self.proxy_fetch_url = f"https://share.proxy.qg.net/get?key={self.proxy_auth_key}&num=1"

    def _extract_proxy_addr(self, raw_text: str) -> Optional[str]:
        """从接口返回文本中提取 host:port 或协议代理地址"""
        if not raw_text:
            return None

        # 优先解析 JSON 响应，提取 data[0].server
        try:
            payload = json.loads(raw_text)
            if isinstance(payload, dict):
                data = payload.get("data")
                if isinstance(data, list) and data:
                    first_item = data[0]
                    if isinstance(first_item, dict):
                        server = str(first_item.get("server", "")).strip()
                        if server:
                            return server
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        # 常见返回：纯文本 "ip:port" 或多行内容，取第一个代理格式片段
        match = re.search(r'((?:https?|socks5)://[^\s]+|\d{1,3}(?:\.\d{1,3}){3}:\d{2,5})', raw_text)
        if not match:
            return None
        return match.group(1).strip()

    def _fetch_proxy_addr(self) -> Optional[str]:
        """每次调用实时获取代理地址"""
        if not self.proxy_fetch_url:
            return None
        try:
            resp = requests.get(self.proxy_fetch_url, timeout=10, verify=False)
            resp.raise_for_status()
            addr = self._extract_proxy_addr(resp.text)
            if not addr:
                print(f"代理接口返回无法解析: {resp.text[:120]}")
                return None
            return addr
        except Exception as e:
            print(f"获取动态代理失败: {e}")
            return None

    def _build_proxy_settings(self) -> Optional[dict]:
        """
        构建代理配置（支持动态提取和固定配置）

        支持：
            - CRAWLER_PROXY_FETCH_URL=动态代理提取接口（每次 crawl_page 调用都请求）
            - CRAWLER_PROXY_ADDR=host:port
            - CRAWLER_PROXY_AUTH_KEY=用户名
            - CRAWLER_PROXY_PASSWORD=密码
        """
        proxy_addr = self._fetch_proxy_addr()
        if not proxy_addr:
            return None

        # Playwright proxy server 需要协议前缀
        server = proxy_addr if "://" in proxy_addr else f"http://{proxy_addr}"
        proxy: dict = {"server": server}
        if self.proxy_auth_key:
            proxy["username"] = self.proxy_auth_key
        if self.proxy_password:
            proxy["password"] = self.proxy_password

        print(f"已启用代理: {server}")
        return proxy
    
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
        使用 Playwright + stealth 爬取页面内容（带反检测）

        Args:
            url: 目标 URL
            timeout: 超时时间（毫秒）

        Returns:
            页面 HTML 内容，失败返回 None
        """
        import random
        from playwright_stealth import Stealth

        target_url = str(url)
        try:
            with sync_playwright() as p:
                launch_options = {
                    "headless": True,
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-infobars",
                        "--window-size=1920,1080",
                    ],
                }
                proxy_settings = self._build_proxy_settings()
                if proxy_settings:
                    launch_options["proxy"] = proxy_settings

                browser = p.chromium.launch(**launch_options)

                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                    timezone_id="America/New_York",
                    extra_http_headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                        "Sec-CH-UA-Mobile": "?0",
                        "Sec-CH-UA-Platform": '"Windows"',
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                        "Upgrade-Insecure-Requests": "1",
                    },
                )
                context.set_default_navigation_timeout(timeout)
                context.set_default_timeout(timeout)

                page = context.new_page()

                # 应用 playwright-stealth：自动隐藏 webdriver、伪造
                # navigator.plugins/languages/chrome/permissions 等指纹
                Stealth().apply_stealth_sync(page)

                page.goto(target_url, wait_until="domcontentloaded")
                page.wait_for_load_state('networkidle')

                # 检测 Cloudflare 挑战页面并等待
                for _ in range(3):
                    title = page.title().lower()
                    body_text = page.inner_text("body")[:500].lower()
                    if ("just a moment" in title
                            or "checking your browser" in body_text
                            or "cf-challenge" in page.content()[:2000].lower()):
                        print(f"  检测到 Cloudflare 挑战，等待通过...")
                        page.wait_for_timeout(random.randint(5000, 8000))
                        page.wait_for_load_state('networkidle')
                    else:
                        break

                # 模拟人类行为：随机短暂等待
                page.wait_for_timeout(random.randint(500, 1500))

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
