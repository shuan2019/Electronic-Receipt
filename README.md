# 收据打印系统

## 简介
一个基于Flask的Web收据打印系统，支持收据填写、预览、打印和历史记录。

## 安装依赖
```bash
pip install -r requirements.txt
```

## 初始化数据库
```bash
python
>>> from app import db
>>> db.create_all()
>>> exit()
```

## 启动项目
```bash
python app.py
```

## 访问方式
浏览器访问：http://127.0.0.1:5000/ 