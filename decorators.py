from functools import wraps
from flask import session,redirect,url_for,render_template_string
from models import UserModel,PermissionModel

def login_required(func):
    #保留func的信息
    @wraps(func)
    # func(a,b,c)
    # func(1,2,c=3)
    def inner(*args,**kwargs):
        if session.get('username'):
            return func(*args,**kwargs)
        else:
            return redirect(url_for("user.login"))
    return inner

def admin_required(func):
    @wraps(func)
    def inner(*args,**kwargs):
        perm= PermissionModel.query.get(session['username'])

        if perm.charactercode == 'GAdmin':  # 假设1为管理员权限
            return func(*args,**kwargs)
        else:
            # 弹窗后，跳转回去
            return render_template_string("""
                <script>
                    alert('权限不足，无法进行操作！');
                    window.history.back();
                </script>
            """)
    return inner