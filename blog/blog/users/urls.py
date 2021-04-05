 # 进行users子应用的视图路由
from django.urls import path
from users.views import RegisterView, ImageCodeView, SmsCodeView, LoginView, LoginOutView, ForgetPasswordView
from users.views import UserCenterView
urlpatterns = [
    # 两个参数：路由，视图函数名
    path('register/', RegisterView.as_view(), name='register'),
    # 图片验证码的路由
    path('imagecode/', ImageCodeView.as_view(), name='imagecode'),
    # 短信验证码路由
    path('smscode/', SmsCodeView.as_view(), name='smscode'),
    # 登录路由
    path('login/', LoginView.as_view(), name='login'),
    # 登出路由
    path('logout/', LoginOutView.as_view(), name='logout'),
    # 忘记密码路由
    path('forgetpassword/', ForgetPasswordView.as_view(), name='forgetpassword'),
    # 用户中心展示路由
    path('center/', UserCenterView.as_view(), name='center'),
]