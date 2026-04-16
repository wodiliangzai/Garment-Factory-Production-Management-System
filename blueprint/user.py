from flask import Blueprint,render_template,jsonify,redirect,url_for,session,request,render_template_string,flash
from forms import LoginForm,UpdateuserForm,AdduserForm,ForgotpwdForm,AddcharacterForm,AltercharacterForm,AddPermissionForm,AlterPermissionForm,ChangePwdForm,PersonInfoForm
from werkzeug.security import generate_password_hash,check_password_hash #加密与检查密码
from PIL import Image, ImageDraw, ImageFont
import random
import io
from exts import db, mail
from flask_mail import Message
from datetime import datetime
import string
from models import UserModel,CharacterModel,PermissionModel
from decorators import login_required,admin_required

user_bp=Blueprint('user',__name__,url_prefix='/user')

#生成图像验证码
@user_bp.route('/captcha')
def captcha():
    # 生成验证码图片
    image = Image.new('RGB', (120, 30), color=(73, 109, 137))

    font_path = "../static/arial.ttf"  # 注意：你需要一个字体文件
    fnt = ImageFont.truetype(font_path, 20)
    d = ImageDraw.Draw(image)

    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    d.text((10, 10), captcha_text, font=fnt, fill=(255, 255, 0))

    # 添加干扰线条
    for _ in range(random.randint(10, 15)):  # 10到15条线条
        start = (random.randint(0, image.width), random.randint(0, image.height))
        end = (random.randint(0, image.width), random.randint(0, image.height))
        d.line([start, end], fill=(random.randint(50, 200), random.randint(50, 200), random.randint(50, 200)))

    # 添加噪点
    for _ in range(500):  # 添加500个噪点
        xy = (random.randrange(0, image.width), random.randrange(0, image.height))
        d.point(xy, fill=(random.randint(50, 200), random.randint(50, 200), random.randint(50, 200)))

    session['img_captcha'] = captcha_text

    buf = io.BytesIO()
    image.save(buf, format='PNG')
    buf.seek(0)
    return buf.getvalue(), 200, {
        'Content-Type': 'image/png',
        'Content-Length': str(len(buf.getvalue()))
    }

# 获取邮箱验证码
@user_bp.post('/captcha/email')
def get_email_captcha():
    # 从POST请求的表单数据中获取email
    username=request.form.get('username')
    email = request.form.get('email')
    if not UserModel.query.filter_by(username=username,email=email).first():
        return jsonify({"code": 400, "message": "用户名和邮箱不匹配", "data": None})
    # 生成随机验证码并发送邮件
    captcha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    message = Message(subject="一帆制衣邮箱验证码", recipients=[email], body=f"您的验证码是：{captcha}")
    mail.send(message)
    session['mail_captcha'] = captcha
    return jsonify({"code": 200, "message": "", "data": None})

#退登
@user_bp.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for("user.login"))

#登录
@user_bp.route('/login',methods=['GET','POST'])
def login():
    loginform=LoginForm()
    forgotpwdform=ForgotpwdForm()
    if request.method=='GET':
        session.pop('mail_captcha', None)  
        return render_template('login.html',form=loginform,form2=forgotpwdform)
    else:
        if loginform.validate():
            username=loginform.username.data
            password=loginform.password.data
            
            user=UserModel.query.filter_by(username=username).first()
            if user and check_password_hash(user.password,password):
                permission=PermissionModel.query.filter_by(username=username).first()
                if not permission:
                    return render_template('login.html', form=loginform, form2=forgotpwdform,error_msgs=["该用户未被分配任何角色，请联系管理员！"])
                session['username']=permission.username
                session['charactercode']=permission.charactercode
                session['keycode']=permission.keycode
                session.pop('img_captcha', None)  # 删除img_captcha
                return redirect(url_for('home'))
            else:
                return render_template('login.html', form=loginform, form2=forgotpwdform,error_msgs=["用户名或密码错误，请重新输入！"])
        else:
            # 收集所有错误信息
            error_msgs = []
            for field_errors in loginform.errors.values():
                error_msgs.extend(field_errors)
            # 传递到模板
            return render_template('login.html', form=loginform, form2=forgotpwdform,error_msgs=error_msgs)

#忘记密码第一步        
@user_bp.post('/forgotpwd')
def forgotpwd():
    forgotpwdform=ForgotpwdForm()
    if forgotpwdform.validate():
        username=forgotpwdform.username.data
        email=forgotpwdform.email.data
        
        user=UserModel.query.filter_by(username=username,email=email).first()
        if user:
            session['reset_username']=user.username
            session.pop('mail_captcha', None)  
            session.pop('img_captcha', None)  
            return jsonify({'code':200,'msg':'信息正确'})
        else:
            return jsonify({"code": 400, "message": "用户名和邮箱不匹配", "data": None})

    else:
        error_msgs = []
        for field, errors in forgotpwdform.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        return jsonify({"code": 400, "message": "; ".join(error_msgs), "data": None})

#忘记密码第二步
@user_bp.post('/resetpwd')
def resetpwd():
    username=session.get('reset_username')
    password=request.form.get('password')
    if not username:
        return jsonify({'code':400,'msg':'会话已过期，请重新验证身份'})
    user = UserModel.query.get(username)
    user.password = generate_password_hash(password)
    db.session.commit()
    session.pop('reset_username', None)
    return jsonify({'code':200,'msg':'密码重置成功'})

#用户管理界面
@user_bp.route('/usermanage')
@login_required
@admin_required
def usermanage():
    updateuserForm=UpdateuserForm()
    adduserForm=AdduserForm()
    users=UserModel.query.all()
    return render_template('usermanage.html',users=users,updateuserForm=updateuserForm,adduserForm=adduserForm)

#更新用户信息
@user_bp.post('/updateuser/<string:hide_username>')
@login_required
@admin_required
def updateuser(hide_username):
    updateuserForm=UpdateuserForm()
    if updateuserForm.validate():
        data = updateuserForm.data
        user = UserModel.query.filter_by(username=hide_username).first()
        if user:
            newname=data['username']
            if newname!=hide_username and UserModel.query.filter_by(username=newname).first():
                flash("修改失败：用户名已存在", "error") # 使用 flash 消息
                return redirect(url_for('user.usermanage'))
            
            user.username = newname
            user.realname = data['realname']
            user.email = data['email']
            db.session.commit()
            flash("用户信息修改成功", "success")
            return redirect(url_for('user.usermanage'))
        else:
            flash("修改失败：用户已不存在", "error")
            return redirect(url_for('user.usermanage'))
    else:
        error_msgs = []
        for field, errors in updateuserForm.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        flash("修改用户失败："+ "; ".join(error_msgs), "error")
        return redirect(url_for('user.usermanage'))

#添加用户信息       
@user_bp.post('/adduser')
@login_required
@admin_required
def adduser():
    adduserForm=AdduserForm()
    if adduserForm.validate():
        data = adduserForm.data
        if UserModel.query.filter_by(username=data['required']).first():
            flash("添加失败：用户名已存在", "error") # 使用 flash 消息
            return redirect(url_for('user.usermanage'))
        
        new_user = UserModel(
            username=data['required'],
            realname=data['realname'],
            email=data['email'],
            password=generate_password_hash(data['pwd']),
            effectivedate=datetime.now()
        )
        db.session.add(new_user)
        db.session.commit()
        flash("用户添加成功", "success")
        return redirect(url_for('user.usermanage'))
    else:
        error_msgs = []
        for field, errors in adduserForm.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        flash("用户添加失败："+ "; ".join(error_msgs), "error")
        return redirect(url_for('user.usermanage'))

#用户验证（初始化密码前验证）    
@user_bp.post('/verification')
@login_required
@admin_required
def userverification():
    username=request.form.get('username')
    password=request.form.get('password')
    user=UserModel.query.filter_by(username=username).first()
    if username != session.get('username') or not UserModel.query.filter_by(username=username).first() or not check_password_hash(user.password,password):
        return jsonify({'code':400,'msg':'验证失败'})
    return jsonify({'code':200,'msg':'验证成功'})

#初始化用户密码
@user_bp.post('/updatepwd')
@login_required
@admin_required
def updatepwd():
    username=request.form.get('username')
    password=request.form.get('password')
    if not UserModel.query.filter_by(username=username).first():
        return jsonify({'code':400,'msg':'用户不存在'})
    user=UserModel.query.filter_by(username=username).first()
    user.password=generate_password_hash(password)
    db.session.commit()
    return jsonify({'code':200,'msg':'密码修改成功'})

#角色管理界面
@user_bp.route('/character')
@login_required
@admin_required
def character():
    characters=CharacterModel.query.all()
    addcharacterform=AddcharacterForm()
    altercharacterform=AltercharacterForm()
    return render_template('character.html',characters=characters,addcharacterform=addcharacterform,altercharacterform=altercharacterform)

#添加角色信息
@user_bp.post('/addcharacter')
@login_required
@admin_required
def addcharacter():
    addcharacterform=AddcharacterForm()
    if addcharacterform.validate():
        data = addcharacterform.data
        if CharacterModel.query.filter_by(charactercode=data['required']).first() or CharacterModel.query.filter_by(charactername=data['realname']).first():
            flash("添加失败：角色代码或角色名称已存在", "error") # 使用 flash 消息
            return redirect(url_for('user.character'))
        
        new_character = CharacterModel(
            charactercode=data['required'],
            charactername=data['realname'],
            description=data['description'],
            effectivedate=datetime.now()
        )
        db.session.add(new_character)
        db.session.commit()
        flash("角色添加成功", "success")
        return redirect(url_for('user.character'))
    else:
        error_msgs = []
        for field, errors in addcharacterform.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        flash("角色添加失败："+ "; ".join(error_msgs), "error")
        return redirect(url_for('user.character'))

#修改角色信息    
@user_bp.post('/altercharacter/<string:role_code>')
@login_required
@admin_required
def altercharacter(role_code):
    altercharacterform=AltercharacterForm()
    if altercharacterform.validate():
        data = altercharacterform.data
        character = CharacterModel.query.filter_by(charactercode=role_code).first()
        if character:
            if data['role_name']!=character.charactername and CharacterModel.query.filter_by(charactername=data['role_name']).first():
                return jsonify({'code':500,'msg':'角色名称已存在，修改失败'})
            character.charactername = data['role_name']
            character.description = data['role_desc']
            db.session.commit()
            return jsonify({'code':200,'msg':'角色修改成功'})
        else:
            return jsonify({'code':500,'msg':'角色已不存在，修改失败'})
    else:
        error_msgs = []
        for field, errors in altercharacterform.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        return jsonify({"code": 400, "msg": "; ".join(error_msgs)})

#权限管理界面
@user_bp.route('/permission')
@login_required
@admin_required
def permission():
    permissions=PermissionModel.query.all()
    authorized_users = [p.username for p in permissions]

    if authorized_users:
        users_available = UserModel.query.filter(UserModel.username.notin_(authorized_users)).all()
    else:
        users_available = UserModel.query.all()
    addpermissionform=AddPermissionForm()
    addpermissionform.username.choices=[('', '请选择用户')] + [(u.username, f"{u.username} - {u.realname} - {u.email or '无邮箱'}") for u in users_available]
    addpermissionform.charactercode.choices=[('', '请选择角色')] + [(c.charactercode, c.charactername) for c in CharacterModel.query.all()]
    alterpermissionform=AlterPermissionForm()
    alterpermissionform.charactercode.choices=[('', '请选择角色')] + [(c.charactercode, c.charactername) for c in CharacterModel.query.all()]
    return render_template('permission.html',permissions=permissions,addpermissionform=addpermissionform,alterpermissionform=alterpermissionform)

#添加权限信息
@user_bp.post('/addpermission')
@login_required
@admin_required
def addpermission():
    permissions=PermissionModel.query.all()
    authorized_users = [p.username for p in permissions]

    if authorized_users:
        users_available = UserModel.query.filter(UserModel.username.notin_(authorized_users)).all()
    else:
        users_available = UserModel.query.all()
    addpermissionform=AddPermissionForm()
    addpermissionform.username.choices=[('', '请选择用户')] + [(u.username, f"{u.username} - {u.realname} - {u.email or '无邮箱'}") for u in users_available]
    addpermissionform.charactercode.choices=[('', '请选择角色')] + [(c.charactercode, c.charactername) for c in CharacterModel.query.all()]

    if addpermissionform.validate():
        username = addpermissionform.username.data
        if PermissionModel.query.filter_by(username=username).first():
            flash('该用户已存在权限配置，请勿重复添加', 'error')
        else:
            perm = PermissionModel(
                username=username,
                charactercode=addpermissionform.charactercode.data,
                keycode=addpermissionform.permission.data
            )
            try:
                db.session.add(perm)
                db.session.commit()
                flash('权限赋予成功', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'添加失败: {str(e)}', 'error')
    else:
        flash('表单数据验证失败', 'error')
    
    return redirect(url_for('user.permission'))

#修改权限信息
@user_bp.post('/alterpermission/<string:username>')
@login_required
@admin_required
def alterpermission(username):
    alterpermissionform = AlterPermissionForm()
    # 重新填充 choices
    alterpermissionform.charactercode.choices=[('', '请选择角色')] + [(c.charactercode, c.charactername) for c in CharacterModel.query.all()]

    if alterpermissionform.validate():
        perm = PermissionModel.query.filter_by(username=username).first()
        if perm:
            try:
                perm.charactercode = alterpermissionform.charactercode.data
                perm.keycode = alterpermissionform.role_desc.data # 前端字段名为 role_desc，对应数据库 keycode
                db.session.commit()
                return jsonify({'code': 200, 'msg': '权限修改成功'})
            except Exception as e:
                db.session.rollback()
                return jsonify({'code': 500, 'msg': f'数据库错误: {str(e)}'})
        else:
            return jsonify({'code': 404, 'msg': '未找到该用户的权限记录'})
    else:
        errors = "; ".join([msg for sublist in alterpermissionform.errors.values() for msg in sublist])
        return jsonify({'code': 400, 'msg': errors})

#更新密码
@user_bp.route('/changepwd',methods=['GET','POST'])
@login_required
def changepwd():
    form = ChangePwdForm()
    
    # 获取当前的用户名自动填充
    session_username = session.get('username') 

    if request.method == 'GET':
        form.username.data = session_username
        return render_template('changepwd.html', form=form)
        
    if form.validate_on_submit():
        user = UserModel.query.filter_by(username=session_username).first()
        # 检验原始密码是否正确
        if not user or not check_password_hash(user.password, form.old_password.data):
            flash("原密码错误", "error")
            return render_template('changepwd.html', form=form)
        
        # 将新密码进行哈希加密并且存入数据库
        user.password = generate_password_hash(form.new_password.data)
        db.session.commit()      
        flash("密码修改成功!", "success")
    else:
        # 表单验证未通过，把错误信息也通过 flash 返回去
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, "error")
                
    # 填充验证失败返回后的旧数据用户名
    form.username.data = session_username 
    return render_template('changepwd.html', form=form)

@user_bp.route('/personinfo', methods=['GET', 'POST'])
@login_required
def personinfo():
    form = PersonInfoForm()
    
    # 获取当前登录用户名
    session_username = session.get('username')
    user = UserModel.query.filter_by(username=session_username).first()

    if request.method == 'GET':
        # 页面加载时填入现有数据
        form.username.data = user.username
        form.realname.data = user.realname
        form.email.data = user.email
        return render_template('personinfo.html', form=form)
        
    if form.validate_on_submit():
        # 表单验证通过，更新数据并提交
        user.realname = form.realname.data
        user.email = form.email.data
        db.session.commit()
        
        flash("个人信息修改成功", "success")
        return redirect(url_for('user.personinfo'))
    else:
        # 表单验证未通过，把错误信息也通过 flash 返回去
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, "error")
                
    # 填充验证失败返回后的旧数据用户名
    form.username.data = session_username 
    return render_template('personinfo.html', form=form)