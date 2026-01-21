from flask import Blueprint,render_template,json,jsonify,redirect,url_for,session,request,render_template_string,flash
from datetime import datetime
import string
from exts import db
from models import UserModel,SupplierModel,MaterialModel,PRHeaderModel,PRLineModel,POHeaderModel,POLineModel,ReceiptModel
from forms import AddsupplierForm,AltersupplierForm
from sqlalchemy import text
from snowflake import SnowflakeGenerator

gen = SnowflakeGenerator(0)

procurement_bp=Blueprint('procurement',__name__,url_prefix='/procurement')

@procurement_bp.route('/suppliermanage')
def suppliermanage():
    suppliers = SupplierModel.query.all()
    addsupplierform=AddsupplierForm()
    altersupplierform=AltersupplierForm()
    return render_template('suppliermanage.html',suppliers=suppliers,addsupplierform=addsupplierform,altersupplierform=altersupplierform)

@procurement_bp.post('/addsupplier')
def addsupplier():
    addsupplierform=AddsupplierForm()
    if addsupplierform.validate():
        data = addsupplierform.data
        if SupplierModel.query.filter_by(suppliercode=data['required']).first() or SupplierModel.query.filter_by(suppliername=data['realname']).first():
            flash("添加失败：供应商代码或供应商名称已存在", "error") # 使用 flash 消息
            return redirect(url_for('procurement.suppliermanage'))
        
        new_supplier = SupplierModel(
            suppliercode=data['required'],
            suppliername=data['realname'],
            supplieraddress=data['description'],
            creationtime=datetime.now(),
            altertime=datetime.now()
        )
        db.session.add(new_supplier)
        db.session.commit()
        flash("供应商添加成功", "success")
        return redirect(url_for('procurement.suppliermanage'))
    else:
        error_msgs = []
        for field, errors in addsupplierform.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        flash("供应商添加失败："+ "; ".join(error_msgs), "error")
        return redirect(url_for('procurement.suppliermanage'))

@procurement_bp.post('/altersupplier/<string:role_code>')
def altersupplier(role_code):
    altersupplierform=AltersupplierForm()
    if altersupplierform.validate():
        data = altersupplierform.data
        supplier = SupplierModel.query.filter_by(suppliercode=role_code).first()
        if supplier:
            if data['role_name']!=supplier.suppliername and SupplierModel.query.filter_by(suppliername=data['role_name']).first():
                return jsonify({'code':500,'msg':'供应商名称已存在，修改失败'})
            supplier.suppliername = data['role_name']
            supplier.supplieraddress = data['role_desc']
            supplier.altertime = datetime.now()
            db.session.commit()
            return jsonify({'code':200,'msg':'供应商修改成功'})
        else:
            return jsonify({'code':500,'msg':'供应商已不存在，修改失败'})
    else:
        error_msgs = []
        for field, errors in altersupplierform.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        return jsonify({"code": 400, "msg": "; ".join(error_msgs)})
    
@procurement_bp.route('/prmanage')
def prmanage():
    prlines=PRLineModel.query.all()
    return render_template('prmanage.html',prlines=prlines)

@procurement_bp.route('/pradd')
def pradd():
    username=session.get('username')
    user=UserModel.query.filter_by(username=username).first()
    realname=user.realname
    email=user.email
    suppliers = SupplierModel.query.all()
    suppliers_json = json.dumps([
        {
            'code': supplier.suppliercode,
            'name': supplier.suppliername
        }
        for supplier in suppliers
    ], ensure_ascii=False)
    materials = MaterialModel.query.all()
    materials_json = json.dumps([
        {
            'code': material.materialcode,
            'desc': material.materialdesc,
            'spec': material.specification
        }
        for material in materials
    ], ensure_ascii=False)
    return render_template('pradd.html',username=username,realname=realname,email=email,suppliers_json=suppliers_json,materials_json=materials_json)

@procurement_bp.post('/submit_pr')
def submit_pr():
    try:
        # 1. 获取前端 JSON 数据
        data = request.get_json()
        supplier_code = data.get('supplier_code')
        reason = data.get('reason')
        items = data.get('items')        
        applicant = session.get('username')

        if not supplier_code or not reason or not items:
            return jsonify({'code': 400, 'msg': '数据不完整'})

        sql = text("""
            DECLARE @out_prcode nvarchar(50);
            EXEC dbo.usp_InsertGPRHeader 
                @reason = :reason, 
                @applicant = :applicant, 
                @prsupplier = :prsupplier, 
                @prcode = @out_prcode OUTPUT;
            SELECT @out_prcode;
        """)    
        # 执行 SQL
        result = db.session.execute(sql, {
            'reason': reason,
            'applicant': applicant,
            'prsupplier': supplier_code
        }).fetchone()
        
        if not result or not result[0]:
            db.session.rollback()
            return jsonify({'code': 500, 'msg': '生成采购申请单号失败'})
            
        new_prcode = result[0]

        for item in items:
            new_line = PRLineModel(
                prcode=new_prcode,
                prmaterial=item['code'],
                quantity=int(item['qty'])
            )
            db.session.add(new_line)       
        # 提交行数据
        db.session.commit()

        return jsonify({'code': 200, 'msg': '采购申请创建成功', 'prcode': new_prcode})

    except Exception as e:
        db.session.rollback()
        print(f"Error in submit_pr: {e}")
        return jsonify({'code': 500, 'msg': f'系统错误: {str(e)}'})
    
@procurement_bp.route('/prinfo/<string:pr_code>')
def prinfo(pr_code):
    prheader=PRHeaderModel.query.filter_by(prcode=pr_code).first()
    suppliers = SupplierModel.query.all()
    suppliers_json = json.dumps([
        {
            'code': supplier.suppliercode,
            'name': supplier.suppliername
        }
        for supplier in suppliers
    ], ensure_ascii=False)
    materials = MaterialModel.query.all()
    materials_json = json.dumps([
        {
            'code': material.materialcode,
            'desc': material.materialdesc,
            'spec': material.specification
        }
        for material in materials
    ], ensure_ascii=False)
    return render_template('prinfo.html',prheader=prheader,suppliers_json=suppliers_json,materials_json=materials_json)

@procurement_bp.post('/prheader_update')
def prheader_update():
    try:
        data = request.get_json()
        prcode = data.get('prcode')
        supplier_code = data.get('supplier_code')
        reason = data.get('reason')

        if not prcode or not supplier_code or not reason:
            return jsonify({'code': 400, 'msg': '参数不完整'})

        prheader = PRHeaderModel.query.filter_by(prcode=prcode).first()
        if not prheader:
            return jsonify({'code': 404, 'msg': '采购申请单不存在'})

        prheader.prsupplier = supplier_code
        prheader.reason = reason
        
        db.session.commit()
        return jsonify({'code': 200, 'msg': '单据头信息更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)})

@procurement_bp.post('/prline_update')
def prline_update():
    try:
        data = request.get_json()
        prcode = data.get('prcode')
        new_material_code = data.get('material_code') # 下拉框选中的新编码
        quantity = data.get('quantity')
        original_material_code = data.get('original_material_code') # 编辑前的旧编码

        if not prcode or not new_material_code or not quantity:
            return jsonify({'code': 400, 'msg': '参数不完整'})

        # 情况1：新增行（没有原始编码）
        if not original_material_code:
            # 检查是否已存在，防止重复添加
            existing = PRLineModel.query.filter_by(prcode=prcode, prmaterial=new_material_code).first()
            if existing:
                return jsonify({'code': 400, 'msg': '该物料已存在于此申请单中'})
            
            new_line = PRLineModel(prcode=prcode, prmaterial=new_material_code, quantity=int(quantity))
            db.session.add(new_line)
            msg = '采购项添加成功'

        # 情况2：更新现有行
        else:
            # 使用【原始编码】查找数据库中的行
            prline = PRLineModel.query.filter_by(prcode=prcode, prmaterial=original_material_code).first()
            if not prline:
                return jsonify({'code': 404, 'msg': '原采购项未找到，无法更新'})
            
            # 如果修改了物料编码
            if original_material_code != new_material_code:
                # 检查新编码是否冲突
                conflict = PRLineModel.query.filter_by(prcode=prcode, prmaterial=new_material_code).first()
                if conflict:
                     return jsonify({'code': 400, 'msg': '修改后的物料已存在于此申请单中，无法合并'})
                
                # 更新主键字段（SQLAlchemy 支持直接修改）
                prline.prmaterial = new_material_code
            
            # 更新数量
            prline.quantity = int(quantity)
            msg = '采购项更新成功'

        db.session.commit()
        return jsonify({'code': 200, 'msg': msg})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)})

@procurement_bp.post('/prline_delete')
def prline_delete():
    try:
        data = request.get_json()
        prcode = data.get('prcode')
        material_code = data.get('material_code')

        if not prcode or not material_code:
            return jsonify({'code': 400, 'msg': '参数不完整'})

        prline = PRLineModel.query.filter_by(prcode=prcode, prmaterial=material_code).first()
        if prline:
            linecount=PRLineModel.query.filter_by(prcode=prcode).count()
            if linecount<=1:
                return jsonify({'code': 400, 'msg': '采购申请至少包含一条内容'})
            db.session.delete(prline)
            db.session.commit()
            return jsonify({'code': 200, 'msg': '采购项删除成功'})
        else:
            return jsonify({'code': 404, 'msg': '未找到该采购项'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)})

@procurement_bp.post('/pr_delete')
def pr_delete():
    try:
        data = request.get_json()
        prcode = data.get('prcode')

        if not prcode:
            return jsonify({'code': 400, 'msg': '参数不完整'})

        prheader = PRHeaderModel.query.filter_by(prcode=prcode).first()
        if prheader:
            db.session.delete(prheader)
            db.session.commit()
            return jsonify({'code': 200, 'msg': '采购申请删除成功'})
        else:
            return jsonify({'code': 404, 'msg': '采购申请不存在'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)})
    
@procurement_bp.route('/preview')
def preview():
    prheaders=PRHeaderModel.query.filter(PRHeaderModel.prstatus=='待审核').all()
    return render_template('preview.html',prheaders=prheaders)

@procurement_bp.route('/issue_pr/<string:pr_code>')
def issue_pr(pr_code):
    prheader=PRHeaderModel.query.filter_by(prcode=pr_code).first()
    if not prheader:
        return render_template_string("""<script>alert('该采购申请单不存在！');window.history.back();</script>""")
    if prheader.prstatus == '待审核':
        return render_template_string("""<script>alert('该申请正在审核中！');window.history.back();</script>""")
    if prheader.prstatus == '处理成功':
        return render_template_string("""<script>alert('该采购申请单已处理，无需重复下达！');window.history.back();</script>""")
    prheader.prstatus = '待审核'
    db.session.commit()
    return render_template_string("""<script>alert('下达成功！');window.location.href="{{ url_for('procurement.prmanage') }}";</script>""")

@procurement_bp.post('/pr_reject')
def pr_reject():
    data = request.get_json(silent=True) or {}
    prcodes = data.get('prcodes') or []
    # 基本校验
    if not isinstance(prcodes, list) or not prcodes:
        return jsonify({'code': 400, 'msg': '请勾选需要驳回的申请'})
    # 去重 + 去空
    prcodes = [c for c in list(dict.fromkeys(prcodes)) if c]

    try:
        # 只处理“待审核”的单据（避免重复驳回/状态混乱）
        headers = PRHeaderModel.query.filter(PRHeaderModel.prcode.in_(prcodes),PRHeaderModel.prstatus == '待审核').all()

        if not headers:
            return jsonify({'code': 404, 'msg': '未找到可驳回的采购申请（可能已被处理或不存在）'})

        for h in headers:
            h.prstatus = '驳回'

        db.session.commit()
        return jsonify({'code': 200, 'msg': f'已驳回 {len(headers)} 条采购申请'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)})

@procurement_bp.route('/prdetails/<string:pr_code>')
def prdetails(pr_code):
    prheader=PRHeaderModel.query.filter_by(prcode=pr_code).first()
    return render_template('prdetails.html',prheader=prheader)

@procurement_bp.route('/pomanage')
def pomanage():
    poheaders=POHeaderModel.query.all()
    return render_template('pomanage.html', poheaders=poheaders)

@procurement_bp.route('/podetails/<string:po_code>')
def podetails(po_code):
    poheader=POHeaderModel.query.filter_by(pocode=po_code).first()
    return render_template('podetails.html',poheader=poheader)

@procurement_bp.post('/pr_approve')
def pr_approve():
    data = request.get_json(silent=True) or {}
    prcodes = data.get('prcodes') or []

    if not isinstance(prcodes, list) or not prcodes:
        return jsonify({'code': 400, 'msg': '请勾选需要审核的申请'})   
    # 去重
    prcodes = list(set(prcodes))
    
    success_count = 0
    error_msgs = []

    try:
        for prcode in prcodes:
            # 检查状态，确保只有“待审核”的单据才能被审核
            prheader = PRHeaderModel.query.filter_by(prcode=prcode).first()
            if not prheader:
                error_msgs.append(f"单号 {prcode} 不存在")
                continue
            if prheader.prstatus != '待审核':
                error_msgs.append(f"单号 {prcode} 状态不是待审核")
                continue
            # 调用存储过程生成PO并更新PR状态
            sql = text("EXEC dbo.usp_PRtoPO @prcode = :prcode")           
            # 获取 result 对象
            result = db.session.execute(sql, {'prcode': prcode})

            try:
                result.close()
            except Exception:
                pass

            success_count += 1

        if success_count > 0:
            db.session.commit()
            
        msg = f"成功审核 {success_count} 条申请。"
        if error_msgs:
            msg += " 未处理: " + "; ".join(error_msgs)
            
        return jsonify({'code': 200, 'msg': msg})

    except Exception as e:
        db.session.rollback()
        err_str = str(e)
        if '无效的采购申请编号' in err_str:
            return jsonify({'code': 500, 'msg': '审核失败：数据库提示“无效的采购申请编号”，请检查数据一致性。'})
        # 其他错误
        return jsonify({'code': 500, 'msg': f"系统错误: {err_str}"})
    
@procurement_bp.post('/po_place_order')
def po_place_order():
    data = request.get_json(silent=True) or {}
    pocodes = data.get('pocodes') or []

    if not isinstance(pocodes, list) or not pocodes:
        return jsonify({'code': 400, 'msg': '请勾选需要下单的订单'})
    
    # 去重
    pocodes = list(set(pocodes))
    current_time = datetime.now()

    try:
        # 1. 查询并锁定选中的订单头 (with_for_update 实现数据库行锁)
        # 注意：在 SQL Server 中，这通常会添加 UPDLOCK 或 XLOCK
        po_headers = POHeaderModel.query.filter(
            POHeaderModel.pocode.in_(pocodes),
            POHeaderModel.postatus == '待下单'
        ).with_for_update().all()

        if not po_headers:
            return jsonify({'code': 404, 'msg': '未找到有效的待下单订单，请刷新页面重试'})

        processed_count = 0

        for header in po_headers:
            # 2. 遍历该订单的所有采购项
            # 注意：这里假设 polines 关系已在模型中定义，且数据已加载
            # 如果 polines 很多，可以考虑单独查询，但通常订单行数有限，直接访问关系即可
            for line in header.polines:
                # 3. 生成收料单据
                new_receipt = ReceiptModel(
                    receiptid=str(next(gen)), # 利用 SnowflakeGenerator 生成主键
                    materialcode=line.pomaterial,
                    quantity=line.quantity,
                    suppliercode=header.posupplier,
                    status='待接收',
                    pocode=header.pocode,
                    creationtime=current_time
                )
                db.session.add(new_receipt)
            
            # 4. 更新订单头状态
            header.postatus = '已下单'
            header.orderdate = current_time
            processed_count += 1

        # 5. 提交事务 (释放锁)
        db.session.commit()

        return jsonify({'code': 200, 'msg': f'成功下单 {processed_count} 个采购订单，已生成对应收料单。'})

    except Exception as e:
        db.session.rollback() # 回滚事务，释放锁
        return jsonify({'code': 500, 'msg': f'下单失败: {str(e)}'})