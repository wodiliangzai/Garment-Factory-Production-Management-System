from flask import Blueprint, render_template, json, jsonify, redirect, url_for, session, request, render_template_string, flash, current_app
from datetime import datetime
import string
import os
import qrcode
from exts import db
from models import UserModel, CharacterModel, PermissionModel, MaterialModel, WarehouseModel, InventoryModel, SequenceModel, CraftModel, FormulaModel, TOPModel, PItemModel, PReportModel
from sqlalchemy import text, func
from snowflake import SnowflakeGenerator
from decorators import login_required,admin_required

gen = SnowflakeGenerator(2)

taskmodule_bp = Blueprint('taskmodule', __name__, url_prefix='/taskmodule')

@taskmodule_bp.route('/release_tasks', methods=['POST'])
@login_required
@admin_required
def release_tasks():
    try:
        data = request.json
        task_codes = data.get('task_codes', [])

        if not task_codes:
            return jsonify({'code': 400, 'msg': '未选择任何任务'})

        # 1. 查找所有涉及的任务单
        tasks = TOPModel.query.filter(TOPModel.taskcode.in_(task_codes), TOPModel.taskstatus == '新建').all()
        
        if not tasks:
            return jsonify({'code': 400, 'msg': '未找到符合下达条件的任务'})

        count_tasks = 0
        count_items = 0

        # 二维码保存路径
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        static_files_dir = os.path.join(base_path, 'static', 'files')
        if not os.path.exists(static_files_dir):
            os.makedirs(static_files_dir)

        for task in tasks:
            # 更新任务状态
            task.taskstatus = '进行中'
            task.altertime = datetime.now()
            task.alteruser = session.get('username')
            count_tasks += 1

            # 2. 查找关联的任务生产项
            pitems = PItemModel.query.filter_by(taskid=task.taskid).all()
            for item in pitems:
                # 3. 更新工艺状态
                if item.craftid:
                    craft = CraftModel.query.filter_by(craftid=item.craftid).first()
                    if craft:
                        craft.usagestatus = '使用中'
                
                # 4. 生成二维码
                # 二维码内容为报产页面的URL
                report_url = url_for('taskmodule.report_page', item_id=item.itemid, _external=True)
                
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(report_url)
                qr.make(fit=True)
                img = qr.make_image(fill='black', back_color='white')
                
                # 文件名：itemid.png
                filename = f"{item.itemid}.png"
                file_path = os.path.join(static_files_dir, filename)
                img.save(file_path)

                # 保存相对路径到数据库 (static/files/xxx.png)
                # 注意：数据库存的是相对 static 的路径或者 web 访问路径
                item.itemqr = f"static/files/{filename}"
                count_items += 1

        db.session.commit()
        return jsonify({'code': 200, 'msg': f'下达成功！已更新 {count_tasks} 个任务单，生成 {count_items} 个生产项二维码。'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': f'系统错误: {str(e)}'})

@taskmodule_bp.route('/report_page/<string:item_id>')
def report_page(item_id):
    """
    移动端报产页面
    不需要 @login_required，因为是扫码进入，无法保持 session
    """
    pitem = PItemModel.query.filter_by(itemid=item_id).first()
    if not pitem:
        return "无效的二维码或生产项不存在", 404

    # 获取关联信息用于展示
    task_info = TOPModel.query.filter_by(taskid=pitem.taskid).first()
    material_info = MaterialModel.query.filter_by(materialcode=pitem.materialcode).first()
    sequence_info = SequenceModel.query.filter_by(sequenceid=pitem.sequenceid).first()

    # 获取负责该工序的所有用户
    # 逻辑：Item -> Sequence -> Character -> Permission -> User
    # 注意：PermissionModel 中 username 是外键指向 User
    users = []
    if sequence_info:
        permissions = PermissionModel.query.filter_by(charactercode=sequence_info.charactercode).all()
        for perm in permissions:
            user = UserModel.query.filter_by(username=perm.username).first()
            if user:
                users.append(user)

    return render_template('mobile_report.html', 
                           pitem=pitem, 
                           task=task_info, 
                           material=material_info, 
                           sequence=sequence_info,
                           users=users)

@taskmodule_bp.post('/submit_report')
def submit_report():
    try:
        data = request.json
        item_id = data.get('itemid')
        username = data.get('username')
        
        # 获取前端传来的两个数量
        real_quantity_str = data.get('real_quantity')      # 实际产量
        planned_quantity_str = data.get('planned_quantity') # 计划产量（用于扣料）

        if not item_id or not username or not real_quantity_str or not planned_quantity_str:
            return jsonify({'code': 400, 'msg': '请填写完整信息'})

        try:
            real_qty = float(real_quantity_str)
            planned_qty = float(planned_quantity_str)
            if real_qty <= 0 or planned_qty <= 0:
                raise ValueError
        except ValueError:
            return jsonify({'code': 400, 'msg': '报产数量必须为正数'})

        pitem = PItemModel.query.filter_by(itemid=item_id).first()
        if not pitem:
            return jsonify({'code': 404, 'msg': '生产项不存在'})

        # 1. 工艺与库存校验逻辑
        craft = CraftModel.query.filter_by(craftid=pitem.craftid).first()
        if not craft:
             return jsonify({'code': 500, 'msg': '该生产项未关联有效工艺，无法计算消耗'})

        formulas = FormulaModel.query.filter_by(craftid=craft.craftid).all()
        
        # 记录缺少的物料
        missing_materials = []

        for formula in formulas:
            # 修改点：计算所需消耗量 = 计划产量(planned_qty) * 单位用量
            # 无论是否有损耗，都按照投入的计划量来扣减原材料
            needed_qty = planned_qty * float(formula.usage)
            component_code = formula.component
            
            # 查询当前库存总量 (跨仓库总和)
            total_stock = db.session.query(func.sum(InventoryModel.quantity)).filter_by(materialcode=component_code).scalar()
            total_stock = float(total_stock) if total_stock else 0.0

            if total_stock < needed_qty:
                mat = MaterialModel.query.filter_by(materialcode=component_code).first()
                mat_name = mat.materialdesc if mat else component_code
                missing_materials.append(f"{mat_name} (缺 {needed_qty - total_stock:.6f})")

        if missing_materials:
            return jsonify({'code': 400, 'msg': f'报产失败，原料库存不足：\n' + '；\n'.join(missing_materials)})

        # 2. 执行库存扣减 (这里执行实际的 update 操作)
        for formula in formulas:
            # 修改点：使用 planned_qty 进行扣减
            deduct_needed = planned_qty * float(formula.usage)
            component_code = formula.component
            
            # 查找该物料所有有库存的记录 (默认按数据库顺序)
            inventories = InventoryModel.query.filter_by(materialcode=component_code).filter(InventoryModel.quantity > 0).all()
            
            for inv in inventories:
                if deduct_needed <= 0:
                    break
                    
                current_qty = float(inv.quantity)
                if current_qty >= deduct_needed:
                    # 当前仓库够扣
                    inv.quantity = current_qty - deduct_needed
                    inv.altertime = datetime.now()
                    deduct_needed = 0
                else:
                    # 当前仓库不够，扣完当前仓库，继续下一个
                    inv.quantity = 0
                    inv.altertime = datetime.now()
                    deduct_needed -= current_qty

        # 3. 生成报产记录
        report_id = str(next(gen))
        
        new_report = PReportModel(
            reportid=report_id,
            itemid=item_id,
            reporter=username, 
            reportquantity=planned_qty, # 存入计划产量
            realquantity=real_qty,      # 存入实际产量
            reporttime=datetime.now(),
            reviewstatus='待审核',
            reviewer=None,
            reviewtime=None,
            comments=None
        )
        
        db.session.add(new_report)
        db.session.commit()

        # 如果有较大损耗，在返回消息中提示一下
        loss_msg = ""
        if planned_qty > real_qty:
            loss_msg = f" (含损耗 {planned_qty - real_qty:.2f})"

        return jsonify({'code': 200, 'msg': f'报产成功！实际产出 {real_qty}，{loss_msg}'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': '系统异常：' + str(e)})


@taskmodule_bp.route('/progress')
@login_required
def progress():
    items = PItemModel.query.join(PItemModel.gtop).filter(TOPModel.taskstatus == '进行中')
    if(session['charactercode']!='GAdmin'):
        items=items.join(PItemModel.gsequence).filter(SequenceModel.charactercode==session['charactercode'])
    return render_template('progress.html', items=items.all())


@taskmodule_bp.route('/reportingreview')
@login_required
def reportingreview():
    items= PReportModel.query.filter(PReportModel.reviewstatus=='待审核')
    if(session['charactercode']!='GAdmin'):
        items=items.join(PReportModel.gpitem).join(PItemModel.gsequence).filter(SequenceModel.charactercode==session['charactercode'])
    return render_template('reportingreview.html', items=items.all())

@taskmodule_bp.post('/reject_report')
@login_required
def reject_report():
    try:
        data = request.json
        report_id = data.get('reportid')
        reason = data.get('reason')

        if not report_id or not reason:
            return jsonify({'code': 400, 'msg': '参数不完整'})

        report = PReportModel.query.filter_by(reportid=report_id).first()
        if not report:
            return jsonify({'code': 404, 'msg': '未找到该报产记录'})
        
        if report.reviewstatus != '待审核':
             return jsonify({'code': 400, 'msg': '该记录并非待审核状态，无法驳回'})

        # 1. 查找关联信息用于库存回退
        pitem = PItemModel.query.filter_by(itemid=report.itemid).first()
        if not pitem:
            return jsonify({'code': 500, 'msg': '关联生产项丢失'})

        craft = CraftModel.query.filter_by(craftid=pitem.craftid).first()
        if not craft:
            return jsonify({'code': 500, 'msg': '关联工艺丢失'}) # 如果没有工艺，不知道退到哪个仓库

        # 2. 获取配方并执行库存回补
        formulas = FormulaModel.query.filter_by(craftid=craft.craftid).all()
        target_warehouse_code = craft.storage # 退回到工艺指定的仓库

        for formula in formulas:
            # 计算应退还数量 = 计划产量 * 配方单位用量
            # 注意：报产时扣减的是 planned_qty (即report.reportquantity) 对应的原料
            return_qty = float(report.reportquantity) * float(formula.usage)
            component_code = formula.component

            # 查询目标仓库的库存记录
            inventory = InventoryModel.query.filter_by(
                materialcode=component_code, 
                warehousecode=target_warehouse_code
            ).first()

            blurred_inventory=InventoryModel.query.filter_by(materialcode=component_code).first()

            if inventory:
                # 原有库存记录，直接累加
                inventory.quantity = float(inventory.quantity) + return_qty
                inventory.altertime = datetime.now()
            elif blurred_inventory:
                # 没有该仓库的库存记录，但有该物料的库存记录，说明之前没有在这个工艺指定的仓库存过这种物料。
                blurred_inventory.quantity = float(blurred_inventory.quantity) + return_qty
                blurred_inventory.altertime = datetime.now()
            else:
                # 理论上应该有记录（即使是0），如果不存在记录，则新建一条
                new_inv = InventoryModel(
                    materialcode=component_code,
                    warehousecode=target_warehouse_code,
                    quantity=return_qty,
                    altertime=datetime.now()
                )
                db.session.add(new_inv)

        # 3. 更新报产记录状态
        report.reviewstatus = '不通过'
        report.comments = reason
        report.reviewer = session.get('username')
        report.reviewtime = datetime.now()

        db.session.commit()
        return jsonify({'code': 200, 'msg': '驳回成功，原料库存已回退'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': f'系统错误: {str(e)}'})
    
@taskmodule_bp.post('/approve_reports')
@login_required
def approve_reports():
    try:
        data = request.json
        # 获取前端传来的 ID 列表
        report_ids = data.get('report_ids', [])
        
        if not report_ids:
            return jsonify({'code': 400, 'msg': '未选择任何记录'})

        # 查找所有选中的且状态为待审核的记录
        reports = PReportModel.query.filter(PReportModel.reportid.in_(report_ids), PReportModel.reviewstatus == '待审核').all()
        
        if not reports:
            return jsonify({'code': 400, 'msg': '未找到有效的待审核记录'})

        count_success = 0
        username = session.get('username')
        current_time = datetime.now()

        for report in reports:
            # 1. 更新对应任务生产项(PItem)的完成数量
            pitem = PItemModel.query.filter_by(itemid=report.itemid).first()
            if pitem:
                # 累加实际产量到生产项的完成数量中
                # 确保转换为float进行计算，SQLAlchemy会自动处理类型映射
                current_completed = float(pitem.completed) if pitem.completed else 0.0
                added_quantity = float(report.realquantity)
                pitem.completed = current_completed + added_quantity

            # 2. 更新报产记录状态
            report.reviewstatus = '已审核'
            report.comments = '通过'
            report.reviewer = username
            report.reviewtime = current_time
            
            count_success += 1

        db.session.commit()
        
        # Flask flash 消息，前端 base.html 中会自动渲染显示
        flash(f'操作成功！共审核通过 {count_success} 条报产记录。', 'success')
        
        return jsonify({'code': 200, 'msg': '审核成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': f'系统错误: {str(e)}'})