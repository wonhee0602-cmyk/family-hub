from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import socket

app = Flask(__name__)
app.config['SECRET_KEY'] = 'family-secret-key-1234'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///family.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

FAMILY_INVITE_CODE = "우리집1234"


# --- 데이터베이스 모델 ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    birthday = db.Column(db.String(20), nullable=True)  # 생일 (MM-DD)


class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(300), nullable=False)
    author = db.Column(db.String(50))
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    content = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, default=False)


class Diary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, default=datetime.date.today)


class Praise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    to_user = db.Column(db.String(50), nullable=False)
    content = db.Column(db.String(300), nullable=False)
    from_user = db.Column(db.String(50), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- 페이지 로직 ---
@app.route('/')
@login_required
def index():
    notices = Notice.query.order_by(Notice.id.desc()).limit(5).all()
    todos = Todo.query.filter_by(user_id=current_user.id).all()
    diaries = Diary.query.filter_by(user_id=current_user.id).order_by(Diary.id.desc()).limit(5).all()
    praises = Praise.query.order_by(Praise.id.desc()).limit(10).all()
    return render_template('index.html', user=current_user, notices=notices, todos=todos, diaries=diaries,
                           praises=praises)


@app.route('/set_birthday', methods=['POST'])
@login_required
def set_birthday():
    bday = request.form.get('birthday')
    if bday:
        current_user.birthday = bday
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')
        password = request.form.get('password')

        if action == 'register':
            invite_code = request.form.get('invite_code')
            if invite_code != FAMILY_INVITE_CODE:
                flash('가족 초대 코드가 올바르지 않습니다!')
                return redirect(url_for('login'))
            if User.query.filter_by(username=username).first():
                flash('이미 존재하는 이름입니다.')
                return redirect(url_for('login'))
            new_user = User(username=username, password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            flash('가족 계정 생성 완료! 로그인하세요.')
            return redirect(url_for('login'))

        elif action == 'login':
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('index'))
            flash('아이디 또는 비밀번호가 틀렸습니다.')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/add_notice', methods=['POST'])
@login_required
def add_notice():
    content = request.form.get('content')
    if content:
        db.session.add(Notice(content=content, author=current_user.username))
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/add_todo', methods=['POST'])
@login_required
def add_todo():
    content = request.form.get('content')
    if content:
        db.session.add(Todo(user_id=current_user.id, content=content))
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/toggle_todo/<int:todo_id>')
@login_required
def toggle_todo(todo_id):
    todo = Todo.query.get(todo_id)
    if todo and todo.user_id == current_user.id:
        todo.done = not todo.done
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/add_diary', methods=['POST'])
@login_required
def add_diary():
    content = request.form.get('content')
    if content:
        db.session.add(Diary(user_id=current_user.id, content=content))
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/add_praise', methods=['POST'])
@login_required
def add_praise():
    to_user = request.form.get('to_user')
    content = request.form.get('content')
    if to_user and content:
        db.session.add(Praise(to_user=to_user, content=content, from_user=current_user.username))
        db.session.commit()
    return redirect(url_for('index'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    # 내 컴퓨터의 로컬 IP 주소 출력 (핸드폰 접속용)
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print("=" * 55)
    print(f"👉 PC 브라우저 접속: http://127.0.0.1:5000")
    print(f"📱 스마트폰(아이폰/갤럭시) 접속 주소: http://{local_ip}:5000")
    print("   (※ 핸드폰과 PC가 같은 Wi-Fi에 연결되어 있어야 합니다)")
    print("=" * 55)

    # 0.0.0.0으로 열어야 외부 기기(핸드폰) 접근 허용됨
    app.run(host='0.0.0.0', port=5000, debug=True)