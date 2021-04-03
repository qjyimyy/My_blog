 # 进行users子应用的视图路由
from django.urls import path
from users.views import RegisterView,ImageCodeView,SmsCodeView,LoginView
urlpatterns = [
    # 两个参数：路由，视图函数名
    path('register/', RegisterView.as_view(), name='register'),
    # 图片验证码的路由
    path('imagecode/', ImageCodeView.as_view(), name='imagecode'),
    # 短信验证码路由
    path('smscode/', SmsCodeView.as_view(), name='smscode'),
    # 登录路由
    path('login/', LoginView.as_view(), name='login'),
]