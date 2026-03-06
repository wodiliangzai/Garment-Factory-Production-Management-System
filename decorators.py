from functools import wraps
from flask import session,redirect,url_for,render_template_string
from models import UserModel,PermissionModel

#是否登录验证
def login_required(func):
    @wraps(func)
    def inner(*args,**kwargs):
        if session.get('username'):
            return func(*args,**kwargs)
        else:
            return redirect(url_for("user.login"))
    return inner

#是否管理员验证
def admin_required(func):
    @wraps(func)
    def inner(*args,**kwargs):
        perm= PermissionModel.query.get(session['username'])
        if perm.charactercode == 'GAdmin':
            return func(*args,**kwargs)
        else:
            return render_template_string("""
                <script>
                    alert('权限不足，无法进行操作！');
                    window.history.back();
                </script>
            """)
    return inner