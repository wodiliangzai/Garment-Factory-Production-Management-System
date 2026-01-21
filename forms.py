from flask_wtf import FlaskForm
from flask import session
from wtforms import StringField,PasswordField,SubmitField,EmailField,HiddenField,SelectField,IntegerField,DateField,ValidationError
from wtforms.validators import DataRequired,EqualTo,Length,Email,InputRequired,NumberRange

class LoginForm(FlaskForm):
    username=StringField('用户名',render_kw={'placeholder':'请输入用户名'},validators=[DataRequired(message='请输入用户名')])
    password=PasswordField('密码',render_kw={'placeholder':'请输入密码'},validators=[DataRequired(message='请输入密码')])
    captcha=StringField('验证码',render_kw={'placeholder':'请输入验证码'},validators=[DataRequired(message='请输入验证码'),Length(min=4,max=4,message="验证码格式错误!")])
    login=SubmitField('登录')

    def validate_captcha(self, field):
        """
        验证验证码是否正确
        """
        session_code = session.get('img_captcha')
        if not session_code or field.data.upper() != session_code.upper():
            raise ValidationError('图像验证码错误，请重新输入！')
        
class UpdateuserForm(FlaskForm):
    hide_username=HiddenField('原用户名')
    username=StringField('用户名',render_kw={'placeholder':'请输入用户名','readonly': True})
    realname=StringField('真实姓名',render_kw={'placeholder':'请输入真实姓名'})
    email=EmailField('邮箱',render_kw={'placeholder':'请输入邮箱'})
    submit=SubmitField('修改')

class AdduserForm(FlaskForm):
    required=StringField('用户名',render_kw={'placeholder':'请输入用户名'})
    realname=StringField('真实姓名',render_kw={'placeholder':'请输入真实姓名'})
    email=EmailField('用户邮箱',render_kw={'placeholder':'请输入邮箱'})
    pwd=PasswordField('密码',render_kw={'placeholder':'请输入密码'})
    pwd2=PasswordField('确认密码',render_kw={'placeholder':'请再次输入密码'})
    add=SubmitField('添加用户')

class ForgotpwdForm(FlaskForm):
    username=StringField('用户名',render_kw={'placeholder':'请输入用户名'},validators=[DataRequired(message='请输入用户名')])
    email=EmailField('用户邮箱',render_kw={'placeholder':'请输入邮箱'},validators=[DataRequired(message='请输入邮箱'),Email(message='邮箱格式不正确')])
    mail_captcha=StringField('邮箱验证码',render_kw={'placeholder':'请输入邮箱验证码'},validators=[DataRequired(message='请输入邮箱验证码'),Length(min=4,max=4,message="验证码格式错误!")])
    img_captcha=StringField('图像验证码',render_kw={'placeholder':'请输入图像验证码'},validators=[DataRequired(message='请输入验证码'),Length(min=4,max=4,message="验证码格式错误!")])
    submit=SubmitField('下一步')

    def validate_mail_captcha(self, field):
        """
        验证邮箱验证码是否正确
        """
        session_code = session.get('mail_captcha')
        if not session_code or field.data.upper() != session_code.upper():
            raise ValidationError('邮箱验证码错误，请重新输入！')

    def validate_img_captcha(self, field):
        """
        验证图像验证码是否正确
        """
        session_code = session.get('img_captcha')
        if not session_code or field.data.upper() != session_code.upper():
            raise ValidationError('图像验证码错误，请重新输入！')
        
class AddcharacterForm(FlaskForm):
    required=StringField('角色代码',render_kw={'placeholder':'请输入角色编码'})
    realname=StringField('角色名称',render_kw={'placeholder':'请输入角色名称'})
    description=StringField('角色说明',render_kw={'placeholder':'请输入角色说明'},validators=[DataRequired(message='请输入角色说明')])
    add=SubmitField('添加角色')

class AltercharacterForm(FlaskForm):
    role_code=StringField('角色代码',render_kw={'placeholder':'请输入角色编码','readonly': True})
    role_name=StringField('角色名称',render_kw={'placeholder':'请输入角色名称'},validators=[DataRequired(message='请输入角色名称')])
    role_desc=StringField('角色说明',render_kw={'placeholder':'请输入角色说明'},validators=[DataRequired(message='请输入角色说明')])
    alter=SubmitField('保存')

class AddsupplierForm(FlaskForm):
    required=StringField('供应商编码',render_kw={'placeholder':'请输入供应商编码'},validators=[Length(max=50,message="供应商编码超长!")])
    realname=StringField('供应商名称',render_kw={'placeholder':'请输入供应商名称'},validators=[Length(max=50,message="供应商名称超长!")])
    description=StringField('供应商地点',render_kw={'placeholder':'请输入供应商地点'},validators=[DataRequired(message='请输入供应商地点!'),Length(max=50,message="供应商地点超长!")])
    add=SubmitField('添加供应商')

class AltersupplierForm(FlaskForm):
    role_code=StringField('供应商编码',render_kw={'placeholder':'请输入供应商编码','readonly': True})
    role_name=StringField('供应商名称',render_kw={'placeholder':'请输入供应商名称'},validators=[DataRequired(message='请输入供应商名称!'),Length(max=50,message="供应商名称超长!")])
    role_desc=StringField('供应商地点',render_kw={'placeholder':'请输入供应商地点'},validators=[DataRequired(message='请输入供应商地点!'),Length(max=50,message="供应商地点超长!")])
    alter=SubmitField('保存')

class AddmaterialForm(FlaskForm):
    required=StringField('物料编码',render_kw={'placeholder':'请输入物料编码'},validators=[DataRequired(message='请输入物料编码!'),Length(max=50,message="物料编码超长!")])
    realname=StringField('物料描述',render_kw={'placeholder':'请输入物料描述'},validators=[DataRequired(message='请输入物料描述!'),Length(max=50,message="物料描述超长!")])
    description=StringField('规格型号',render_kw={'placeholder':'请输入规格型号'},validators=[DataRequired(message='请输入规格型号!'),Length(max=50,message="规格型号超长!")])
    materialtype=SelectField('物料类型',choices=[('','请选择物料类型'),('原材料','原材料'),('半成品','半成品'),('成品','成品')],render_kw={'placeholder':'请选择物料类型'},validators=[InputRequired(message='请选择物料类型')])
    add=SubmitField('添加物料')

class AltermaterialForm(FlaskForm):
    role_code=StringField('物料编码',render_kw={'placeholder':'请输入物料编码','readonly': True})
    role_name=StringField('物料描述',render_kw={'placeholder':'请输入物料描述'},validators=[DataRequired(message='请输入物料描述!'),Length(max=50,message="物料描述超长!")])
    role_desc=StringField('规格型号',render_kw={'placeholder':'请输入规格型号'},validators=[DataRequired(message='请输入规格型号!'),Length(max=50,message="规格型号超长!")])
    role_type=SelectField('物料类型',choices=[('原材料','原材料'),('半成品','半成品'),('成品','成品')],render_kw={'placeholder':'请选择物料类型'},validators=[InputRequired(message='请选择物料类型')])
    alter=SubmitField('保存')

class AddwarehouseForm(FlaskForm):
    required=StringField('仓库编码',render_kw={'placeholder':'请输入仓库编码'},validators=[Length(max=50,message="仓库编码超长!")])
    realname=StringField('仓库名称',render_kw={'placeholder':'请输入仓库名称'},validators=[Length(max=50,message="仓库名称超长!")])
    add=SubmitField('添加仓库')

class AlterwarehouseForm(FlaskForm):
    role_code=StringField('仓库编码',render_kw={'placeholder':'请输入仓库编码','readonly': True})
    role_name=StringField('仓库名称',render_kw={'placeholder':'请输入仓库名称'},validators=[DataRequired(message='请输入仓库名称!'),Length(max=50,message="仓库名称超长!")])
    alter=SubmitField('保存')

class CraftForm(FlaskForm):
	role_code=StringField('物料编码',render_kw={'placeholder':'请输入物料编码','readonly': True})
	department=SelectField('负责部门',render_kw={'placeholder':'请选择负责部门'},validators=[InputRequired(message='请选择负责部门')])
	warehouse=SelectField('完成存放仓库',render_kw={'placeholder':'请选择完成存放仓库'},validators=[InputRequired(message='请选择完成存放仓库')])
	alteruser=StringField('最近更新人',render_kw={'placeholder':'请输入最近更新人','readonly': True})
	submit=SubmitField()

class AddcraftForm(FlaskForm):
    materialcode=SelectField('物料编码',render_kw={'placeholder':'请选择物料编码'},validators=[InputRequired(message='请选择物料编码')])
    department=SelectField('负责部门',render_kw={'placeholder':'请选择负责部门'},validators=[InputRequired(message='请选择负责部门')])
    warehouse=SelectField('完成存放仓库',render_kw={'placeholder':'请选择完成存放仓库'},validators=[InputRequired(message='请选择完成存放仓库')])
    add=SubmitField('添加生产工艺')