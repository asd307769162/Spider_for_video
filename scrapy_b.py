# -*- coding: utf-8 -*-
import random
import time
from bs4 import BeautifulSoup
from selenium import webdriver
import os
import pandas as pd
# import requests
from tqdm import tqdm
import math
import re

# 这些始终要用到，作为全局，可以加快code运行速度
chrome_options = webdriver.ChromeOptions()
# 使用headless无界面浏览器模式
chrome_options.add_argument('--headless') # 增加无界面选项
chrome_options.add_argument('--disable-gpu') #如果不加这个选项，有时定位会出现问题
# 启动浏览器
driver = webdriver.Chrome(options=chrome_options)
# 隐式等待
driver.implicitly_wait(10)
# 防止被识别， 设置随机等待秒数
rand_seconds = random.choice([1, 3]) + random.random()

# 给url获取soup
def get_soup(url):
    # print(url)
    # 获取网页源代码
    driver.get(url)
    content = driver.page_source
    soup = BeautifulSoup(content, 'lxml')
    return soup


# 获取番剧的链接list
def getFirstContent(soup):
    # print(content)
    # soup = BeautifulSoup(content, "html.parser")
    # 搜索的页面出来得到视频部分信息
    next_urls = []
    infos = soup.find_all('a','bangumi-title')
    for info in infos:
        next_urls.append(info['href'].strip())
    # print(len(infos))

    return next_urls


# 获取番剧的一些信息
def getDetail(path):
    links = pd.read_csv(path)
    urls = links['links']
    cont_id = 0
    print("start!")
    v_ids = []  # id
    titles = []  # 标题
    genres = []  # 类型
    years = []  # 年份
    long_comms = []  # 长评论数
    short_comms = []  # 短评论数
    detail_link = []  # 当前页面链接
    for url2 in tqdm(urls):
        try:
            soup1 = get_soup(r'http:' + url2)
            next_link = soup1.find('a', 'media-title')['href']
            soup2 = get_soup(r'http:' + next_link + r'#long')  # 长评页面

            '''
                        soup2.find('div', 'media-tab-nav').find('ul').find_all('li'):
                        [<li class="">作品详情</li>,
                         <li class="on">长评 ( 572 )</li>,
                         <li class="">短评 ( 117867 )</li>,
                         <li class="">相关视频</li>]
                        '''
            # 评分数， '长评 ( 572 )' 取数字572,变为int,没有评论等信息的不需要，进行跳过
            long = int(soup2.find('div', 'media-tab-nav').find('ul').find_all('li')[1].string[5:-2])
            short = int(soup2.find('div', 'media-tab-nav').find('ul').find_all('li')[2].string[5:-2])
            long_comms.append(long)
            short_comms.append(short)
            # 取标题
            title = soup2.find('span', 'media-info-title-t').string
            titles.append(title)
            # 取标签
            tags = ''
            for tag in soup2.find('span', 'media-tags').children:
                tags = tags + str(tag.string) + ','  # tags='漫画改,战斗,热血,声控,'
            genres.append(tags)
            # 截取年份：'2019年4月7日开播'
            year = soup2.find('div','media-info-time').span.string[0:4]
            years.append(year)

            # 增加id的大小
            cont_id += 1
            v_ids.append(cont_id)
            # 获取当前页面链接
            detail_link.append(r'http:' + next_link)

            # soup2.find('div','review-list-wrp type-long').find('ul').contents
            if cont_id % 10 == 0:
                print('已爬取%d条' % cont_id)
            # 每5条写入一次，防止中断导致数据丢失
            if cont_id % 5 == 0:
                # 写入
                Data_detail = {'v_id': v_ids, 'title': titles, 'genres': genres, 'year': years,
                               'long_comm': long_comms,
                               'short_comm': short_comms, 'detail_link': detail_link}
                fname_detail = "new_video_data.csv"
                wirte2csv(Data_detail, fname_detail)
                # 清空
                v_ids = []  # id
                titles = []  # 标题
                genres = []  # 类型
                years = []  # 年份
                long_comms = []  # 长评论数
                short_comms = []  # 短评论数
                detail_link = []  # 当前页面链接
            time.sleep(5)

        except Exception:
            pass
    return


# 滚动获取信息的方法
def get_rating(url,page_num):
    # 获取网页源代码
    driver.get(url)
    # driver.get(url + r'#long')
    # page_num = long_page_num
    id_names = []
    ratings = []
    # 循环几次  滚动几次
    for i in range(page_num):
        # 让浏览器执行简单的js代码，模拟滚动到底部（只滚动一次）
        js = "window.scrollTo(0,document.body.scrollHeight)"
        driver.execute_script(js)
        time.sleep(rand_seconds)
        if i == page_num-1:
            # 获取页面
            content = driver.page_source
            # 放入解析
            soup = BeautifulSoup(content, 'lxml')
            # 找到这页id
            for li in soup.find_all('li','clearfix'):
                id_names.append(li.find('div',re.compile('review-author-name')).string.strip())
                rat = len(li.find_all('i', 'icon-star icon-star-light'))  # 评分
                ratings.append(rat)

    return id_names,ratings


# 获取rating，相关信息，并存入csv
def get_rating_data(path):
    detail = pd.read_csv(detail_data_path)
    # print(min(detail['short_comm']+detail['long_comm']))  # 222;222*470=104340
    # print(detail.columns)  # ['v_id', 'title', 'genres', 'year', 'long_comm', 'short_comm','detail_link']
    minn = min(detail['short_comm'] + detail['long_comm'])
    rating_links = detail['detail_link']
    long_num = detail['long_comm']
    short_num = detail['short_comm']
    v_ids = detail['v_id']
    for ind, url in enumerate(tqdm(rating_links)):
        # print(ind,url)
        # 按比例取长短评价
        lon = int((long_num[ind] / (long_num[ind] + short_num[ind])) * minn)
        sho = minn - lon

        long_page_num = math.ceil(lon / 20)  # 一页20个数据，看需要滑动几页
        short_page_num = math.ceil(sho / 20)  # 一页20个数据，看需要滑动几页

        id_l, rat_l = get_rating(url + r'#long', long_page_num)
        id_s, rat_s = get_rating(url + r"#short", short_page_num)
        # print(len(id_l))
        # print(len(id_s))

        # 需要把之前的长短评价各自分配的数目取到
        id_total = id_l[0:lon]+id_s[0:sho]
        rat_total = rat_l[0:lon]+rat_s[0:sho]
        # print(len(id_total))
        # print(len(rat_total))

        # 封装到DataFrame
        Data_rating = {'user_id_name': id_total,'v_id':[v_ids[ind]]*minn,'rating':rat_total}
        # print(Data_rating)
        fname_rating = "rating_data.csv"
        wirte2csv(Data_rating, fname_rating)
    return


# 写入csv
def wirte2csv(Data,fname):
    try:
        if os.path.exists(fname):
            DataFrame = pd.DataFrame(Data)
            DataFrame.to_csv(fname, index=False, sep=',', mode='a', header=False)
            print('追加成功！')
        else:
            DataFrame = pd.DataFrame(Data)
            DataFrame.to_csv(fname, index=False, sep=',')
            print('save!')
    except:
        print('fail')


if __name__ == '__main__':
    rating = []  # 评分
    flag = 0  # 要不要爬取番剧列表页和番剧信息
    if flag:

        for i in tqdm(range(21)):
            # 从0开始的原因是，对于第一次访问的页面会连续访问两次，导致重复爬取，所以i=0时获取页面，但是不去存入信息
            # 剧番页面，从1-20页
            url = 'https://www.bilibili.com/anime/index/#season_version=-1&area=-1' \
              '&is_finish=-1&copyright=-1&season_status=-1&season_month=-1&year=-1' \
              '&style_id=-1&order=3&st=1&sort=0&page='+str(i+1)
            #  刷新，重要！！！否则可能会导致重复爬取第一个页面
            driver.refresh()
            # print(url)
            soup = get_soup(url)
            if i == 0:
                continue
            #driver.find_element_by_class_name('p next-page').click()
            next_urls = getFirstContent(soup)
            print(next_urls)
            # 写入csv
            Data_link = {'links': next_urls}
            fname_link = "link_data.csv"
            wirte2csv(Data_link, fname_link)
            print('爬到第%d页' % i)
            # 暂停
            time.sleep(5)

        # 读取csv
        # path = './link_data_test.csv'
        path = './link_data.csv'
        # 爬取细节并存入新的csv
        getDetail(path)

    detail_data_path = r'D:\Learning\postgraduate\bilibili\scrapy_py\new_video_data.csv'
    get_rating_data(detail_data_path)

    driver.close()