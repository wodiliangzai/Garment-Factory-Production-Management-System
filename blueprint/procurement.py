from flask import Blueprint,render_template,jsonify,redirect,url_for,session,request,render_template_string,flash
from datetime import datetime
import string
from exts import db
from models import SupplierModel
from forms import AddsupplierForm,AltersupplierForm

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