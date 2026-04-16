from flask import Blueprint,render_template,jsonify,redirect,url_for,session,request,render_template_string,flash,json
from datetime import datetime
import string
from exts import db
from models import MaterialModel,CraftModel,FormulaModel,CharacterModel,WarehouseModel,SequenceModel,TOPModel, PItemModel
from forms import AddmaterialForm,AltermaterialForm,CraftForm,AddcraftForm,AddtaskForm,AltertaskForm
from snowflake import SnowflakeGenerator
from decorators import login_required,admin_required

# 初始化雪花算法生成器 (ID=1，避免与采购模块冲突)
gen = SnowflakeGenerator(1)

product_bp=Blueprint('product',__name__,url_prefix='/product')

#查找配方组件函数
def get_formula_tree_recursive(craft_id, tree_list, visited_crafts=None, parent_unique_id=None):
    """
    craft_id: 当前正在查找的工艺ID
    tree_list: 结果列表
    visited_crafts: 路径防循环记录
    parent_unique_id: 上一级配方行的 formulaid (用于确保唯一层级关系)
    """
    if visited_crafts is None:
        visited_crafts = set()
    
    # 使用浅拷贝或者是路径拷贝，避免同一种半成品在不同分支被误判为循环
    # 这里简单起见，仅记录当前分支
    current_path = set(visited_crafts)
    current_path.add(craft_id)

    formulas = FormulaModel.query.filter_by(craftid=craft_id).all()
    
    for formula in formulas:
        component_material = formula.gcomponent
        
        # 1. 确定当前节点的唯一ID
        # 直接使用 formulaid，这是数据库主键，绝对唯一
        current_node_id = formula.formulaid
        
        # 2. 确定当前节点的父级ID
        # 如果 parent_unique_id 为空，说明是顶层，父级仍然用 formula.combination (物料码) 
        # 因为顶层物料码在表格里不存在，TreeTable 会将其视为根节点，这正是我们要的
        actual_parent_id = parent_unique_id if parent_unique_id else formula.combination

        node = {
            'formulaid': formula.formulaid,
            'id': current_node_id,           # 【修改】使用唯一ID，不再是 component
            'parent': actual_parent_id,      # 【修改】指向上一级配方行的唯一ID
            'material_code': formula.component, # 【新增】专门用于前端显示的物料编码字段
            'desc': component_material.materialdesc,
            'spec': component_material.specification,
            'qty': formula.usage,
            'is_root': False
        }
        tree_list.append(node)

        sub_craft = CraftModel.query.filter_by(materialcode=formula.component).first()
        
        if sub_craft and sub_craft.craftid not in current_path:
            # 【关键】递归时，将当前的 formulaid 传下去，作为下一级的 parent
            get_formula_tree_recursive(sub_craft.craftid, tree_list, current_path, current_node_id)

def check_circular_dependency(target_child, target_parent, visited=None):
    if visited is None:
        visited = set()
    
    # 避免检测过程中的死循环
    if target_child in visited:
        return False
    visited.add(target_child)
    
    # 查找生产 target_child 的工艺
    child_craft = CraftModel.query.filter_by(materialcode=target_child).first()
    
    # 如果该物料没有对应的生产工艺（它是纯原材料），则路径终止，不会产生循环
    if not child_craft:
        return False
    
    # 查找该工艺下的所有配方组件
    formulas = FormulaModel.query.filter_by(craftid=child_craft.craftid).all()
    
    for f in formulas:
        # 如果组件就是我们要找的目标父级，说明形成了闭环 (A->B->A)
        if f.component == target_parent:
            return True
        # 否则递归检查下一级
        if check_circular_dependency(f.component, target_parent, visited):
            return True
            
    return False

def create_pitem_recursive(task_id, material_code, required_qty):
    """
    递归查找工艺和配方，生成任务生产项
    task_id: 所属任务单编号
    material_code: 当前需要生产的物料
    required_qty: 需产数量
    """
    # 1. 查找是否存在生产工艺
    craft = CraftModel.query.filter_by(materialcode=material_code).first()
    
    # 如果该物料没有工艺，说明它是原材料（采购件），不需要建立生产项，直接返回（根据需求）
    if not craft:
        return

    # 2. 生成生产项 (雪花算法)
    pitem_id = str(next(gen))
    
    new_pitem = PItemModel(
        itemid=pitem_id,
        taskid=task_id,
        materialcode=material_code,
        sequenceid=craft.sequenceid, # 从工艺中获取
        quantity=required_qty,
        craftid=craft.craftid,
        completed=0
    )
    db.session.add(new_pitem)

    # 3. 查找该工艺的配方（子件）
    formulas = FormulaModel.query.filter_by(craftid=craft.craftid).all()
    
    if formulas:
        for formula in formulas:
            # 计算子件的需求数量 = 父件数量 * 用量
            child_qty = float(required_qty) * float(formula.usage)
            
            # 递归调用：继续为子件查找工艺并生成生产项
            create_pitem_recursive(task_id, formula.component, child_qty)

#物料信息管理界面
@product_bp.route('/materialmanage')
@login_required
def materialmanage():
    materials = MaterialModel.query.all()
    addmaterialform=AddmaterialForm()
    altermaterialform=AltermaterialForm()
    return render_template('materialmanage.html',materials=materials,addmaterialform=addmaterialform,altermaterialform=altermaterialform)

#添加物料信息
@product_bp.post('/addmaterial')
@login_required
@admin_required
def addmaterial():
    addmaterialform=AddmaterialForm()
    if addmaterialform.validate():
        data = addmaterialform.data
        if MaterialModel.query.filter_by(materialcode=data['required']).first():
            flash("添加失败：物料代码已存在", "error")
            return redirect(url_for('product.materialmanage'))
        
        new_material = MaterialModel(
            materialcode=data['required'],
            materialdesc=data['realname'],
            specification=data['description'],
            materialtype=data['materialtype'],
            creationtime=datetime.now(),
            creater=session['username'], 
            altertime=datetime.now(),
            alteruser=session['username']
        )
        db.session.add(new_material)
        db.session.commit()
        flash("物料添加成功", "success")
        return redirect(url_for('product.materialmanage'))
    else:
        error_msgs = []
        for field, errors in addmaterialform.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        flash("物料添加失败："+ "; ".join(error_msgs), "error")
        return redirect(url_for('product.materialmanage'))

#修改物料信息    
@product_bp.post('/altermaterial/<string:role_code>')
@login_required
@admin_required
def altermaterial(role_code):
    altermaterialform=AltermaterialForm()
    if altermaterialform.validate():
        data = altermaterialform.data
        material = MaterialModel.query.filter_by(materialcode=role_code).first()
        if material:
            material.materialdesc = data['role_name']
            material.specification = data['role_desc']
            material.materialtype = data['role_type']
            material.altertime = datetime.now()
            material.alteruser = session['username']
            db.session.commit()
            return jsonify({'code':200,'msg':'物料修改成功'})
        else:
            return jsonify({'code':500,'msg':'物料已不存在，修改失败'})
    else:
        error_msgs = []
        for field, errors in altermaterialform.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        return jsonify({"code": 400, "msg": "; ".join(error_msgs)})

#生产工艺管理界面    
@product_bp.route('/processmanage')
@login_required
def processmanage():
    addcraftform=AddcraftForm()
    addcraftform.materialcode.choices =[('', '请选择物料编码')] + [(m.materialcode, f"{m.materialcode} - {m.materialdesc} - {m.specification}") for m in MaterialModel.query.all()]
    addcraftform.sequence.choices =[('', '请选择所属工序')] + [(s.sequenceid, s.sequencename) for s in SequenceModel.query.all()]
    addcraftform.warehouse.choices =[('', '请选择完成存放仓库')] + [(w.warehousecode, w.warehousename) for w in WarehouseModel.query.all()]
    crafts = CraftModel.query.all()
    return render_template('processmanage.html',crafts=crafts, addcraftform=addcraftform)

#添加生产工艺信息
@product_bp.post('/addcraft')
@login_required
@admin_required
def addcraft():
    addcraftform=AddcraftForm()
    # 关键：必须重新填充 SelectField 的 choices，否则 WTForms 会因为提交的值不在 choices 列表中而校验失败
    addcraftform.materialcode.choices =[('', '请选择物料编码')] + [(m.materialcode, f"{m.materialcode} - {m.materialdesc} - {m.specification}") for m in MaterialModel.query.all()]
    addcraftform.sequence.choices =[('', '请选择所属工序')] + [(s.sequenceid, s.sequencename) for s in SequenceModel.query.all()]
    addcraftform.warehouse.choices =[('', '请选择完成存放仓库')] + [(w.warehousecode, w.warehousename) for w in WarehouseModel.query.all()]

    if addcraftform.validate_on_submit():
        # 1. 业务逻辑校验：防止重复添加
        if CraftModel.query.filter_by(materialcode=addcraftform.materialcode.data).first():
            flash('添加失败：该物料已存在生产工艺，请勿重复添加。', 'error')
            return redirect(url_for('product.processmanage'))

        try:
            # 2. 调用雪花算法生成ID
            new_craft_id = str(next(gen))
            
            # 3. 创建新工艺对象
            new_craft = CraftModel(
                craftid=new_craft_id,
                materialcode=addcraftform.materialcode.data,
                sequenceid=addcraftform.sequence.data,
                storage=addcraftform.warehouse.data,
                usagestatus='未使用',  # 设置默认为未使用
                creationtime=datetime.now(),
                creater=session.get('username'),
                altertime=datetime.now(),
                alteruser=session.get('username')
            )
            
            db.session.add(new_craft)
            db.session.commit()
            
            flash('生产工艺添加成功，请添加配方数据', 'success')
            
            # 4. 添加完成后直接跳转到该工艺的详情界面
            return redirect(url_for('product.processinfo', craft_id=new_craft_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'系统错误: {str(e)}', 'error')
            return redirect(url_for('product.processmanage'))
    else:
        # 表单校验失败的处理（例如必填项为空）
        error_msgs = []
        for field, errors in addcraftform.errors.items():
            for error in errors:
                # 获取字段的中文标签名
                label = getattr(addcraftform, field).label.text
                error_msgs.append(f"{label}: {error}")
        flash("验证失败：" + "; ".join(error_msgs), "error")
        return redirect(url_for('product.processmanage'))

#生产工艺信息界面
@product_bp.route('/processinfo/<string:craft_id>')
@login_required
def processinfo(craft_id):
    craftform=CraftForm()
    craft = CraftModel.query.filter_by(craftid=craft_id).first()
    if not craft:
        return render_template_string("""
                <script>
                    alert('该工艺不存在！');
                    window.history.back();
                </script>
            """)
    craftform.sequence.choices = [(s.sequenceid, s.sequencename) for s in SequenceModel.query.all()]
    craftform.warehouse.choices = [(w.warehousecode, w.warehousename) for w in WarehouseModel.query.all()]
    craftform.sequence.default = craft.sequenceid
    craftform.warehouse.default = craft.storage
    craftform.process()
    craftform.role_code.data = craft.materialcode
    craftform.alteruser.data = craft.alteruser
    # 3. 构建配方树
    recipe_tree = []
    
    # 【修改点】不再添加成品的根节点，直接递归获取配方组件
    # jquery-treetable 特性：如果父节点ID在表中不存在，该行会自动显示为根节点
    get_formula_tree_recursive(craft_id, recipe_tree)

    materials = MaterialModel.query.all()
    materials_json = json.dumps([
        {
            'code': material.materialcode,
            'desc': material.materialdesc,
            'spec': material.specification
        }
        for material in materials
    ], ensure_ascii=False)
    return render_template('processinfo.html', craft=craft,craft_id=craft_id, craftform=craftform, recipe_tree=recipe_tree,materials_json=materials_json)

#修改生产工艺信息
@product_bp.post('/updatecraft/<string:craft_id>')
@login_required
@admin_required
def updatecraft(craft_id):
    craftform = CraftForm()
    # 必须重新填充 SelectField 的 choices，否则验证会失败
    craftform.sequence.choices = [(s.sequenceid, s.sequencename) for s in SequenceModel.query.all()]
    craftform.warehouse.choices = [(w.warehousecode, w.warehousename) for w in WarehouseModel.query.all()]
    
    if craftform.validate_on_submit():
        craft = CraftModel.query.filter_by(craftid=craft_id).first()
        if craft and craft.usagestatus=='未使用':
            # 更新字段
            craft.sequenceid = craftform.sequence.data
            craft.storage = craftform.warehouse.data
            craft.alteruser = session.get('username')
            craft.altertime = datetime.now()
            
            try:
                db.session.commit()
                flash('生产工艺信息修改成功', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'修改失败: {str(e)}', 'error')
        else:
            flash('修改失败：工艺使用中或工艺不存在', 'error')
    else:
        # 收集表单验证错误
        error_msgs = []
        for field, errors in craftform.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        flash('表单验证失败: ' + ';'.join(error_msgs), 'error')
        
    # 修改完成后重定向回详情页
    return redirect(url_for('product.processinfo', craft_id=craft_id))

#删除生产工艺信息
@product_bp.route('/deletecraft/<string:craft_id>')
@login_required
@admin_required
def deletecraft(craft_id):
    craft = CraftModel.query.filter_by(craftid=craft_id).first()
    if craft and craft.usagestatus=='未使用':
        try:
            FormulaModel.query.filter_by(craftid=craft_id).delete()
            db.session.delete(craft)
            db.session.commit()
            flash('生产工艺及关联配方已删除', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'删除失败: {str(e)}', 'error')

            return redirect(url_for('product.processinfo', craft_id=craft_id))
    else:
        flash('该工艺使用中或不存在', 'error')

    return redirect(url_for('product.processmanage'))

#更新工艺配方信息(修改/添加)
@product_bp.post('/formula_update')
@login_required
@admin_required
def formula_update():
    try:
        data = request.get_json()
        formula_id = data.get('formula_id')
        craft_id = data.get('craft_id')
        craft = CraftModel.query.filter_by(craftid=craft_id).first()
        if not craft:
            return jsonify({'code': 404, 'msg': '关联工艺未找到，操作失败'})
        if craft.usagestatus == '使用中':
            return jsonify({'code': 400, 'msg': '工艺正在使用中，无法修改配方信息'})
        combination = data.get('combination') # 父级物料编码
        component = data.get('component')     # 子级物料编码
        qty = data.get('qty')

        if not component or not qty or float(qty) <= 0:
            return jsonify({'code': 400, 'msg': '参数不完整或数量无效'})
        
        if component == combination:
             return jsonify({'code': 400, 'msg': '保存失败：不能将物料自身添加为它的配方组件（自引用循环）！'})

        # 1. 循环检测
        # 我们试图建立 combination(父) -> component(子) 的关系
        # 需要检查是否存在 component -> ... -> combination 的反向路径
        if check_circular_dependency(component, combination):
            return jsonify({'code': 400, 'msg': f'保存失败：检测到循环依赖！物料【{component}】的生产结构中已包含了【{combination}】。'})

        # 2. 判断是新增还是更新
        if not formula_id: 
            # --- 新增逻辑 ---
            if not craft_id or not combination:
                 return jsonify({'code': 400, 'msg': '新增配方丢失上下文信息'})

            # 防止重复添加相同的组件
            existing = FormulaModel.query.filter_by(craftid=craft_id, combination=combination, component=component).first()
            if existing:
                return jsonify({'code': 400, 'msg': '该物料已存在于当前配方中'})

            new_id = str(next(gen))
            new_formula = FormulaModel(
                formulaid=new_id,
                craftid=craft_id,
                combination=combination,
                component=component,
                usage=qty,
                altertime=datetime.now(),
                alteruser=session.get('username', 'system')
            )
            db.session.add(new_formula)
            msg = '配方添加成功'
            res_id = new_id
        else:
            # --- 更新逻辑 ---
            formula = FormulaModel.query.filter_by(formulaid=formula_id).first()
            if not formula:
                return jsonify({'code': 404, 'msg': '原配方记录未找到'})
            
            # 检查是否修改了物料，如果修改了，需要检查新物料是否冲突
            if formula.component != component:
                existing = FormulaModel.query.filter_by(craftid=formula.craftid, combination=formula.combination, component=component).first()
                if existing:
                    return jsonify({'code': 400, 'msg': '修改后的物料已存在于列表中'})
            
            formula.component = component
            formula.usage = qty
            formula.altertime = datetime.now()
            formula.alteruser = session.get('username', 'system')
            msg = '配方更新成功'
            res_id = formula_id

        db.session.commit()
        return jsonify({'code': 200, 'msg': msg, 'formula_id': res_id})

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': f'系统错误: {str(e)}'})

# 删除工艺配方信息
@product_bp.post('/formula_delete')
@login_required
@admin_required
def formula_delete():
    try:
        data = request.get_json()
        formula_id = data.get('formula_id')

        if not formula_id:
            return jsonify({'code': 400, 'msg': '参数缺失'})

        formula = FormulaModel.query.filter_by(formulaid=formula_id).first()
        if formula and formula.gcraft.usagestatus == '未使用':
            db.session.delete(formula)
            db.session.commit()
            return jsonify({'code': 200, 'msg': '配方删除成功'})
        else:
            return jsonify({'code': 404, 'msg': '配方不存在或工艺正在使用中'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': f'系统错误: {str(e)}'})

#生产任务创建界面    
@product_bp.route('/taskadd')
@login_required
@admin_required
def taskadd():
    form=AddtaskForm()
    materials = MaterialModel.query.filter_by(materialtype='成品').all()
    materials_json = json.dumps([
        {
            'code': material.materialcode,
            'desc': material.materialdesc,
            'spec': material.specification
        }
        for material in materials
    ], ensure_ascii=False)
    return render_template('taskadd.html',form=form,materials_json=materials_json)

#创建生产任务操作
@product_bp.post('/addtask')
@login_required
@admin_required
def addtask():
    form = AddtaskForm()

    if form.validate_on_submit():
        if TOPModel.query.filter_by(taskcode=form.required.data).first():
            flash(f"创建失败：任务编码【{form.required.data}】已存在，请更换编码后重试。", "error")
            return redirect(url_for('product.taskadd'))

        try:
            # 1. 获取基础数据
            task_code_prefix = form.required.data
            task_name = form.realname.data
            endtime_str = form.endtime.data # mm/dd/yyyy
            
            # 转换时间格式
            try:
                finish_time = datetime.strptime(endtime_str, '%m/%d/%Y')
            except ValueError:
                flash("日期格式错误，请使用 mm/dd/yyyy", "error")
                return redirect(url_for('product.taskadd'))
            
            if finish_time.replace(hour=0, minute=0, second=0, microsecond=0) <= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                flash("计划完成日期不能早于或等于今天", "error")
                return redirect(url_for('product.taskadd'))

            # 2. 获取表格数据 (JSON)
            items_json = form.items_json.data
            if not items_json:
                flash("未检测到生产项数据", "error")
                return redirect(url_for('product.taskadd'))
            
            items_list = json.loads(items_json)
            if not items_list:
                flash("生产项列表为空", "error")
                return redirect(url_for('product.taskadd'))

            current_user = session.get('username')
            now_time = datetime.now()

            # 3. 遍历每一条成品数据，开始创建任务
            for item in items_list:
                material_code = item.get('code')
                qty = float(item.get('qty'))

                check_craft = CraftModel.query.filter_by(materialcode=material_code).first()
                if not check_craft:
                    raise Exception(f"成品【{material_code}】尚未维护生产工艺数据，无法创建任务！")

                task_id = str(next(gen)) # 雪花算法
                
                new_task = TOPModel(
                    taskid=task_id,
                    taskcode=task_code_prefix, # 所属任务编码
                    taskname=task_name,        # 任务名称
                    materialcode=material_code,# 界面表格项的编码
                    quantity=qty,              # 界面表格项的数量
                    taskstatus='新建',
                    starttime=None,
                    finishtime=finish_time,
                    issuer=None,
                    creationtime=now_time,
                    creater=current_user,
                    altertime=now_time,
                    alteruser=current_user
                )
                db.session.add(new_task)

                create_pitem_recursive(task_id, material_code, qty)

            db.session.commit()
            flash(f"生产任务创建成功！共生成 {len(items_list)} 个任务单。", "success")
            return redirect(url_for('product.taskinfo', task_code=task_code_prefix))

        except Exception as e:
            # 5. 失败回滚
            db.session.rollback()
            flash(f"创建失败，系统发生错误：{str(e)}", "error")
            return redirect(url_for('product.taskadd'))

    else:
        error_msgs = []
        for field, errors in form.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        flash("验证失败：" + "; ".join(error_msgs), "error")
        return redirect(url_for('product.taskadd'))

#任务管理界面    
@product_bp.route('/taskmanage')
@login_required
@admin_required
def taskmanage():
    tasks = TOPModel.query.all()
    return render_template('taskmanage.html',tasks=tasks)

#生产任务详情界面
@product_bp.route('/taskinfo/<string:task_code>')
@login_required
@admin_required
def taskinfo(task_code):
    form=AltertaskForm()
    task = TOPModel.query.filter_by(taskcode=task_code).first()
    if not task:
        return render_template_string("""
                <script>
                    alert('该生产任务不存在！');
                    window.history.back();
                </script>
            """)
    
    form.required.data = task.taskcode
    form.realname.data = task.taskname
    form.endtime.data = task.finishtime.strftime('%m/%d/%Y')
    
    materials = MaterialModel.query.filter_by(materialtype='成品').all()
    materials_json = json.dumps([
        {
            'code': material.materialcode,
            'desc': material.materialdesc,
            'spec': material.specification
        }
        for material in materials
    ], ensure_ascii=False)
    initialItems = TOPModel.query.filter_by(taskcode=task_code).all()
    return render_template('taskinfo.html', task=task,form=form,materials_json=materials_json,initialItems=initialItems)

#修改生产任务操作
@product_bp.post('/altertask')
@login_required
@admin_required
def altertask():
    form = AltertaskForm()

    if form.validate_on_submit():
        try:
            # 1. 解包数据
            task_code = form.required.data
            task_name = form.realname.data
            endtime_str = form.endtime.data
            items_json = form.items_json.data
            check_task = TOPModel.query.filter_by(taskcode=task_code).all()
            if not check_task:
                raise Exception(f"任务【{task_code}】不存在，无法修改！")
            if any(t.taskstatus != '新建' for t in check_task):
                raise Exception(f"任务【{task_code}】当前状态不为【新建】，不允许修改！")
            
            try:
                finish_time = datetime.strptime(endtime_str, '%m/%d/%Y')
            except ValueError:
                finish_time = datetime.strptime(endtime_str, '%Y-%m-%d')

            if finish_time.replace(hour=0, minute=0, second=0, microsecond=0) <= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                raise Exception("修改失败：计划完成日期不能早于或等于今天")
            
            items_list = json.loads(items_json) if items_json else []

            if not items_list:
                flash("生产项不能为空，请使用删除功能。", "error")
                return redirect(url_for('product.taskinfo', task_code=task_code))

            # 2. 查询现有数据，构建 {taskid: obj} 字典
            current_tasks = TOPModel.query.filter_by(taskcode=task_code).all()
            current_task_map = {t.taskid: t for t in current_tasks}

            # 3. 同步表头信息
            for task in current_tasks:
                task.taskname = task_name
                task.finishtime = finish_time
                task.altertime = datetime.now()
                task.alteruser = session.get('username')

            submitted_ids = [item.get('taskid') for item in items_list if item.get('taskid')]

            # 4. 【删除逻辑】：前端没传回来的 ID 视为删除
            for taskid, task_obj in current_task_map.items():
                if taskid not in submitted_ids:
                    # 级联删除 GPItem
                    db.session.delete(task_obj)

            # 5. 【更新与新增逻辑】
            for item in items_list:
                item_taskid = item.get('taskid')
                material_code = item.get('code')
                qty = float(item.get('qty'))
                
                # A. 更新
                if item_taskid and item_taskid in current_task_map:
                    existing_task = current_task_map[item_taskid]
                    
                    code_changed = existing_task.materialcode != material_code
                    qty_changed = float(existing_task.quantity) != qty

                    if code_changed or qty_changed:
                        # 核心修改逻辑：先清除旧 GPItem，再更新 GTOP，最后重新递归生成新的 GPItem
                        PItemModel.query.filter_by(taskid=item_taskid).delete()
                        
                        existing_task.materialcode = material_code
                        existing_task.quantity = qty
                        
                        # 校验工艺是否存在 (如果是改了物料)
                        if code_changed and not CraftModel.query.filter_by(materialcode=material_code).first():
                             raise Exception(f"保存失败：物料【{material_code}】未维护生产工艺")

                        create_pitem_recursive(item_taskid, material_code, qty)

                # B. 新增
                else:
                    if not CraftModel.query.filter_by(materialcode=material_code).first():
                        raise Exception(f"保存失败：新增物料【{material_code}】未维护生产工艺")
                    
                    new_id = str(next(gen))
                    new_task = TOPModel(
                        taskid=new_id,
                        taskcode=task_code,
                        taskname=task_name,
                        materialcode=material_code,
                        quantity=qty,
                        taskstatus='新建',
                        starttime=None,
                        finishtime=finish_time,
                        issuer=None,
                        creationtime=datetime.now(),
                        creater=session.get('username'),
                        altertime=datetime.now(),
                        alteruser=session.get('username')
                    )
                    db.session.add(new_task)
                    create_pitem_recursive(new_id, material_code, qty)

            db.session.commit()
            flash("保存修改成功！", "success")
            return redirect(url_for('product.taskinfo', task_code=task_code))

        except Exception as e:
            db.session.rollback()
            flash(f"保存失败: {str(e)}", "error")
            return redirect(url_for('product.taskinfo', task_code=form.required.data))
    
    else:
        # 表单验证失败 (如日期格式不对)
        flash(f"验证失败：{form.errors}", "error")
        return redirect(url_for('product.taskmanage'))

#删除生产任务操作
@product_bp.route('/deletetask/<string:task_code>')
@login_required
@admin_required
def deletetask(task_code):
    try:
        tasks = TOPModel.query.filter_by(taskcode=task_code).all()
        if not tasks:
            flash("该任务不存在或已被删除", "error")
            return redirect(url_for('product.taskmanage'))
        if any(t.taskstatus != '新建' for t in tasks):
            flash("只能删除状态为【新建】的任务！", "error")
            return redirect(url_for('product.taskinfo', task_code=task_code))
        
        count = len(tasks)
        for task in tasks:
            db.session.delete(task)
            
        db.session.commit()
        flash(f"已删除任务【{task_code}】（共清除 {count} 条任务单）。", "success")
        return redirect(url_for('product.taskmanage'))

    except Exception as e:
        db.session.rollback()
        flash(f"删除失败: {str(e)}", "error")
        return redirect(url_for('product.taskinfo', task_code=task_code))

# 获取任务单的生产项列表（AJAX）    
@product_bp.route('/get_task_items/<string:task_id>')
@login_required
@admin_required
def get_task_items(task_id):
    """获取指定任务单的所有生产项"""
    items = PItemModel.query.filter_by(taskid=task_id).all()
    items_data = []
    for item in items:
        gmaterial = MaterialModel.query.filter_by(materialcode=item.materialcode).first()
        gsequence = SequenceModel.query.filter_by(sequenceid=item.sequenceid).first()
        
        items_data.append({
            'itemid': item.itemid,
            'materialcode': item.materialcode,
            'materialdesc': gmaterial.materialdesc if gmaterial else '',
            'specification': gmaterial.specification if gmaterial else '',
            'sequencename': gsequence.sequencename if gsequence else item.sequenceid,
            'quantity': float(item.quantity)
        })
    return jsonify({'code': 200, 'data': items_data})

#更新生产项数量
@product_bp.post('/update_task_item')
@login_required
@admin_required
def update_task_item():
    try:
        data = request.json
        item_id = data.get('itemid')
        new_qty = data.get('quantity')
        
        if not item_id or new_qty is None:
             return jsonify({'code': 400, 'msg': '参数缺失'})
             
        item = PItemModel.query.filter_by(itemid=item_id).first()
        if not item:
            return jsonify({'code': 404, 'msg': '生产项不存在'})

        if item.gtop.taskstatus != '新建':
            return jsonify({'code': 403, 'msg': '当前任务状态不允许修改生产项'})
            
        item.quantity = float(new_qty)

        db.session.commit()
        return jsonify({'code': 200, 'msg': '更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)})

#删除生产项
@product_bp.post('/delete_task_item')
@login_required
@admin_required
def delete_task_item():
    try:
        data = request.json
        item_id = data.get('itemid')
        
        item = PItemModel.query.filter_by(itemid=item_id).first()
        if not item:
            return jsonify({'code': 404, 'msg': '生产项不存在'})
        if item.gtop.taskstatus != '新建':
             return jsonify({'code': 403, 'msg': '当前任务状态不允许删除生产项'})
            
        db.session.delete(item)
        db.session.commit()
        return jsonify({'code': 200, 'msg': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)})