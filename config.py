# config.py  数据库配置信息，此处利用sql server身份验证在本机连接数据库
USERNAME = "sa"  # 数据库登录用户名
PASSWORD = "159m4159"  # 数据库登录密码
HOST = "127.0.0.1"  # 数据库服务器地址，若为远程服务器填写对应的IP地址，这里是本机地址
PORT = "1433"  # 数据库连接端口号，MSSQL SERVER默认常用端口是1433，默认端口可不加
DATABASE = "GDatabase"  # 要访问的数据库名称
# 创建统一资源标识符（URI），用于指定数据库连接的详细信息
# SQLALCHEMY_DATABASE_URI的格式为：数据库类型 + 驱动://{登录名}:{密码}@{IP地址}:{端口号}/{数据库名}?charset={编码格式}
DB_URI = f'mssql+pymssql://{USERNAME}:{PASSWORD}@{HOST}/{DATABASE}?charset=utf8'
# SQLALCHEMY_DATABASE_URI配置项，设置数据库的连接URI，让SQLAlchemy知道如何连接数据库
SQLALCHEMY_DATABASE_URI = DB_URI
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 1800,
    "pool_timeout": 30
}

#邮箱配置
MAIL_SERVER="smtp.qq.com"
MAIL_USE_SSL=True
MAIL_PORT=465
MAIL_USERNAME="2696503630@qq.com"
MAIL_PASSWORD="xqldjawmdlpzdffd"
MAIL_DEFAULT_SENDER="2696503630@qq.com"

SECRET_KEY="AsDfAsDfJaSdFjAsD;Iffaf3243_[3@fdsfs" #要用session加密必须使用secret_key,同样的Flask-WTF默认开启CSRF防护,成表单时需要用到SECRET_KEY。