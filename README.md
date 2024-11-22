# PostCrawler

[![GitHub Stars](https://img.shields.io/github/stars/NikoAoi/PostCrawler?style=social)](https://github.com/NikoAoi/PostCrawler/stargazers) [![GitHub Forks](https://img.shields.io/github/forks/NikoAoi/PostCrawler?style=social)](https://github.com/NikoAoi/PostCrawler/network/members)

PostCrawler是一个用于爬取网站：[技术文章摘抄](https://learn.lianglianglee.com/)上的文章的爬虫



# 准备工作



## 使用到以下组件或工具

| 组件或工具                           | 版本                               | 链接                                              |
| :----------------------------------- | ---------------------------------- | ------------------------------------------------- |
| Ubuntu 22.04.5 LTS (Jammy Jellyfish) | 22.04（桌面版）                    | https://releases.ubuntu.com/jammy/                |
| Python                               | 3.10                               | Ubuntu22.04预载Python3.10                         |
| Deno                                 | 2.0.6                              | https://deno.com/                                 |
| Chrome Browser                       | 64 位 .deb（适用于 Debian/Ubuntu） | https://www.google.com/chrome/                    |
| single-file-cli                      | /                                  | https://github.com/gildas-lormeau/single-file-cli |



## 安装Ubuntu22.04桌面版



略



## 安装Deno



```
curl -fsSL https://deno.land/install.sh | sh
```



## 安装Chrome浏览器



1. 使用Ubuntu自带的FireFox浏览器访问Chrome官网下载`google-chrome-stable_current_amd64.deb`
2. 执行以下命令安装

```
sudo apt install ./google-chrome-stable_current_amd64.deb
```



## 安装single-file-cli



引用自[组件的github](https://github.com/gildas-lormeau/single-file-cli)

> - Download and unzip manually the [master archive](https://github.com/gildas-lormeau/single-file-cli/archive/master.zip) provided by Github
>
>   ```shell
>   unzip master.zip .
>   cd single-file-cli-master
>   ```

>
>
>- Make `single-file` executable (Linux/Unix/BSD etc.).
>
>  ```
>  chmod +x single-file
>  ```



# 开始使用



```
python bugs_v2.py <url> [--posts_limit {number}] [--links_limit {number}]
```



## 参数说明



| 参数        | 说明                                                         |
| :---------- | :----------------------------------------------------------- |
| url         | 要爬取的页面的链接，但实际上这个脚本只适配了[技术文章摘抄](https://learn.lianglianglee.com/)这个网站首页的页面结构，所以一般是写死的；有需要的话可以自己改造脚本来适应不同网站的页面结构 |
| posts_limit | [技术文章摘抄](https://learn.lianglianglee.com/)首页的一个文章合集我称为一个posts（例如，[10x程序员工作法](https://learn.lianglianglee.com/专栏/10x程序员工作法)就是一个posts），这个参数用于限制爬虫最终爬取的文章合集的数量，例如，当使用 `--posts_limit 1` 作为参数时，表示只会爬取第一个文章合集；不指明该参数时，将会爬取所有文章合集 |
| links_limit | 这个参数用于设置爬虫最终爬取文章合集中的文章的数量，当使用 --links_limit 1 作为参数时，表示只会爬取每个文章合集里的第一篇文章；不指明该参数时，将会爬取文章合集里的所有文章 |



## 使用方法



```
python bugs_v2.py "https://learn.lianglianglee.com"
```



执行后，脚本会在当前目录下创建一个目录用于存放所有下载的文章



---



# TODO

| Task                                                         | Status |
| :----------------------------------------------------------- | :----- |
| 完成脚本的第一个版本                                         | ✔      |
| 将脚本执行过程中产生的日志输出到文件中                       | ❌      |
| 加入重试机制，所有导出任务完成后重新下载那些没有下载成功的html | ❌      |
| 加入下载超时机制，某条链接下载时超过指定时间仍未能下载完成，则打印错误日志，之后直接下载下一条连接 | ❌      |
| 断点续传机制。新增一个指定下载目录的参数，下载HTML前会判断目录中是否已存在该文件，若存在则跳过 | ❌      |

