# 知乎的登陆
import requests
import execjs
import time
import hashlib
import hmac
from PIL import Image
import base64
from http import cookiejar  # 用于保存登陆的cookie
from urllib import parse
import json
import psycopg2
import datetime
import re

class ZhiHu(object):

    def __init__(self,phone,password,username,keyword,conn,cur):
        self.timestamp = int(time.time() * 1000)
        self.phone = phone
        self.password = password
        self.username = username
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36',
            'x-zse-83': '3_1.1',
            'content-type': 'application/x-www-form-urlencoded'
        }
        self.session = requests.session()
        self.session.cookies = cookiejar.LWPCookieJar('cookie.txt')  # 保存的cookie文件
        self.keyword = keyword
        self.cur = cur
        self.conn = conn


        with open('get_formdata.js', 'r', encoding='utf-8') as f:
            self.encry_js = f.read()

    def get_signature(self):
        h = hmac.new(b'd1b964811afb40118a12068ff74a12f4', None, hashlib.sha1)
        h.update('password'.encode('utf-8'))
        h.update('c3cef7c66a1843f8b3a9e6a1e3160e20'.encode('utf-8'))
        h.update('com.zhihu.web'.encode('utf-8'))
        h.update(str(self.timestamp).encode('utf-8'))
        return h.hexdigest()

    def get_captcha(self):
        url = 'https://www.zhihu.com/api/v3/oauth/captcha?lang=en'
        r = self.session.get(url, headers=self.headers)
        if r.status_code == 200 and 'true' in r.text:
            print('需要输入验证码')
            r = self.session.put(url, headers=self.headers)
            with open('captcha.png', 'wb') as f:
                content = base64.b64decode(r.json()['img_base64'])  # 需要先将base64加密的解密为字符串
                f.write(content)
            img = Image.open('captcha.png')
            img.show()
            captcha = input('请输入验证码\n>')
            return captcha

    def verify_captcha(self, captcha):
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36',
        }
        data = {
            'input_text': captcha
        }
        url = 'https://www.zhihu.com/api/v3/oauth/captcha?lang=en'
        r = self.session.post(url, headers=headers, data=data)
        return 'true' in r.text

    def get_form_data(self, signature, captcha):
        text = "client_id=c3cef7c66a1843f8b3a9e6a1e3160e20&grant_type=password&timestamp={0}&" \
               "source=com.zhihu.web&signature={1}&username=%2B86{2}&password={3}&" \
               "captcha={4}&lang=cn&ref_source=homepage&utm_source=".format(self.timestamp, signature, self.phone, self.password, captcha)
        ctx = execjs.compile(self.encry_js)
        encry = ctx.call('Q', text)
        return encry

    def login(self, encry):
        url = 'https://www.zhihu.com/api/v3/oauth/sign_in'
        self.session.post(url, headers=self.headers, data=encry)

    def verify_login(self,):
        r = self.session.get('https://www.zhihu.com/notifications', headers=self.headers)
        if self.username in r.text:
            print('登陆成功')
            self.session.cookies.save()
            return True
        else:
            print('登陆失败')
            return False

    def run(self):
        sign = self.get_signature()
        captcha = self.get_captcha()
        print(sign,captcha)
        if captcha:
            while not self.verify_captcha(captcha):
                captcha = self.get_captcha()
        encry = self.get_form_data(sign, captcha)
        self.login(encry)

    def read_cookie2login(self):
        # 读取cookie来登陆
        try:
            self.session.cookies.load()  # 加载cookie到session
            print('加载cookie成功')
        except:
            print('cookie未能加载，需要登陆')
            self.run()
        # 验证登陆
        print(self.verify_login())

    #获取关键词相关问题url
    def get_information_id(self):
        url_list = []
        now_date = datetime.datetime.now().date()
        for index in range(0,1000,20):
            url = 'https://www.zhihu.com/api/v4/search_v3?t=general&q={0}&correction=1&offset={1}&limit=20&lc_idx={2}&show_all_topics=0'.format(parse.quote(keyword),index,index+5)
            html = self.session.get(url, headers=self.headers).text
            json_html = json.loads(html)
            if json_html['paging']['is_end'] == 'true':  #到达最终页
                break
            else:
                total_list = json_html['data']
                for one_dict in total_list:
                    if one_dict['type'] == 'one_box':
                        content_list = one_dict['object']['content_list']

                        '''
                         #获取所有相关问题 文章 url
                         #类型    0 ：问答  1：文章 
                     '''
                        for content in content_list:
                            if content['type'] == 'answer':  #问答
                                # url_dict['url'] = 'https://www.zhihu.com/question/'+content['question']['id']
                                # url_dict['flag'] = 0
                                url ='https://www.zhihu.com/question/'+content['question']['id']
                            elif content['type'] == 'article': #文章
                                url = content['url']
                    elif one_dict['type'] == 'search_result':
                        if one_dict['object']['type'] == 'article':
                            url = one_dict['object']['url']  #文章
                        elif one_dict['object']['type'] == 'answer':
                            url = 'https://www.zhihu.com/question/'+one_dict['object']['question']['id']  #问答
                    #存储数据
                    if url not in url_list:
                        url_list.append(url)
                        self.cur.execute("INSERT INTO zhihu_question_id (url,keyword,page,date ) values ('{0}','{1}','{2}','{3}')".format(url,keyword,index,now_date))
                        self.conn.commit()
        return url_list

    #根据url获取问题下所有回答 和 作者相关信息
    def get_information(self,origin_url):
        id = re.findall(r"(\d+)",origin_url)[0]
        if 'question' in origin_url:
            type = 'question'
        else:
            type = 'article'

        #问题
        if type == 'question':
            for index in range(0,200,5):
                url = 'https://www.zhihu.com/api/v4/questions/{0}/answers?include=data[*].is_normal,admin_closed_comment,reward_info,is_collapsed,' \
                      'annotation_action,annotation_detail,collapse_reason,is_sticky,collapsed_by,suggest_edit,comment_count,can_comment,' \
                      'content,editable_content,voteup_count,reshipment_settings,comment_permission,created_time,updated_time,review_info,relevant_info,' \
                      'question,excerpt,relationship.is_authorized,is_author,voting,is_thanked,is_nothelp,is_labeled,is_recognized,paid_info;' \
                      'data[*].mark_infos[*].url;data[*].author.follower_count,badge[*].topics&limit=5&offset={1}&platform=desktop&sort_by=default'.format(id,index)
                html = self.session.get(url, headers=self.headers).text
                json_html = json.loads(html)
                if json_html['paging']['is_end'] == 'true':
                    break
                else:
                    data_list = json_html['data']
                    for m in data_list:
                        information_dict = {}
                        #问题相关
                        information_dict['data_type'] = type
                        information_dict['question_title'] = m['question']['title'] #问题
                        information_dict['question_url'] = origin_url  #问题url
                        information_dict['question_create_time'] = datetime.datetime.utcfromtimestamp(m['question']['created']).strftime("%Y-%m-%d %H:%M:%S") #问题创建时间
                        information_dict['question_update_time'] = datetime.datetime.utcfromtimestamp(m['question']['updated_time']).strftime("%Y-%m-%d %H:%M:%S") #问题更新时间
                        #回答相关
                        information_dict['answer_url'] = m['url']  #回答url
                        information_dict['answer_voteup_count'] = m['voteup_count']  #回答赞同数
                        information_dict['answer_comment_count'] = m['comment_count']  #回答评论数
                        information_dict['answer_content'] = m['content']  #回答内容
                        information_dict['answer_create_time']  = datetime.datetime.utcfromtimestamp(m['created_time']).strftime("%Y-%m-%d %H:%M:%S")  #回答创建时间
                        information_dict['answer_update_time']  = datetime.datetime.utcfromtimestamp(m['updated_time']).strftime("%Y-%m-%d %H:%M:%S")  #回答更新时间
                        #用户相关
                        information_dict['author_url'] = 'https://www.zhihu.com/people/'+m['author']['url_token']+'/activities'  #回答用户链接
                        information_dict['author_name']  = m['author']['name'] #回答用户名称
                        information_dict['author_picture']  = m['author']['avatar_url'] #回答用户头像地址
                        information_dict['author_headline']  = m['author']['headline']  #回答用户签名
                        information_dict['author_gender']  = m['author']['gender']  #回答用户性别  1 男  -1 未知 0 女
                        print(information_dict)
                        self.cur.execute("INSERT INTO zhihu_answer (data_type,question_title,question_url,question_create_time,question_update_time,author_name,"
                                         "author_gender,author_headline,author_url,author_picture,answer_content,answer_voteup_count,answer_comment_count,"
                                         "answer_create_time,answer_update_time,answer_url ) values ('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}',"
                                         "'{8}','{9}','{10}','{11}','{12}','{13}','{14}','{15}')".format(information_dict['data_type'],information_dict['question_title'],information_dict['question_url'],
                                                                                    information_dict['question_create_time'],information_dict['question_update_time'],information_dict['author_name'],
                                                                                    information_dict['author_gender'],information_dict['author_headline'],information_dict['author_url'],
                                                                                    information_dict['author_picture'],information_dict['answer_content'], information_dict['answer_voteup_count'],
                                                                                    information_dict['answer_comment_count'],information_dict['answer_create_time'],information_dict['answer_update_time'],
                                                                                    information_dict['answer_url']))
                        self.conn.commit()
        #文章
        else:
            html = self.session.get(origin_url, headers=self.headers).text
            json_html = json.loads(html)
            information_dict = {}
            information_dict['data_type'] = type
            information_dict['question_title'] = json_html['title']  #文章标题
            #文章相关
            information_dict['answer_url'] = 'https://zhuanlan.zhihu.com/p/'+id  #文章路径url
            information_dict['answer_voteup_count'] = json_html['voteup_count']  #文章赞同数
            information_dict['answer_comment_count'] = json_html['comment_count']  #文章评论数
            information_dict['answer_content'] = json_html['content']  #文章内容
            information_dict['answer_create_time'] = datetime.datetime.utcfromtimestamp(json_html['created']).strftime("%Y-%m-%d %H:%M:%S") #文章创建时间
            information_dict['answer_update_time'] = datetime.datetime.utcfromtimestamp(json_html['updated']).strftime("%Y-%m-%d %H:%M:%S") #文章修改时间
            #用户相关
            information_dict['author_url'] = 'https://www.zhihu.com/people/'+json_html['author']['url_token']+'/activities'  #回答用户链接
            information_dict['author_name']  = json_html['author']['name'] #文章用户名称
            information_dict['author_picture']  = json_html['author']['avatar_url'] #文章用户头像地址
            information_dict['author_headline']  = json_html['author']['description']  #文章用户签名
            information_dict['author_gender']  = json_html['author']['gender']  #w文章用户性别  1 男  -1 未知 0 女

            self.cur.execute("INSERT INTO zhihu_answer (data_type,question_title,author_name,"
                             "author_gender,author_headline,author_url,author_picture,answer_content,answer_voteup_count,answer_comment_count,"
                             "answer_create_time,answer_update_time,answer_url ) values ('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}',"
                             "'{8}','{9}','{10}','{11}','{12}')".format(information_dict['data_type'],information_dict['question_title'],
                                                                                             information_dict['author_name'],
                                                                                             information_dict['author_gender'],information_dict['author_headline'],information_dict['author_url'],
                                                                                             information_dict['author_picture'],information_dict['answer_content'], information_dict['answer_voteup_count'],
                                                                                             information_dict['answer_comment_count'],information_dict['answer_create_time'],information_dict['answer_update_time'],
                                                                                             information_dict['answer_url']))
            self.conn.commit()

if __name__ == '__main__':
    #配置数据库
    conn = psycopg2.connect(database="postgres", user="postgres", password="19950626", host="47.100.18.128", port="5432")
    cur = conn.cursor()
    #配置账号信息
    phone = ''  # 账号
    password = ''  # 密码
    username = ''  # 用户名，用于验证登陆
    keyword = input('输入搜索的关键词:')

    zhihu = ZhiHu(phone,password,username,keyword,conn,cur)
    zhihu.read_cookie2login()
    #1
    url_list = zhihu.get_information_id()
    for url in url_list:
       zhihu.get_information(url)
    conn.close()

    #避免重复爬取 从数据库中筛选需要爬取的url

    #2
    # cur.execute("select url from zhihu_question_id where date = '2019-04-11' and keyword = '刘鑫'")
    # url_list = cur.fetchall()
    # for url in url_list:
    #     zhihu.get_information(url[0])
    # conn.close()
