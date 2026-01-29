from flask import Flask,redirect,url_for,render_template
from blueprint.user import user_bp
from blueprint.procurement import procurement_bp
from blueprint.product import product_bp
from blueprint.storage import storage_bp
from blueprint.customer import customer_bp
from exts import db,mail
from flask_migrate import Migrate
from decorators import login_required,admin_required
# 使用Flask类创建app对象
app = Flask(__name__)
print('__name__', __name__)
app.config.from_object('config') # 从config.py文件中加载配置
db.init_app(app)# 在进行初始化之前一定要先加载好配置再进行初始化
mail.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(user_bp)
app.register_blueprint(procurement_bp)
app.register_blueprint(product_bp)
app.register_blueprint(storage_bp)
app.register_blueprint(customer_bp)

with app.app_context():
    #根据模型建表,如果数据库中模型中涉及的的表已经存在,就直接跳过,即使后续作出修改也不会影响
    db.create_all()

@app.route('/')
def index():
    return redirect(url_for('user.login'))

@app.route('/home')
@login_required
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
    #此处修改host为0.0.0.0可以让局域网内的其他设备访问到我电脑上的flask项目