知乎
=============

实现模拟登录  根据搜索的关键词爬取相关信息  
------------------------------
-   获取所有问题相关信息 （问题类型，问题描述，问题URL，问题创建时间，问题描述时间）
-   获取问题下的所有回答 （回答URL，回答赞同数，回答评论数，回答内容，回答创建时间，回答更新时间）
-   获取所有回答者的用户信息 （用户URL，用户名称，用户头像地址，用户签名，用户性别）

![](https://img.shields.io/pypi/v/nine.svg?color=green&label=version)
-----

2019-4-25
--
- 已开放api，无需配置运行脚本直接调用接口即可获得相同数据

  - 详情项目移步：
    - https://github.com/suxin1995/Flask_Api-spider


1.配置
--

**a.  实例化 ZhiHu 类** 

`zhihu = ZhiHu(phone,password,username,keyword)`
>需要配置账号信息：手机号，密码，用户名

>需要配置搜索信息信息： 关键词



2.爬取信息
--

获取相关问题URL:

`zhihu.get_information_id()`

获取该url下全部回答:

`zhihu.get_information(url)`

3.数据存储
--
当前demo只是简单的print

可自定义数据处理函数

将数据保存txt 或 数据库中


4.结果示例
--

![](image/results1.png )


![](image/results2.png )