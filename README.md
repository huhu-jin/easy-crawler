# 综合说明
python的爬虫项目, beautiful soup 负责html解析, playwright 模拟用户操作, 需要将网页内容转化markdown, 目前将爬取的内容保存在本地, Flask提供查询数据的接口

# 如何爬
## 读取配置文件
```
[
    {
        "url": "https://www.bis.gov/news-updates",
        "desc": "美国商务部网站1"
    },
    {
        "url": "https://www.bis.gov/news-updates",
        "desc": "美国商务部网站2"
    }
]
```
1 逐个监控url,url中的列表,列表的更新时间为今天时候, 列表为 ul > li的结构.检测时间为程序启动,或者每隔12小时
2 如果更新则获取url中的链接,然后将链接中的网页内容转化为 markdown存储(每日新建一个文件夹,每个markdown一个文件)
3 提供接口查询某天所有更新markdown的列表, 提供一个详细markdown获取的接口



# docker
firecrawl
```
docker-compose up -d
```