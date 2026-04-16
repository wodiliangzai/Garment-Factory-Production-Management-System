from flask import Flask,redirect,url_for,render_template,session
from models import TOPModel, PermissionModel
from blueprint.user import user_bp
from blueprint.procurement import procurement_bp
from blueprint.product import product_bp
from blueprint.storage import storage_bp
from blueprint.customer import customer_bp
from blueprint.taskmodule import taskmodule_bp
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
app.register_blueprint(taskmodule_bp)

with app.app_context():
    #根据模型建表,如果数据库中模型中涉及的的表已经存在,就直接跳过,即使后续作出修改也不会影响
    db.create_all()

#默认登录页
@app.route('/')
def index():
    return redirect(url_for('user.login'))

#首页
@app.route('/home')
@login_required
def home():
    username = session.get('username')
    # 获取当前用户的角色权限信息
    permissions = PermissionModel.query.filter_by(username=username).all()
    roles = [p.charactercode for p in permissions]
    
    # 判断是否为管理员或采购员
    is_admin_or_purchaser = ('GAdmin' in roles) or ('GPurchaser' in roles)
    
    # 查找所有进行中的任务
    active_tops = TOPModel.query.filter_by(taskstatus='进行中').all()
    
    # 整理数据：结构为 { taskname: {'altertime': xxx, 'finishtime': xxx, 'items': [...] } }
    tasks_data = {}
    
    for top in active_tops:
        # 提取公共时间（优先展示第一条记录的时间）
        if top.taskname not in tasks_data:
            tasks_data[top.taskname] = {
                'altertime': top.altertime.strftime('%Y-%m-%d %H:%M:%S') if top.altertime else '无',
                'finishtime': top.finishtime.strftime('%Y-%m-%d %H:%M:%S') if top.finishtime else '无',
                'task_items': []  # 注意这里改为了 task_items
            }
        
        # 1. 如果身份为管理员或采购员，按任务单级别展示进度
        if is_admin_or_purchaser:
            # 综合该任务单下的所有生产项数量计算总体进度
            total_qty = sum([float(item.quantity) for item in top.gpitems])
            total_completed = sum([float(item.completed) for item in top.gpitems])
            
            progress = 0
            if total_qty > 0:
                progress = round((total_completed / total_qty) * 100, 2)
                progress = min(progress, 100) # 最高到100%
            
            tasks_data[top.taskname]['task_items'].append({
                'materialcode': top.materialcode,
                'materialdesc': top.gmaterial.materialdesc,
                'quantity': total_qty,   # <--- 新增传递 quantity 数据
                'progress': progress
            })
            
        # 2. 如果是其他身份，按该身份相关的生产项(PItem)级别展示进度
        else:
            # 过滤找到当前角色的生产工序匹配的生产项
            for pitem in top.gpitems:
                if pitem.gsequence.charactercode in roles:
                    progress = 0
                    if float(pitem.quantity) > 0:
                        progress = round((float(pitem.completed) / float(pitem.quantity)) * 100, 2)
                        progress = min(progress, 100) # 最高到100%
                    
                    tasks_data[top.taskname]['task_items'].append({
                        'materialcode': pitem.materialcode,
                        'materialdesc': pitem.gmaterial.materialdesc,
                        'quantity': float(pitem.quantity),   # <--- 新增传递 quantity 数据
                        'progress': progress
                    })
    
    # 清理那些在其他角色下没有任何相关生产项的空任务节点
    if not is_admin_or_purchaser:
        tasks_data = {k: v for k, v in tasks_data.items() if len(v['task_items']) > 0}

    return render_template('index.html', tasks_data=tasks_data)

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
    #此处修改host为0.0.0.0可以让局域网内的其他设备访问到我电脑上的flask项目