import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'family-hub-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///family.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- 데이터베이스 테이블 정의 ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    birthday = db.Column(db.String(20), default='')

# 1. 칭찬 모델
class Praise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50), nullable=False)
    receiver = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

# 2. 나만의 일기 모델 (작성자 본인만 봄)
class Diary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

# 3. 내 할 일 모델 (작성자 본인만 봄)
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)

# 4. 가족 공지사항 모델 (가족 전체 공유)
class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# DB 테이블 생성 보장
with app.app_context():
    db.create_all()

# --- 라우트 및 기능 ---

@app.route('/')
@login_required
def index():
    users = User.query.all()
    praises = Praise.query.order_by(Praise.created_at.desc()).all()
    diaries = Diary.query.filter_by(user_id=current_user.id).order_by(Diary.created_at.desc()).all()
    todos = Todo.query.filter_by(user_id=current_user.id).all()
    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    
    return render_template('index.html', 
                           user=current_user, 
                           all_users=users,
                           praises=praises,
                           diaries=diaries,
                           todos=todos,
                           notices=notices)

# 칭찬 보내기 기능
@app.route('/add_praise', methods=['POST'])
@login_required
def add_praise():
    receiver = request.form.get('receiver')
    content = request.form.get('content')
    if receiver and content:
        new_praise = Praise(sender=current_user.username, receiver=receiver, content=content)
        db.session.add(new_praise)
        db.session.commit()
    return redirect(url_for('index'))

# 나만의 일기 저장 기능
@app.route('/add_diary', methods=['POST'])
@login_required
def add_diary():
    content = request.form.get('content')
    if content:
        new_diary = Diary(user_id=current_user.id, content=content)
        db.session.add(new_diary)
        db.session.commit()
    return redirect(url_for('index'))

# 할 일 추가 기능
@app.route('/add_todo', methods=['POST'])
@login_required
def add_todo():
    content = request.form.get('content')
    if content:
        new_todo = Todo(user_id=current_user.id, content=content)
        db.session.add(new_todo)
        db.session.commit()
    return redirect(url_for('index'))

# 공지사항 등록 기능
@app.route('/add_notice', methods=['POST'])
@login_required
def add_notice():
    content = request.form.get('content')
    if content:
        new_notice = Notice(author=current_user.username, content=content)
        db.session.add(new_notice)
        db.session.commit()
    return redirect(url_for('index'))

# 로그인
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('아이디 또는 비밀번호가 일치하지 않습니다.')
    return render_template('login.html')

# 회원가입
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        invite_code = request.form.get('invite_code')
        if invite_code != '서희스타일스':
            flash('가족 초대 코드가 올바르지 않습니다.')
            return redirect(url_for('login'))
            
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('이미 존재하는 아이디입니다.')
            return redirect(url_for('login'))
            
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('index'))
    return render_template('login.html')

# 생일 등록
@app.route('/set_birthday', methods=['POST'])
@login_required
def set_birthday():
    birthday = request.form.get('birthday')
    current_user.birthday = birthday
    db.session.commit()
    return redirect(url_for('index'))

# 로그아웃
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
