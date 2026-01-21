from flask import Blueprint,render_template,jsonify,redirect,url_for,session,request,render_template_string,flash,json
from datetime import datetime
import string
from exts import db
from models import MaterialModel,CraftModel,FormulaModel,CharacterModel,WarehouseModel
from forms import AddmaterialForm,AltermaterialForm,CraftForm,AddcraftForm
from snowflake import SnowflakeGenerator

# 初始化雪花算法生成器 (ID=1，避免与采购模块冲突)
gen = SnowflakeGenerator(1)

product_bp=Blueprint('product',__name__,url_prefix='/product')

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


@product_bp.route('/materialmanage')
def materialmanage():
    materials = MaterialModel.query.all()
    addmaterialform=AddmaterialForm()
    altermaterialform=AltermaterialForm()
    return render_template('materialmanage.html',materials=materials,addmaterialform=addmaterialform,altermaterialform=altermaterialform)

@product_bp.post('/addmaterial')
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
    
@product_bp.post('/altermaterial/<string:role_code>')
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
    
@product_bp.route('/processmanage')
def processmanage():
    addcraftform=AddcraftForm()
    addcraftform.materialcode.choices =[('', '请选择物料编码')] + [(m.materialcode, f"{m.materialcode} - {m.materialdesc} - {m.specification}") for m in MaterialModel.query.all()]
    addcraftform.department.choices =[('', '请选择负责部门')] + [(c.charactercode, c.charactername) for c in CharacterModel.query.all()]
    addcraftform.warehouse.choices =[('', '请选择完成存放仓库')] + [(w.warehousecode, w.warehousename) for w in WarehouseModel.query.all()]
    crafts = CraftModel.query.all()
    return render_template('processmanage.html',crafts=crafts, addcraftform=addcraftform)

@product_bp.post('/addcraft')
def addcraft():
    addcraftform=AddcraftForm()
    # 关键：必须重新填充 SelectField 的 choices，否则 WTForms 会因为提交的值不在 choices 列表中而校验失败
    addcraftform.materialcode.choices =[('', '请选择物料编码')] + [(m.materialcode, f"{m.materialcode} - {m.materialdesc} - {m.specification}") for m in MaterialModel.query.all()]
    addcraftform.department.choices =[('', '请选择负责部门')] + [(c.charactercode, c.charactername) for c in CharacterModel.query.all()]
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
                department=addcraftform.department.data,
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

@product_bp.route('/processinfo/<string:craft_id>')
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
    craftform.department.choices = [(c.charactercode, c.charactername) for c in CharacterModel.query.all()]
    craftform.warehouse.choices = [(w.warehousecode, w.warehousename) for w in WarehouseModel.query.all()]
    craftform.department.default = craft.department
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
    return render_template('processinfo.html', craft_id=craft_id, craftform=craftform, recipe_tree=recipe_tree,materials_json=materials_json)

@product_bp.route('/updatecraft/<string:craft_id>', methods=['POST'])
def updatecraft(craft_id):
    craftform = CraftForm()
    # 必须重新填充 SelectField 的 choices，否则验证会失败
    craftform.department.choices = [(c.charactercode, c.charactername) for c in CharacterModel.query.all()]
    craftform.warehouse.choices = [(w.warehousecode, w.warehousename) for w in WarehouseModel.query.all()]
    
    if craftform.validate_on_submit():
        craft = CraftModel.query.filter_by(craftid=craft_id).first()
        if craft:
            # 更新字段
            craft.department = craftform.department.data
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
            flash('修改失败：工艺记录不存在', 'error')
    else:
        # 收集表单验证错误
        error_msgs = []
        for field, errors in craftform.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        flash('表单验证失败: ' + ';'.join(error_msgs), 'error')
        
    # 修改完成后重定向回详情页
    return redirect(url_for('product.processinfo', craft_id=craft_id))

@product_bp.route('/deletecraft/<string:craft_id>')
def deletecraft(craft_id):
    craft = CraftModel.query.filter_by(craftid=craft_id).first()
    if craft:
        try:
            # 先删除关联的配方行（防止外键约束报错）
            FormulaModel.query.filter_by(craftid=craft_id).delete()
            # 删除工艺头信息
            db.session.delete(craft)
            db.session.commit()
            flash('生产工艺及关联配方已删除', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'删除失败: {str(e)}', 'error')
            # 如果出错，停留在详情页以便查看问题
            return redirect(url_for('product.processinfo', craft_id=craft_id))
    else:
        flash('该工艺不存在', 'error')
        
    # 删除成功后跳转到管理列表页
    return redirect(url_for('product.processmanage'))

@product_bp.post('/formula_update')
def formula_update():
    try:
        data = request.get_json()
        formula_id = data.get('formula_id')
        craft_id = data.get('craft_id')       # 当前页面的工艺ID
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

# 删除配方行
@product_bp.post('/formula_delete')
def formula_delete():
    try:
        data = request.get_json()
        formula_id = data.get('formula_id')

        if not formula_id:
            return jsonify({'code': 400, 'msg': '参数缺失'})

        formula = FormulaModel.query.filter_by(formulaid=formula_id).first()
        if formula:
            db.session.delete(formula)
            db.session.commit()
            return jsonify({'code': 200, 'msg': '配方删除成功'})
        else:
            return jsonify({'code': 404, 'msg': '配方不存在或已被删除'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': f'系统错误: {str(e)}'})