from flask import Blueprint,render_template,jsonify,redirect,url_for,session,request,render_template_string,flash
from datetime import datetime
import string
from exts import db
from models import MaterialModel
from forms import AddmaterialForm

product_bp=Blueprint('product',__name__,url_prefix='/product')

@product_bp.route('/materialmanage')
def materialmanage():
    materials = MaterialModel.query.all()
    addmaterialform=AddmaterialForm()
    return render_template('materialmanage.html',materials=materials,addmaterialform=addmaterialform)

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