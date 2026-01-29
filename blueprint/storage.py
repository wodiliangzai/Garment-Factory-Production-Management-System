from flask import Blueprint,render_template,jsonify,redirect,url_for,session,request,render_template_string,flash
from datetime import datetime
import string
from exts import db
from models import WarehouseModel,InventoryModel,ReceiptModel,SequenceModel,CharacterModel
from forms import AddwarehouseForm,AlterwarehouseForm,AddsequenceForm,AltersequenceForm
from decorators import login_required,admin_required

storage_bp=Blueprint('storage',__name__,url_prefix='/storage')

@storage_bp.route('/warehouses')
@login_required
def warehouses():
    warehouses = WarehouseModel.query.all()
    addwarehouseform=AddwarehouseForm()
    alterwarehouseform=AlterwarehouseForm()
    return render_template('warehouse.html',warehouses=warehouses,addwarehouseform=addwarehouseform,alterwarehouseform=alterwarehouseform)

@storage_bp.post('/addwarehouse')
@login_required
@admin_required
def addwarehouse():
    addwarehouseform=AddwarehouseForm()
    if addwarehouseform.validate():
        data = addwarehouseform.data
        if WarehouseModel.query.filter_by(warehousecode=data['required']).first():
            flash("添加失败：仓库代码已存在", "error")
            return redirect(url_for('storage.warehouses'))
        
        new_warehouse = WarehouseModel(
            warehousecode=data['required'],
            warehousename=data['realname'],
            creationtime=datetime.now(),
            creater=session['username'], 
            altertime=datetime.now(),
            alteruser=session['username']
        )
        db.session.add(new_warehouse)
        db.session.commit()
        flash("仓库添加成功", "success")
        return redirect(url_for('storage.warehouses'))
    else:
        error_msgs = []
        for field, errors in addwarehouseform.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        flash("仓库添加失败："+ "; ".join(error_msgs), "error")
        return redirect(url_for('storage.warehouses'))
    
@storage_bp.post('/alterwarehouse/<string:role_code>')
@login_required
@admin_required
def alterwarehouse(role_code):
    alterwarehouseform=AlterwarehouseForm()
    if alterwarehouseform.validate():
        data = alterwarehouseform.data
        warehouse = WarehouseModel.query.filter_by(warehousecode=role_code).first()
        if warehouse:
            # 检查名称是否重复（排除自身）
            if data['role_name'] != warehouse.warehousename and WarehouseModel.query.filter_by(warehousename=data['role_name']).first():
                return jsonify({'code':500,'msg':'仓库名称已存在，修改失败'})
            
            warehouse.warehousename = data['role_name']
            warehouse.altertime = datetime.now()
            warehouse.alteruser = session.get('username')
            db.session.commit()
            return jsonify({'code':200,'msg':'仓库修改成功'})
        else:
            return jsonify({'code':500,'msg':'仓库已不存在，修改失败'})
    else:
        error_msgs = []
        for field, errors in alterwarehouseform.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        return jsonify({"code": 400, "msg": "; ".join(error_msgs)})

@storage_bp.route('/inventory')
@login_required
def inventory():
    inventorie_item = InventoryModel.query.all()
    return render_template('inventory.html',inventorie_item=inventorie_item)

@storage_bp.route('/receipt')
@login_required
def receipt():
    receipt_items = ReceiptModel.query.all()
    warehouses = WarehouseModel.query.all()
    return render_template('receipt.html',receipt_items=receipt_items,warehouses=warehouses)

@storage_bp.post('/process_receipt')
@login_required
def process_receipt():
    data = request.get_json()
    receipt_ids = data.get('receipt_ids', [])
    warehouse_code = data.get('warehouse_code')

    if not receipt_ids or not warehouse_code:
        return jsonify({'code': 400, 'msg': '参数错误'})

    try:
        # 开启事务处理
        # 使用 with_for_update() 加上排他锁，防止并发问题
        items = ReceiptModel.query.filter(ReceiptModel.receiptid.in_(receipt_ids)).with_for_update().all()        
        # 1. 校验：判断是否包含已接收的数据
        for item in items:
            if item.status != '待接收':
                # 只要有一条不是待接收，直接回滚（虽然还没改数据，但逻辑上终止）
                return jsonify({'code': 400, 'msg': '入库失败：存在已接收的物料数据'})

        current_time = datetime.now()
        # 2. 执行入库操作
        for item in items:
            # 更新 ReceiptModel 状态
            item.status = '已接收'
            item.warehousecode = warehouse_code
            item.receiptdate = current_time

            # 更新 InventoryModel 库存
            # 查询该仓库下该物料是否存在
            inventory = InventoryModel.query.filter_by(
                warehousecode=warehouse_code, 
                materialcode=item.materialcode
            ).with_for_update().first()

            if inventory:
                # 存在则增加数量
                inventory.quantity += item.quantity
                inventory.altertime = current_time
            else:
                # 不存在则新增记录
                new_inventory = InventoryModel(
                    materialcode=item.materialcode,
                    warehousecode=warehouse_code,
                    quantity=item.quantity,
                    altertime=current_time
                )
                db.session.add(new_inventory)

        db.session.commit()
        return jsonify({'code': 200, 'msg': '入库成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': f'系统错误: {str(e)}'})
    
@storage_bp.route('/sequence')
@login_required
def sequence():
    sequences = SequenceModel.query.all()
    addsequenceform=AddsequenceForm()
    addsequenceform.role.choices=[('', '请选择负责角色')] + [(c.charactercode, c.charactername) for c in CharacterModel.query.all()]
    altersequenceform=AltersequenceForm()
    altersequenceform.role.choices=[(c.charactercode, c.charactername) for c in CharacterModel.query.all()] 
    return render_template('sequence.html',sequences=sequences,addsequenceform=addsequenceform,altersequenceform=altersequenceform)

@storage_bp.post('/addsequence')
@login_required
@admin_required
def addsequence():
    addsequenceform=AddsequenceForm()
    addsequenceform.role.choices=[('', '请选择负责角色')] + [(c.charactercode, c.charactername) for c in CharacterModel.query.all()]

    if addsequenceform.validate():
        data = addsequenceform.data
        if SequenceModel.query.filter_by(sequenceid=data['required']).first():
            flash("添加失败：工序编码已存在", "error")
            return redirect(url_for('storage.sequence'))
        
        new_sequence = SequenceModel(
            sequenceid=data['required'],
            sequencename=data['realname'],
            charactercode=data['role'], 
            creationtime=datetime.now(),
            creater=session.get('username'), 
            altertime=datetime.now(),
            alteruser=session.get('username')
        )
        db.session.add(new_sequence)
        db.session.commit()
        flash("工序添加成功", "success")
        return redirect(url_for('storage.sequence'))
    else:
        error_msgs = []
        for field, errors in addsequenceform.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        flash("添加失败："+ "; ".join(error_msgs), "error")
        return redirect(url_for('storage.sequence'))

@storage_bp.post('/altersequence/<string:role_code>')
@login_required
@admin_required
def altersequence(role_code):
    altersequenceform=AltersequenceForm()
    altersequenceform.role.choices=[(c.charactercode, c.charactername) for c in CharacterModel.query.all()]

    if altersequenceform.validate():
        data = altersequenceform.data
        sequence = SequenceModel.query.filter_by(sequenceid=role_code).first()
        if sequence:
            sequence.sequencename = data['role_name']
            sequence.charactercode = data['role'] # 更新角色代码
            sequence.altertime = datetime.now()
            sequence.alteruser = session.get('username')
            
            try:
                db.session.commit()
                return jsonify({'code':200,'msg':'工序修改成功'})
            except Exception as e:
                db.session.rollback()
                return jsonify({'code':500,'msg':f'数据库错误: {str(e)}'})
        else:
            return jsonify({'code':500,'msg':'工序已不存在，修改失败'})
    else:
        error_msgs = []
        for field, errors in altersequenceform.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        return jsonify({"code": 400, "msg": "; ".join(error_msgs)})